"""Detached on-device collection/reset accumulators and checkpoint metadata."""
import torch


def normalizers_from_state(payload):
    states = {'wm': payload['world_model']['dynamics'], 'actor': payload['actor']}
    result = {}
    for module, state in states.items():
        for key, value in state.items():
            if key.endswith('count'):
                prefix = key[:-len('count')]
                mean = state.get(prefix + '_mean', state.get(prefix + 'mean'))
                std = state.get(prefix + '_std', state.get(prefix + 'std'))
                if mean is None or std is None:
                    continue
                v = std.detach().float().cpu().flatten()
                result[module + '.' + prefix.rstrip('.')] = {
                    'count': int(value.item()), 'mean_vector_norm': float(mean.detach().float().norm().cpu()),
                    'std_min_p50_p95_max': [float(v.min()), float(v.quantile(.5)), float(v.quantile(.95)), float(v.max())]}
    return result


def optimizer_metadata(runner):
    return {name: [{'type': type(opt).__name__, 'lr': [float(g['lr']) for g in opt.param_groups]}
                   for opt in optimizers]
            for name, optimizers in [('wm', runner.world_model_learner.optimizers),
                ('actor', runner.policy_learner.actor_optimizers), ('critic', runner.policy_learner.critic_optimizers)]}


class CollectionDiagnostics:
    def __init__(self, runner, clips, hard_ids):
        self.device = runner.device
        self.episode_return = torch.zeros(runner.env.num_envs, device=self.device, dtype=torch.float64)
        self.episode_length = torch.zeros_like(self.episode_return)
        self.totals = torch.zeros(12, device=self.device, dtype=torch.float64)
        categories = sorted({c['category'] for c in clips})
        skills = ['flip', 'side_roll', 'cartwheel', 'handstand']
        self.reset_names = ['hard639', 'nonhard'] + ['category/' + c for c in categories] + ['skill/' + s for s in skills]
        rows = []
        for clip in clips:
            hard = clip['source_clip_id'] in hard_ids
            rows.append([hard, not hard] + [clip['category'] == c for c in categories]
                        + [s in clip['name'].lower() for s in skills])
        self.reset_membership = torch.tensor(rows, device=self.device, dtype=torch.float64)
        self.ends = torch.tensor([c['packed_start'] + c['frames'] for c in clips], device=self.device, dtype=torch.long)
        self.reset_counts = torch.zeros(len(self.reset_names), device=self.device, dtype=torch.float64)
        self.reset_total = torch.zeros((), device=self.device, dtype=torch.float64)
        motion = runner.motion_cmd
        original = motion._external_sampling

        def counted(env_ids):
            frames = original(env_ids)
            ids = torch.searchsorted(self.ends, frames, right=True)
            self.reset_counts.add_(self.reset_membership[ids].sum(0))
            self.reset_total.add_(frames.numel())
            return frames

        motion._external_sampling = counted

    @torch.no_grad()
    def collection(self, rewards, manager):
        rewards = rewards.detach().double()
        hard = manager.terminated.bool()
        timeout = manager.time_outs.bool()
        motion_end = manager.get_term('motion_end').bool()
        done = hard | timeout | motion_end
        self.episode_return.add_(rewards)
        self.episode_length.add_(1)
        self.totals.add_(torch.stack([rewards.sum(), rewards.new_tensor(rewards.numel()), hard.sum(),
            timeout.sum(), motion_end.sum(), (hard & timeout).sum(), (hard & motion_end).sum(),
            done.sum(), (self.episode_return * done).sum(), (self.episode_length * done).sum(),
            (timeout & ~motion_end).sum(), (timeout & motion_end).sum()]))
        self.episode_return.masked_fill_(done, 0)
        self.episode_length.masked_fill_(done, 0)

    def flush(self):
        keys = ['raw_reward_sum', 'transition_count', 'hard_count', 'timeout_count', 'motion_end_count',
                'hard_and_timeout', 'hard_and_motion_end', 'episode_count', 'episode_return_sum',
                'episode_length_sum', 'timeout_without_motion_end', 'timeout_and_motion_end']
        result = {'kind': 'since_previous_log_window', 'collection': dict(zip(keys, self.totals.cpu().tolist())),
                  'actual_reset_count': float(self.reset_total.cpu()),
                  'actual_resets': dict(zip(self.reset_names, self.reset_counts.cpu().tolist())),
                  'reset_count_boundary': 'from formal initial reset; categories partition, named skills may overlap'}
        self.totals.zero_()
        self.reset_total.zero_()
        self.reset_counts.zero_()
        return result
