"""Four frozen examples, sampled from tensors in the scheduled scoring rollout."""
import json
import numpy as np
import torch
from common import PROTOCOL_PATH, QUALITY, write_json


class QualitySeries:
    def __init__(self, output, clips, base, reward_terms):
        self.output = output
        self.plan = json.loads(PROTOCOL_PATH.read_text())['fixed_quality_timeseries']
        members = {m['source_clip_id']: m for m in self.plan['members']}
        self.slots = [i for i, c in enumerate(clips) if c['source_clip_id'] in members]
        self.clips = [clips[i] for i in self.slots]
        self.ids = torch.tensor(self.slots, device=base.device, dtype=torch.long)
        self.origins = base.scene.env_origins[self.ids].clone()
        self.dt = base.step_dt
        self.reward_terms = reward_terms
        self.samples = []

    def capture(self, step, motion, active, terminated, truncated, steps, ref_steps,
                delta, quality, rewards, terms, cumulative_rewards, cumulative_terms):
        if not self.slots:
            return
        ids = self.ids
        # Keep selected small tensors on device until the batch ends. A mask is
        # applied on CPU to retain only stride5, first and actual terminal rows.
        end = terminated[ids] | truncated[ids] | (steps[ids] >= ref_steps[ids])
        keep = active[ids] & (end | (step == 1) | (step % 5 == 0))
        sample = {'executed_transition': steps[ids].clone(), 'keep': keep,
                  'packed_reference_frame': motion.time_steps[ids].clone(),
                  'active_before_step': active[ids].clone(), 'terminated': terminated[ids].clone(),
                  'truncated': truncated[ids].clone(), 'end_of_executed_prefix': end,
                  'robot_anchor_pos_w': motion.robot_anchor_pos_w[ids].clone(),
                  'reference_anchor_pos_w': motion.anchor_pos_w[ids].clone(),
                  'delta_xyz': delta[ids].clone(), 'quality': quality[ids].clone(),
                  'native_reward': rewards[ids].clone(), 'native_reward_terms': terms[ids].clone(),
                  'cumulative_reward_sum': cumulative_rewards[ids].clone(),
                  'cumulative_term_sum': cumulative_terms[ids].clone()}
        self.samples.append(sample)

    def save(self):
        if not self.samples:
            return
        arrays = {key: torch.stack([s[key] for s in self.samples]).cpu().numpy() for key in self.samples[0]}
        origins = self.origins.cpu().numpy()
        self.output.mkdir(parents=True, exist_ok=True)
        for slot, clip in enumerate(self.clips):
            keep = arrays['keep'][:, slot]
            values = {key: value[:, slot][keep] for key, value in arrays.items() if key != 'keep'}
            values['executed_time_seconds'] = values['executed_transition'] * self.dt
            values['clip_relative_reference_frame'] = values['packed_reference_frame'] - clip['packed_start']
            values['reference_time_seconds'] = values['clip_relative_reference_frame'] * self.dt
            values['source_clip_id'] = np.asarray(clip['source_clip_id'], dtype=np.int64)
            values['env_origin'] = origins[slot]
            np.savez_compressed(self.output / f"source_{clip['source_clip_id']:06d}.npz", **values)
            member = next(m for m in self.plan['members'] if m['source_clip_id'] == clip['source_clip_id'])
            write_json(self.output / f"source_{clip['source_clip_id']:06d}.json", {
                'member': member, 'samples': int(keep.sum()), 'sample_every_scoring_transitions': 5,
                'includes_first_and_actual_last_or_failure': True, 'env_origin': origins[slot].tolist(),
                'source': 'same scheduled formal evaluation; no new physics/model/RNG calls',
                'purpose': 'fixed diagnostic example, not a representative random sample'})
        write_json(self.output / 'schema.json', {
            'quality_columns': list(QUALITY), 'native_reward_term_columns': self.reward_terms,
            'step_dt_seconds': self.dt, 'xyz_units': 'metres, world coordinates including env_origin',
            'orientation_units': 'radians', 'delta_definition': 'robot anchor minus reference anchor',
            'timing': self.plan['timing'], 'reference_frame': 'post-step motion.time_steps, advanced reference',
            'executed_transition': 'one-based scored transition, includes first hard failure',
            'cumulative_values': 'every active physical transition, not the stride5 samples',
            'termination': 'native flags at native timing; do not reclassify from post-step quality',
            'prefix_only': True, 'padding': False, 'members': self.plan['members'],
            'npz_fields': list(values)})
