"""Shared real-physics task for SuperMimic and PPO-Sim."""
import torch

from .kinematics import ForwardKinematics
from .simulator import G1Simulator
from .task import observation, reward_and_termination


class ReturnSampler:
    def __init__(self, motions, environments, max_episode_steps=500, gamma=0.99):
        device = motions.device
        clip, frame = [], []
        for i, length in enumerate(motions.lengths.tolist()):
            for start in range(0, length - 1, 50):
                clip.append(i)
                frame.append(start)
        self.clip = torch.tensor(clip, device=device)
        self.frame = torch.tensor(frame, device=device)
        self.bin_offsets = torch.tensor([sum(c < i for c in clip) for i in range(len(motions.names))], device=device)
        self.lengths = motions.lengths
        self.returns = torch.zeros(len(clip), device=device)
        self.memory = torch.full((len(clip),), 1 / len(clip), device=device)
        self.ep_reward = torch.zeros((environments, max_episode_steps), device=device)
        self.ep_bin = torch.zeros((environments, max_episode_steps), device=device, dtype=torch.long)
        self.ep_length = torch.zeros(environments, device=device, dtype=torch.long)
        self.discount = gamma ** torch.arange(max_episode_steps, device=device)
        self.gamma = gamma
        self.gmax = 0.1 / (1 - gamma)

    @torch.no_grad()
    def sample(self, count):
        current = torch.softmax(-25 * self.returns / self.gmax, 0)
        probability = 0.5 / len(current) + 0.4 * current + 0.1 * self.memory / self.memory.sum()
        index = torch.multinomial(probability, count, replacement=True)
        clip = self.clip[index]
        available = torch.minimum(self.lengths[clip] - 1 - self.frame[index], torch.full_like(index, 50))
        frame = self.frame[index] + (torch.rand(count, device=index.device) * available).long()
        return clip, frame

    @torch.no_grad()
    def record(self, reward, clip, frame, boundary):
        ids = torch.arange(len(reward), device=reward.device)
        self.ep_reward[ids, self.ep_length] = reward
        self.ep_bin[ids, self.ep_length] = self.bin_offsets[clip] + frame // 50
        self.ep_length += 1
        ended = torch.nonzero(boundary).flatten()
        if not len(ended):
            return
        times = torch.arange(self.ep_reward.shape[1], device=reward.device)
        valid = times[None] < self.ep_length[ended, None]
        discounted = torch.where(valid, self.ep_reward[ended], 0) * self.discount
        returns = torch.flip(torch.cumsum(torch.flip(discounted, (-1,)), -1), (-1,)) / self.discount
        bins = self.ep_bin[ended][valid]
        sums = torch.zeros_like(self.returns).scatter_add_(0, bins, returns[valid])
        counts = torch.zeros_like(self.returns).scatter_add_(0, bins, torch.ones_like(returns[valid]))
        seen = counts > 0
        # EMA coefficient and finite-episode return convention are explicit choices.
        self.returns[seen] = 0.9 * self.returns[seen] + 0.1 * sums[seen] / counts[seen]
        self.memory.mul_(0.99).add_(torch.softmax(-25 * self.returns / self.gmax, 0), alpha=0.01)
        self.ep_length[ended] = 0


class TrackingEnvironment:
    def __init__(self, motions, num_envs, max_episode_steps=500):
        self.motions = motions
        self.sim = G1Simulator(num_envs)
        self.fk = ForwardKinematics(self.sim.host_model).float().to(motions.device)
        self.sampler = ReturnSampler(motions, num_envs, max_episode_steps)
        self.max_episode_steps = max_episode_steps
        self.device = motions.device
        self.num_envs = num_envs
        self.clip = torch.zeros(num_envs, device=self.device, dtype=torch.long)
        self.frame = torch.zeros_like(self.clip)
        self.episode = torch.zeros_like(self.clip)
        self.length = torch.zeros_like(self.clip)
        self.previous_action = torch.zeros((num_envs, 29), device=self.device)
        self.history = torch.zeros((num_envs, 10, 93), device=self.device)
        self.noise_scale = torch.tensor([0.01] * 29 + [0.5] * 29 + [0.2] * 3 + [0.05] * 3 + [0.] * 29, device=self.device)
        self.reset(torch.arange(num_envs, device=self.device))

    def state(self):
        return torch.cat((self.sim.qpos, self.sim.qvel, self.previous_action), -1)

    def observe(self, state, context, noise=True):
        out = observation(state[..., :36], state[..., 36:71], state[..., 71:], self.sim.q0, context[..., 1:30])
        if noise:
            out = out + (2 * torch.rand_like(out) - 1) * self.noise_scale
        return out

    @torch.no_grad()
    def reset(self, ids):
        clip, frame = self.sampler.sample(len(ids))
        ref = self.motions.get(clip, frame)
        self.sim.reset(ref["qpos"], ref["qvel"], ids, randomize=True)
        self.clip[ids], self.frame[ids] = clip, frame
        self.previous_action[ids] = 0
        self.length[ids] = 0
        self.episode[ids] += 1
        obs = self.observe(self.state()[ids], self.sim.context[ids])
        self.history[ids] = obs[:, None].expand(-1, 10, -1)

    @torch.no_grad()
    def step(self, executed_action):
        transition = {"state": self.state(), "action": executed_action.detach().clone(),
                      "context": self.sim.context.clone(), "observation": self.history[:, -1].clone(),
                      "clip": self.clip.clone(), "frame": self.frame.clone(), "episode": self.episode.clone()}
        qpos, qvel = self.sim.step(executed_action)
        ref = self.motions.get(self.clip, self.frame + 1)
        reward, terminated, metrics = reward_and_termination(self.fk(qpos, qvel), ref, qpos,
                                                            executed_action, self.previous_action,
                                                            self.sim.soft_lower, self.sim.soft_upper)
        if not torch.isfinite(reward).all() or not torch.isfinite(qpos).all() or not torch.isfinite(qvel).all():
            raise FloatingPointError("Nonfinite physical transition; training stopped")
        natural_end = self.frame + 1 >= self.motions.lengths[self.clip] - 1
        self.length += 1
        timeout = self.length >= self.max_episode_steps
        boundary = terminated | natural_end | timeout
        self.previous_action.copy_(executed_action)
        next_state = self.state()
        next_obs = self.observe(next_state, self.sim.context)
        next_history = torch.cat((self.history[:, 1:], next_obs[:, None]), 1)
        transition.update(next_state=next_state, terminated=terminated, reward=reward,
                          boundary=boundary, natural_end=natural_end, timeout=timeout,
                          next_history=next_history, root_position_error=metrics["root_position_error_m"])
        self.sampler.record(reward, self.clip, self.frame, boundary)
        self.frame += 1
        self.history.copy_(next_history)
        ended = torch.nonzero(boundary).flatten()
        if len(ended):
            self.reset(ended)
        return transition
