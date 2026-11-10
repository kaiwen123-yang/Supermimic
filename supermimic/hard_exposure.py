"""Counters from P10's actual samples and existing WM forward tensors."""
import json
import torch

PHASES = ("resets", "WM_windows", "Actor_starts", "real_transitions")
GROUPS = ("lafan", "hard_bones", "other_bones")
SLICES = {"root_position_m2": (0, 3), "root_rotation_rad2": (3, 6),
    "joint_position_rad2": (6, 35), "root_linear_velocity_scaled_mse": (35, 38),
    "root_angular_velocity_scaled_mse": (38, 41), "joint_velocity_scaled_mse": (41, 70)}


class HardExposure:
    def __init__(self, env, root_height_mode=None):
        self.env = env
        self.root_height_mode = root_height_mode
        m, device = env.motions, env.device
        self.hard_clips = torch.nonzero(m.hard_mask).flatten()
        self.hard_index = torch.full_like(m.lengths, -1)
        self.hard_index[self.hard_clips] = torch.arange(len(self.hard_clips), device=device)
        self.groups = torch.where(m.source_ids == m.source_names.index("lafan"), 0,
            torch.where(m.hard_mask, 1, 2))
        self.counts = torch.zeros((4, 3, 5), dtype=torch.long, device=device)
        self.per_clip = torch.zeros((4, len(self.hard_clips)), dtype=torch.long, device=device)
        self.reset_bins_seen = torch.zeros_like(env.sampler.clip, dtype=torch.bool)
        self.wm_sums = torch.zeros((3, 71), dtype=torch.float64, device=device)
        self.wm_counts = torch.zeros(3, dtype=torch.long, device=device)
        if root_height_mode is not None:
            self.hard_bins = torch.nonzero(m.hard_mask[env.sampler.clip]).flatten()
            self.hard_bin_index = torch.full_like(env.sampler.clip, -1)
            self.hard_bin_index[self.hard_bins] = torch.arange(len(self.hard_bins), device=device)
            self.bin_counts = torch.zeros((3, len(self.hard_bins)), dtype=torch.long, device=device)
            self.bin_error_sums = torch.zeros((len(self.hard_bins), 4), dtype=torch.float64, device=device)
            self.phase_error_clip = torch.tensor([("flip" in n.lower() or "handstand" in n.lower())
                for n in m.original_names], device=device) & m.hard_mask
            self.wm_height_sums = torch.zeros((3, 9), dtype=torch.float64, device=device)
            self.actor_height_sums = torch.zeros((3, 6), dtype=torch.float64, device=device)
            self.actor_height_counts = torch.zeros(3, dtype=torch.long, device=device)

    @torch.no_grad()
    def count(self, phase, clip, frame):
        remaining = self.env.motions.lengths[clip] - 1 - frame
        bins = torch.bucketize(remaining, remaining.new_tensor([16, 32, 50, 250]))
        self.counts[phase].add_(torch.bincount(self.groups[clip]*5+bins, minlength=15).reshape(3, 5))
        ids = self.hard_index[clip]
        selected = ids >= 0
        self.per_clip[phase].add_(torch.bincount(ids[selected], minlength=len(self.hard_clips)))
        if self.root_height_mode is not None and phase > 0:
            bin_ids = self.hard_bin_index[self.env.sampler.bin_offsets[clip] + frame//50].clamp_min(0)
            self.bin_counts[phase-1].scatter_add_(0, bin_ids, selected.long())
        if phase == 0:
            self.reset_bins_seen[self.env.sampler.bin_offsets[clip[selected]] + frame[selected]//50] = True

    @torch.no_grad()
    def world_error(self, clip, squared, bce, start_frame=None, previous=None, predicted=None, real_current=None, real_next=None):
        group = self.groups[clip]
        self.wm_sums[:, :70].index_add_(0, group, squared.detach().double())
        self.wm_sums[:, 70].index_add_(0, group, bce.detach().double())
        self.wm_counts.add_(torch.bincount(group, minlength=3))
        if self.root_height_mode is not None:
            pred_r = predicted[:, 2] - previous[:, 2] - .01*(previous[:, 38] + predicted[:, 38])
            real_r = real_next[:, 2] - real_current[:, 2] - .01*(real_current[:, 38] + real_next[:, 38])
            physical = torch.stack((squared[:, 2], 9*squared[:, 37], squared[:, 3:6].sum(-1)), -1)
            values = torch.cat((torch.stack((pred_r, pred_r.abs(), pred_r.square(),
                real_r, real_r.abs(), real_r.square()), -1), physical), -1)
            self.wm_height_sums.index_add_(0, group, values.double())
            selected = self.phase_error_clip[clip]
            bin_ids = self.hard_bin_index[self.env.sampler.bin_offsets[clip] + start_frame//50].clamp_min(0)
            errors = torch.cat((physical, torch.ones_like(physical[:, :1])), -1) * selected[:, None]
            self.bin_error_sums.index_add_(0, bin_ids, errors.double())

    @torch.no_grad()
    def actor_height(self, clip, state, predicted, survival, natural_end):
        if self.root_height_mode is not None:
            residual = predicted[:, 2] - state[:, 2] - .01*(state[:, 38] + predicted[:, 38])
            values = torch.stack((survival, survival*residual, survival*residual.abs(),
                survival*residual.square(), natural_end.to(survival.dtype), survival*natural_end), -1)
            group = self.groups[clip]
            self.actor_height_sums.index_add_(0, group, values.double())
            self.actor_height_counts.scatter_add_(0, group, torch.ones_like(group))

    def state_dict(self):
        names = ["counts", "per_clip", "reset_bins_seen", "wm_sums", "wm_counts"]
        if self.root_height_mode is not None:
            names += ["bin_counts", "bin_error_sums", "wm_height_sums", "actor_height_sums", "actor_height_counts"]
        return {name: getattr(self, name) for name in names}

    def load_state_dict(self, state):
        for name, value in state.items():
            getattr(self, name).copy_(value)

    def save(self, directory, iteration):
        directory.mkdir(parents=True, exist_ok=True)
        m = self.env.motions
        counts, per_clip = self.counts.cpu().tolist(), self.per_clip.cpu().tolist()
        samples, sums = self.wm_counts.cpu().tolist(), self.wm_sums.cpu().tolist()
        seen_clips = self.env.sampler.clip[self.reset_bins_seen]
        visited = torch.bincount(self.hard_index[seen_clips], minlength=len(self.hard_clips)).cpu().tolist()
        rows = [{"source_clip_id": m.original_source_clip_ids[c], "motion": m.original_names[c],
            **{phase: per_clip[p][i] for p, phase in enumerate(PHASES)}, "unique_reset_bins_visited": visited[i]}
            for i, c in enumerate(self.hard_clips.cpu().tolist())]
        result = {"through_iteration": iteration, "cumulative_new_stage": True,
            "includes_necessary_replay_fill": True, "groups": GROUPS,
            "remaining_steps_bins": [[1,16],[17,32],[33,50],[51,250],[251,None]],
            "counts": {phase: dict(zip(GROUPS, counts[p])) for p, phase in enumerate(PHASES)},
            "unique_hard_clips_by_phase": {phase: sum(v > 0 for v in per_clip[p]) for p, phase in enumerate(PHASES)},
            "unique_hard_reset_bins": sum(visited), "hard_clips": rows,
            "WM_errors": {group: {"prediction_samples": samples[i],
                "state_components": {name: sum(sums[i][a:b])/((b-a)*samples[i]) if samples[i] else None
                    for name, (a,b) in SLICES.items()},
                "termination_bce": sums[i][70]/samples[i] if samples[i] else None} for i, group in enumerate(GROUPS)},
            "interpretation": "Own evolving replay; existing forward errors only. Environment quotas are not learner sample shares."}
        if self.root_height_mode is not None:
            wm = self.wm_height_sums.cpu().tolist()
            actor = self.actor_height_sums.cpu().tolist()
            actor_counts = self.actor_height_counts.cpu().tolist()
            wm_fields = ["predicted_signed_residual_m", "predicted_abs_residual_m", "predicted_residual_squared_m2",
                "real_signed_residual_m", "real_abs_residual_m", "real_residual_squared_m2",
                "z_squared_error_m2", "vz_squared_error_m2_per_s2", "root_SO3_squared_error_rad2"]
            actor_fields = ["sum_S", "sum_S_r", "sum_S_abs_r", "sum_S_r_squared", "natural_end_flags", "sum_S_natural_end"]
            result["height_consistency"] = {"world_root_height_mode": self.root_height_mode,
                "definition": "r=z_next-z-.01*(vz+vz_next); world frame, dt=.02. Candidate residual is zero by construction, not evidence of accuracy.",
                "WM": {group: {"prediction_samples": samples[i], "sums": dict(zip(wm_fields, wm[i])),
                    "means": {key: value/samples[i] if samples[i] else None for key,value in zip(wm_fields,wm[i])}}
                    for i,group in enumerate(GROUPS)},
                "Actor": {group: {"transitions": actor_counts[i], "sums": dict(zip(actor_fields,actor[i])),
                    "S_weighted_signed_residual_m": actor[i][1]/actor[i][0] if actor[i][0] else None,
                    "S_weighted_abs_residual_m": actor[i][2]/actor[i][0] if actor[i][0] else None,
                    "S_weighted_squared_residual_m2": actor[i][3]/actor[i][0] if actor[i][0] else None}
                    for i,group in enumerate(GROUPS)},
                "Actor_semantics": "Detached pre-reward survival; first terminating transition retained; natural_end_flags include later natural-end suffix flags and are separate from geometric failure."}
            bin_counts = self.bin_counts.cpu().tolist()
            bin_errors = self.bin_error_sums.cpu().tolist()
            bin_clips = self.env.sampler.clip[self.hard_bins]
            bin_numbers = ((self.hard_bins-self.env.sampler.bin_offsets[bin_clips])).cpu().tolist()
            result["hard_bins"] = {"bin_frames":50,
                "columns":["source_clip_id","start_bin","real_transition_start_count","effective_WM_window_start_count","Actor_start_count",
                    "z_squared_error_m2","vz_squared_error_m2_per_s2","root_SO3_squared_error_rad2","WM_prediction_samples"],
                "rows":[[m.original_source_clip_ids[c],bin_numbers[i],bin_counts[2][i],bin_counts[0][i],bin_counts[1][i],*bin_errors[i]]
                    for i,c in enumerate(bin_clips.cpu().tolist())],
                "error_scope":"Flip/handstand only; all k8 errors assigned to the sampled window start bin, not independent per-frame bin errors. Counts cover all fixed hard clips."}
        (directory / f"hard_exposure_{iteration:07d}.json").write_text(json.dumps(result, separators=(",", ":"))+"\n")
