"""Counters from P10's actual samples and existing WM forward tensors."""
import json
import torch

PHASES = ("resets", "WM_windows", "Actor_starts", "real_transitions")
GROUPS = ("lafan", "hard_bones", "other_bones")
SLICES = {"root_position_m2": (0, 3), "root_rotation_rad2": (3, 6),
    "joint_position_rad2": (6, 35), "root_linear_velocity_scaled_mse": (35, 38),
    "root_angular_velocity_scaled_mse": (38, 41), "joint_velocity_scaled_mse": (41, 70)}


class HardExposure:
    def __init__(self, env):
        self.env = env
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

    @torch.no_grad()
    def count(self, phase, clip, frame):
        remaining = self.env.motions.lengths[clip] - 1 - frame
        bins = torch.bucketize(remaining, remaining.new_tensor([16, 32, 50, 250]))
        self.counts[phase].add_(torch.bincount(self.groups[clip]*5+bins, minlength=15).reshape(3, 5))
        ids = self.hard_index[clip]
        selected = ids >= 0
        self.per_clip[phase].add_(torch.bincount(ids[selected], minlength=len(self.hard_clips)))
        if phase == 0:
            self.reset_bins_seen[self.env.sampler.bin_offsets[clip[selected]] + frame[selected]//50] = True

    @torch.no_grad()
    def world_error(self, clip, squared, bce):
        group = self.groups[clip]
        self.wm_sums[:, :70].index_add_(0, group, squared.detach().double())
        self.wm_sums[:, 70].index_add_(0, group, bce.detach().double())
        self.wm_counts.add_(torch.bincount(group, minlength=3))

    def state_dict(self):
        return {name: getattr(self, name) for name in ("counts", "per_clip", "reset_bins_seen", "wm_sums", "wm_counts")}

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
        (directory / f"hard_exposure_{iteration:07d}.json").write_text(json.dumps(result, separators=(",", ":"))+"\n")
