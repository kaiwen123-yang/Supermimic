"""SuperMimic's three-phase update and the matched PPO-Sim baseline."""
import math
import re
import torch
from torch import nn
from torch.nn import functional as F

from .networks import Actor, Critic, WorldModel, state_prediction_squared_coordinates
from .replay import Replay
from .task import reward_and_termination


def optimize(loss, optimizer, parameters, element_clip=None):
    parameters = list(parameters)
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError("Nonfinite learning objective")
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    norm = nn.utils.clip_grad_norm_(parameters, 1.0, error_if_nonfinite=True)
    if element_clip is not None:
        for p in parameters:
            if p.grad is not None:
                p.grad.clamp_(-element_clip, element_clip)
    optimizer.step()
    return float(norm)


class SuperMimic:
    def __init__(self, env, cfg):
        self.env, self.cfg = env, cfg
        self.actor, self.critic, self.world = Actor().to(env.device), Critic().to(env.device), WorldModel().to(env.device)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=cfg["learning_rate"], betas=(0.9, 0.95))
        self.critic_opt = torch.optim.Adam(self.critic.parameters(), lr=cfg["learning_rate"])
        self.world_opt = torch.optim.Adam(self.world.parameters(), lr=cfg["learning_rate"])
        self.replay = Replay(cfg["replay_steps_per_environment"], env.num_envs, env.device)
        self.collected_steps = 0
        self.phase_times = {}
        families = [re.match(r"[A-Za-z]+", name)[0] for name in env.motions.names]
        self.family_names = sorted(set(families))
        self.clip_family = torch.tensor([self.family_names.index(f) for f in families], device=env.device)

    @torch.no_grad()
    def collect(self, steps):
        rewards, failures = [], []
        counts = torch.zeros(len(self.family_names), device=self.env.device)
        failed = torch.zeros_like(counts)
        reset_counts = torch.zeros_like(counts)
        for _ in range(steps):
            goal = self.env.motions.goal(self.env.clip, self.env.frame,
                goal_frame=self.cfg.get("goal_frame", "reference_heading"), root_quaternion=self.env.sim.qpos[:, 3:7])
            action = self.actor(self.env.history, goal)
            executed = action + 0.1 * torch.randn_like(action)
            transition = self.env.step(executed)
            self.replay.add(transition)
            rewards.append(transition["reward"].mean())
            failures.append(transition["terminated"].float().mean())
            family = self.clip_family[transition["clip"]]
            counts.add_(torch.bincount(family, minlength=len(counts)))
            failed.add_(torch.bincount(family[transition["terminated"]], minlength=len(counts)))
            reset_counts.add_(torch.bincount(self.clip_family[self.env.clip[transition["boundary"]]], minlength=len(counts)))
            self.collected_steps += self.env.num_envs
        return {"sim_step_reward": float(torch.stack(rewards).mean()), "sim_step_termination_fraction": float(torch.stack(failures).mean()),
                "family_transitions": dict(zip(self.family_names, counts.long().tolist())),
                "family_sample_share": dict(zip(self.family_names, (counts / counts.sum()).tolist())),
                "family_failure_count": dict(zip(self.family_names, failed.long().tolist())),
                "family_reset_samples": dict(zip(self.family_names, reset_counts.long().tolist()))}

    def fit_world(self):
        cfg = self.cfg
        state_losses, termination_losses, norms = [], [], []
        use_bce = cfg.get("world_termination_loss", "aux_bce") == "aux_bce"
        components = torch.zeros(70, device=self.env.device)
        family_counts = torch.zeros(len(self.family_names), device=self.env.device)
        for _ in range(cfg["world_batches"]):
            sample = self.replay.sample(cfg["world_batch_size"], cfg["world_window"])
            state = sample["state"][:, 0]
            family_counts.add_(torch.bincount(self.clip_family[sample["clip"].flatten()], minlength=len(family_counts)))
            state_loss = term_loss = 0
            for j in range(cfg["world_window"]):
                state = self.world(state, sample["action"][:, j], sample["context"][:, j])
                squared = state_prediction_squared_coordinates(state, sample["next_state"][:, j])
                state_loss = state_loss + squared.mean(-1).mean()
                components.add_(squared.detach().mean(0))
                if use_bce:
                    reference = self.env.motions.get(sample["clip"][:, j], sample["frame"][:, j] + 1)
                    logits = self.world.termination_logits(state, reference["qpos"])
                    term_loss = term_loss + F.binary_cross_entropy_with_logits(logits, sample["terminated"][:, j].float())
            loss = (state_loss + term_loss) / cfg["world_window"]
            norms.append(optimize(loss, self.world_opt, self.world.parameters()))
            state_losses.append(float(state_loss.detach()) / cfg["world_window"])
            if use_bce:
                termination_losses.append(float(term_loss.detach()) / cfg["world_window"])
        components /= cfg["world_batches"] * cfg["world_window"]
        slices = {"root_position_m2": (0, 3), "root_rotation_rad2": (3, 6), "joint_position_rad2": (6, 35),
                  "root_linear_velocity_scaled_mse": (35, 38), "root_angular_velocity_scaled_mse": (38, 41),
                  "joint_velocity_scaled_mse": (41, 70)}
        return {"wm_normalized_state_mse": sum(state_losses) / len(state_losses),
                "world_termination_loss": cfg.get("world_termination_loss", "aux_bce"),
                "wm_termination_bce": sum(termination_losses) / len(termination_losses) if use_bce else None,
                "wm_state_components": {name: float(components[a:b].mean()) for name, (a, b) in slices.items()},
                "wm_family_sample_share": dict(zip(self.family_names, (family_counts / family_counts.sum()).tolist())),
                "wm_gradient_norm_before_clip": sum(norms) / len(norms)}

    def improve_policy(self):
        cfg, env = self.cfg, self.env
        sample = self.replay.sample(cfg["imagination_batch_size"])
        state, context, history = sample["state"][:, 0], sample["context"][:, 0], sample["history"]
        clip, frame = sample["clip"][:, 0], sample["frame"][:, 0]
        horizon, gamma, lam = cfg["imagination_horizon"], cfg["gamma"], cfg["lambda"]
        self.world.requires_grad_(False)
        self.critic.requires_grad_(False)
        survival = torch.ones(len(state), device=state.device)
        objective = torch.zeros_like(survival)
        states, goals, critic_references, rewards, deaths, values = [], [], [], [], [], []
        for step in range(horizon):
            goal = env.motions.goal(clip, frame + step,
                goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7])
            states.append(state.detach())
            goals.append(goal.detach())
            current_ref = env.motions.get(clip, frame + step)["qpos"]
            critic_references.append(current_ref)
            with torch.no_grad():
                values.append(self.critic(state, goal, context, current_ref))
            action = self.actor(history, goal)
            predicted = self.world(state, action, context)
            ref = env.motions.get(clip, frame + step + 1)
            reward, _, _ = reward_and_termination(env.fk(predicted[:, :36], predicted[:, 36:71]), ref,
                                                  predicted[:, :36], action, state[:, 71:],
                                                  env.sim.soft_lower, env.sim.soft_upper)
            probability = self.world.termination_probability(
                predicted, ref["qpos"], cfg.get("imagination_termination", "learned"),
                cfg.get("termination_smoothing_temperature", 0.05))
            natural_end = frame + step + 1 >= env.motions.lengths[clip] - 1
            probability = torch.where(natural_end, torch.ones_like(probability), probability)
            objective = objective + gamma**step * survival * reward
            survival = survival * (1 - probability)
            rewards.append(reward.detach())
            deaths.append(probability.detach())
            state = predicted
            obs = env.observe(state, context, noise=True)
            history = torch.cat((history[:, 1:], obs[:, None]), 1)
        goal_end = env.motions.goal(clip, frame + horizon,
            goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7])
        terminal_value = self.critic(state, goal_end, context, env.motions.get(clip, frame + horizon)["qpos"])
        objective = objective + gamma**horizon * survival * terminal_value
        values.append(terminal_value.detach())
        actor_loss = -objective.mean()
        actor_norm = optimize(actor_loss, self.actor_opt, self.actor.parameters(), element_clip=0.1)
        self.world.requires_grad_(True)
        self.critic.requires_grad_(True)
        targets = [None] * horizon
        target = values[-1]
        for t in reversed(range(horizon)):
            target = rewards[t] + gamma * (1 - deaths[t]) * ((1 - lam) * values[t + 1] + lam * target)
            targets[t] = target
        states = torch.stack(states).flatten(0, 1)
        goals = torch.stack(goals).flatten(0, 1)
        critic_references = torch.stack(critic_references).flatten(0, 1)
        contexts = context.unsqueeze(0).expand(horizon, -1, -1).reshape(-1, context.shape[-1])
        targets = torch.stack(targets).flatten()
        losses = []
        for _ in range(cfg["critic_epochs"]):
            indices = torch.randperm(len(targets), device=targets.device)
            for ids in indices.tensor_split(cfg["critic_minibatches"]):
                prediction = self.critic(states[ids], goals[ids], contexts[ids], critic_references[ids])
                loss = F.mse_loss(prediction, targets[ids])
                optimize(loss, self.critic_opt, self.critic.parameters())
                losses.append(float(loss.detach()))
        return {"imagined_discounted_return": -float(actor_loss.detach()),
                "actor_gradient_norm_before_clip": actor_norm,
                "critic_mse": sum(losses) / len(losses),
                "imagined_survival_at_horizon": float(survival.detach().mean())}

    def set_schedule(self, iteration):
        progress = min(iteration / self.cfg["cosine_iterations"], 1.)
        multiplier = 0.03 + 0.97 * (1 + math.cos(math.pi * progress)) / 2
        for optimizer in (self.actor_opt, self.world_opt, self.critic_opt):
            for group in optimizer.param_groups:
                group["lr"] = self.cfg["learning_rate"] * multiplier

    def checkpoint(self):
        return {"actor": self.actor.state_dict(), "critic": self.critic.state_dict(), "world_model": self.world.state_dict(),
                "actor_optimizer": self.actor_opt.state_dict(), "critic_optimizer": self.critic_opt.state_dict(),
                "world_optimizer": self.world_opt.state_dict(), "collected_steps": self.collected_steps,
                "replay_saved": False, "resume_requires_fresh_replay_warmup": True}


class PPOSim:
    def __init__(self, env, cfg):
        self.env, self.cfg = env, cfg
        self.actor, self.critic = Actor().to(env.device), Critic().to(env.device)
        self.log_std = nn.Parameter(torch.zeros(29, device=env.device))
        self.parameters = list(self.actor.parameters()) + list(self.critic.parameters()) + [self.log_std]
        self.optimizer = torch.optim.Adam(self.parameters, lr=cfg["ppo_learning_rate"])
        self.collected_steps = 0

    @torch.no_grad()
    def collect(self):
        env, cfg = self.env, self.cfg
        records = []
        for _ in range(cfg["ppo_rollout_steps"]):
            state, history = env.state(), env.history.clone()
            goal = env.motions.goal(env.clip, env.frame,
                goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7])
            context = env.sim.context.clone()
            current_ref = env.motions.get(env.clip, env.frame)["qpos"]
            mean = self.actor(history, goal)
            std = self.log_std.exp().expand_as(mean)
            distribution = torch.distributions.Normal(mean, std)
            action = distribution.sample()
            value = self.critic(state, goal, context, current_ref)
            transition = env.step(action)
            next_goal = env.motions.goal(transition["clip"], transition["frame"] + 1,
                goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=transition["next_state"][:, 3:7])
            next_ref = env.motions.get(transition["clip"], transition["frame"] + 1)["qpos"]
            next_value = self.critic(transition["next_state"], next_goal, context, next_ref)
            terminal = transition["terminated"] | transition["natural_end"]
            records.append({"state": state, "history": history, "goal": goal, "context": context, "reference_qpos": current_ref,
                            "action": action, "old_mean": mean, "old_std": std.clone(),
                            "old_log_prob": distribution.log_prob(action).sum(-1), "old_value": value,
                            "reward": transition["reward"], "terminal": terminal, "boundary": transition["boundary"],
                            "next_value": next_value, "terminated": transition["terminated"]})
            self.collected_steps += env.num_envs
        advantage = torch.zeros(env.num_envs, device=env.device)
        for item in reversed(records):
            delta = item["reward"] + cfg["gamma"] * (~item["terminal"]) * item["next_value"] - item["old_value"]
            advantage = delta + cfg["gamma"] * cfg["lambda"] * (~item["boundary"]) * advantage
            item["advantage"] = advantage
            item["target"] = advantage + item["old_value"]
        data = {key: torch.stack([item[key] for item in records]).flatten(0, 1) for key in records[0]}
        data["advantage"] = (data["advantage"] - data["advantage"].mean()) / (data["advantage"].std() + 1e-8)
        return data

    def update(self, data):
        cfg = self.cfg
        actor_losses, value_losses, kls = [], [], []
        for _ in range(cfg["ppo_epochs"]):
            for ids in torch.randperm(len(data["target"]), device=self.env.device).tensor_split(cfg["ppo_minibatches"]):
                mean = self.actor(data["history"][ids], data["goal"][ids])
                std = self.log_std.exp().expand_as(mean)
                distribution = torch.distributions.Normal(mean, std)
                log_prob = distribution.log_prob(data["action"][ids]).sum(-1)
                ratio = torch.exp(log_prob - data["old_log_prob"][ids])
                advantage = data["advantage"][ids]
                actor_loss = -torch.minimum(ratio * advantage, ratio.clamp(0.8, 1.2) * advantage).mean()
                value = self.critic(data["state"][ids], data["goal"][ids], data["context"][ids], data["reference_qpos"][ids])
                value_clip = data["old_value"][ids] + (value - data["old_value"][ids]).clamp(-0.2, 0.2)
                value_loss = torch.maximum((value - data["target"][ids]).square(), (value_clip - data["target"][ids]).square()).mean()
                entropy = distribution.entropy().sum(-1).mean()
                with torch.no_grad():
                    old_std, old_mean = data["old_std"][ids], data["old_mean"][ids]
                    kl = (torch.log(std / old_std) + (old_std.square() + (old_mean - mean).square()) / (2 * std.square()) - 0.5).sum(-1).mean()
                    lr = self.optimizer.param_groups[0]["lr"]
                    if kl > 0.02:
                        lr = max(1e-5, lr / 1.5)
                    elif 0 < kl < 0.005:
                        lr = min(1e-2, lr * 1.5)
                    for group in self.optimizer.param_groups:
                        group["lr"] = lr
                loss = actor_loss + value_loss - 0.005 * entropy
                optimize(loss, self.optimizer, self.parameters)
                actor_losses.append(float(actor_loss.detach()))
                value_losses.append(float(value_loss.detach()))
                kls.append(float(kl))
        return {"ppo_surrogate_loss": sum(actor_losses) / len(actor_losses),
                "critic_mse": sum(value_losses) / len(value_losses), "ppo_mean_kl": sum(kls) / len(kls),
                "sim_step_reward": float(data["reward"].mean()),
                "sim_step_termination_fraction": float(data["terminated"].float().mean()),
                "learning_rate": self.optimizer.param_groups[0]["lr"]}

    def checkpoint(self):
        return {"actor": self.actor.state_dict(), "critic": self.critic.state_dict(), "log_std": self.log_std.detach(),
                "optimizer": self.optimizer.state_dict(), "collected_steps": self.collected_steps}
