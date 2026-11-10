"""SuperMimic's three-phase update and the matched PPO-Sim baseline."""
import math
import re
import torch
from torch import nn
from torch.nn import functional as F

from .networks import Actor, Critic, WorldModel, state_prediction_squared_coordinates, actor_root_position_error
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
        self.actor = Actor(cfg.get("actor_root_position_feedback", False)).to(env.device)
        self.critic, self.world = Critic().to(env.device), WorldModel(cfg.get("world_root_height_mode", "residual")).to(env.device)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=cfg["learning_rate"], betas=(0.9, 0.95))
        self.critic_opt = torch.optim.Adam(self.critic.parameters(), lr=cfg["learning_rate"])
        self.world_opt = torch.optim.Adam(self.world.parameters(), lr=cfg["learning_rate"])
        self.replay = Replay(cfg["replay_steps_per_environment"], env.num_envs, env.device)
        self.collected_steps = 0
        self.phase_times = {}
        families = env.motions.families
        self.family_names = sorted(set(families))
        family_ids = {name: i for i, name in enumerate(self.family_names)}
        self.clip_family = torch.tensor([family_ids[f] for f in families], device=env.device)
        self.record_sampling = cfg.get("record_source_remaining_statistics", False)
        if self.record_sampling:
            self.source_names = env.motions.source_names
            self.sampling_counts = torch.zeros((3, len(self.source_names), 5), dtype=torch.long, device=env.device)
            if not cfg.get("reset_after_resume", False):
                self.count_samples(0, env.clip, env.frame)
        self.hard_exposure = None
        if cfg.get("hard_manifest"):
            from .hard_exposure import HardExposure
            self.hard_exposure = HardExposure(env, cfg.get("world_root_height_mode"))

    def count_samples(self, phase, clip, frame):
        if getattr(self, "hard_exposure", None) is not None:
            self.hard_exposure.count(phase, clip, frame)
        if self.record_sampling:
            remaining = self.env.motions.lengths[clip] - 1 - frame
            bins = torch.bucketize(remaining, remaining.new_tensor([16, 32, 50, 250]), right=False)
            ids = self.env.motions.source_ids[clip] * 5 + bins
            self.sampling_counts[phase].add_(torch.bincount(ids, minlength=len(self.source_names)*5).reshape(-1, 5))

    def save_sampling_counts(self, directory, iteration):
        import json
        directory.mkdir(parents=True, exist_ok=True)
        counts = self.sampling_counts.cpu().tolist()
        result = {"through_iteration": iteration, "remaining_steps_bins": [[1,16],[17,32],[33,50],[51,250],[251,None]],
            "counts": {phase: dict(zip(self.source_names, values)) for phase, values in
                zip(("real_reset", "wm_valid_window_start", "actor_start"), counts)}}
        (directory / f"sampling_{iteration:07d}.json").write_text(json.dumps(result, indent=2)+"\n")
        self.sampling_counts.zero_()
        if self.hard_exposure is not None:
            self.hard_exposure.save(directory, iteration)

    @torch.no_grad()
    def collect(self, steps):
        rewards, failures = [], []
        geometric_count = natural_count = 0
        counts = torch.zeros(len(self.family_names), device=self.env.device)
        failed = torch.zeros_like(counts)
        reset_counts = torch.zeros_like(counts)
        for _ in range(steps):
            window = self.env.motions.window(self.env.clip, self.env.frame, 11) if self.env.motions.cpu_reference else None
            goal = (window.goal(0, goal_frame=self.cfg.get("goal_frame", "reference_heading"), root_quaternion=self.env.sim.qpos[:, 3:7])
                if window else self.env.motions.goal(self.env.clip, self.env.frame,
                goal_frame=self.cfg.get("goal_frame", "reference_heading"), root_quaternion=self.env.sim.qpos[:, 3:7]))
            position_error = actor_root_position_error(self.env.sim.qpos,
                (window.get(0) if window else self.env.motions.get(self.env.clip, self.env.frame))["qpos"],
                self.cfg["actor_root_position_scale_m"]) if self.actor.root_position_feedback else None
            action = self.actor(self.env.history, goal, position_error)
            executed = action + 0.1 * torch.randn_like(action)
            transition = self.env.step(executed, reference=window.get(1) if window else None)
            self.replay.add(transition)
            if self.hard_exposure is not None:
                self.hard_exposure.count(3, transition["clip"], transition["frame"])
            rewards.append(transition["reward"].mean())
            failures.append(transition["terminated"].float().mean())
            family = self.clip_family[transition["clip"]]
            counts.add_(torch.bincount(family, minlength=len(counts)))
            failed.add_(torch.bincount(family[transition["terminated"]], minlength=len(counts)))
            reset_counts.add_(torch.bincount(self.clip_family[self.env.clip[transition["boundary"]]], minlength=len(counts)))
            self.count_samples(0, self.env.clip[transition["boundary"]], self.env.frame[transition["boundary"]])
            geometric_count += int(transition["terminated"].sum())
            natural_count += int(transition["natural_end"].sum())
            self.collected_steps += self.env.num_envs
        return {"sim_step_reward": float(torch.stack(rewards).mean()), "sim_step_termination_fraction": float(torch.stack(failures).mean()),
                "family_transitions": dict(zip(self.family_names, counts.long().tolist())),
                "family_sample_share": dict(zip(self.family_names, (counts / counts.sum()).tolist())),
                "family_failure_count": dict(zip(self.family_names, failed.long().tolist())),
                "family_reset_samples": dict(zip(self.family_names, reset_counts.long().tolist())),
                "real_geometric_terminations": geometric_count, "real_natural_ends": natural_count}

    def fit_world(self):
        cfg = self.cfg
        state_losses, termination_losses, norms = [], [], []
        use_bce = cfg.get("world_termination_loss", "aux_bce") == "aux_bce"
        components = torch.zeros(70, device=self.env.device)
        family_counts = torch.zeros(len(self.family_names), device=self.env.device)
        for _ in range(cfg["world_batches"]):
            sample = self.replay.sample(cfg["world_batch_size"], cfg["world_window"])
            self.count_samples(1, sample["clip"][:, 0], sample["frame"][:, 0])
            reference_window = (self.env.motions.get(sample["clip"], sample["frame"]+1, keys=("qpos",))["qpos"]
                if self.env.motions.cpu_reference and use_bce else None)
            state = sample["state"][:, 0]
            family_counts.add_(torch.bincount(self.clip_family[sample["clip"].flatten()], minlength=len(family_counts)))
            state_loss = term_loss = 0
            for j in range(cfg["world_window"]):
                previous = state
                state = self.world(state, sample["action"][:, j], sample["context"][:, j])
                squared = state_prediction_squared_coordinates(state, sample["next_state"][:, j])
                state_loss = state_loss + squared.mean(-1).mean()
                components.add_(squared.detach().mean(0))
                if use_bce:
                    reference_qpos = (reference_window[:, j] if reference_window is not None else
                        self.env.motions.get(sample["clip"][:, j], sample["frame"][:, j] + 1)["qpos"])
                    logits = self.world.termination_logits(state, reference_qpos)
                    bce = F.binary_cross_entropy_with_logits(logits, sample["terminated"][:, j].float(), reduction="none")
                    term_loss = term_loss + bce.mean()
                if self.hard_exposure is not None:
                    self.hard_exposure.world_error(sample["clip"][:, j], squared, bce,
                        sample["frame"][:, 0], previous, state, sample["state"][:, j], sample["next_state"][:, j])
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

    def improve_policy(self, iteration=None, evidence_directory=None):
        cfg, env = self.cfg, self.env
        sample = self.replay.sample(cfg["imagination_batch_size"])
        state, context, history = sample["state"][:, 0], sample["context"][:, 0], sample["history"]
        clip, frame = sample["clip"][:, 0], sample["frame"][:, 0]
        self.count_samples(2, clip, frame)
        horizon, gamma, lam = cfg["imagination_horizon"], cfg["gamma"], cfg["lambda"]
        window = env.motions.window(clip, frame, horizon+11) if env.motions.cpu_reference else None
        self.world.requires_grad_(False)
        self.critic.requires_grad_(False)
        survival = torch.ones(len(state), device=state.device)
        objective = torch.zeros_like(survival)
        states, goals, critic_references, rewards, deaths, values = [], [], [], [], [], []
        pre_survivals, natural_ends, geometric_probabilities = [], [], []
        for step in range(horizon):
            pre_survivals.append(survival.detach())
            goal = (window.goal(step, goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7])
                if window else env.motions.goal(clip, frame + step,
                goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7]))
            states.append(state.detach())
            goals.append(goal.detach())
            current_ref = (window.get(step) if window else env.motions.get(clip, frame + step))["qpos"]
            critic_references.append(current_ref)
            with torch.no_grad():
                values.append(self.critic(state, goal, context, current_ref))
            position_error = actor_root_position_error(state, current_ref,
                cfg["actor_root_position_scale_m"]) if self.actor.root_position_feedback else None
            action = self.actor(history, goal, position_error)
            predicted = self.world(state, action, context)
            ref = window.get(step+1) if window else env.motions.get(clip, frame + step + 1)
            reward, _, _ = reward_and_termination(env.fk(predicted[:, :36], predicted[:, 36:71]), ref,
                                                  predicted[:, :36], action, state[:, 71:],
                                                  env.sim.soft_lower, env.sim.soft_upper)
            probability = self.world.termination_probability(
                predicted, ref["qpos"], cfg.get("imagination_termination", "learned"),
                cfg.get("termination_smoothing_temperature", 0.05))
            natural_end = frame + step + 1 >= env.motions.lengths[clip] - 1
            if self.hard_exposure is not None:
                self.hard_exposure.actor_height(clip, state, predicted, survival.detach(), natural_end)
            natural_ends.append(natural_end)
            geometric_probabilities.append(probability.detach())
            probability = torch.where(natural_end, torch.ones_like(probability), probability)
            objective = objective + gamma**step * survival * reward
            survival = survival * (1 - probability)
            rewards.append(reward.detach())
            deaths.append(probability.detach())
            state = predicted
            obs = env.observe(state, context, noise=True)
            history = torch.cat((history[:, 1:], obs[:, None]), 1)
        goal_end = (window.goal(horizon, goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7])
            if window else env.motions.goal(clip, frame + horizon,
            goal_frame=cfg.get("goal_frame", "reference_heading"), root_quaternion=state[:, 3:7]))
        terminal_value = self.critic(state, goal_end, context,
            (window.get(horizon) if window else env.motions.get(clip, frame + horizon))["qpos"])
        if cfg.get("record_imagination_evidence", False):
            reward_sum = objective.detach()
            bootstrap = (gamma**horizon * survival * terminal_value).detach()
            terminal_state = state.detach()
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
        weights = torch.stack(pre_survivals).flatten().detach()
        survival_mean = weights.mean().detach()
        losses = []
        raw_losses, weighted_losses, zero_sse, total_sse = [], [], [], []
        for _ in range(cfg["critic_epochs"]):
            indices = torch.randperm(len(targets), device=targets.device)
            for ids in indices.tensor_split(cfg["critic_minibatches"]):
                prediction = self.critic(states[ids], goals[ids], contexts[ids], critic_references[ids])
                squared = (prediction - targets[ids]).square()
                raw = squared.mean()
                weighted = (weights[ids] * squared).mean() / survival_mean
                loss = weighted if cfg.get("critic_loss_mode", "unweighted") == "survival_weighted" else raw
                optimize(loss, self.critic_opt, self.critic.parameters())
                losses.append(float(loss.detach()))
                raw_losses.append(float(raw.detach()))
                weighted_losses.append(float(weighted.detach()))
                zero_sse.append(float(squared.detach()[weights[ids] == 0].sum()))
                total_sse.append(float(squared.detach().sum()))
        metrics = {"imagined_discounted_return": -float(actor_loss.detach()),
                "actor_gradient_norm_before_clip": actor_norm,
                "critic_mse": sum(raw_losses) / len(raw_losses),
                "critic_optimization_objective": sum(losses) / len(losses),
                "raw_critic_mse": sum(raw_losses) / len(raw_losses),
                "survival_weighted_critic_mse": sum(weighted_losses) / len(weighted_losses),
                "survival_mean": float(survival_mean),
                "exact_zero_survival_fraction": float((weights == 0).float().mean()),
                "zero_survival_suffix_squared_error_sum": sum(zero_sse),
                "all_squared_error_sum": sum(total_sse),
                "imagined_survival_at_horizon": float(survival.detach().mean())}
        if cfg.get("record_imagination_evidence", False):
            metrics.update(discounted_survival_reward_sum_mean=float(reward_sum.mean()),
                discounted_terminal_bootstrap_mean=float(bootstrap.mean()),
                terminal_value_mean=float(values[-1].mean()), terminal_value_min=float(values[-1].min()),
                terminal_value_max=float(values[-1].max()),
                terminal_value_fraction_above10=float((values[-1]>10).float().mean()),
                lambda_target_mean=float(targets.mean()), lambda_target_min=float(targets.min()),
                lambda_target_max=float(targets.max()))
            if cfg["capture_selected_training_rollouts"]:
                block = ((iteration-1)//1000+1)*1000
                if getattr(self, "evidence_block", None) != block:
                    self.evidence_block, self.evidence_best_mse = block, -float("inf")
                if metrics["critic_mse"] > self.evidence_best_mse:
                    self.evidence_best_mse = metrics["critic_mse"]
                    from .rollout_evidence import save_selected_rollouts
                    save_selected_rollouts(evidence_directory, block, iteration, env.motions,
                        clip, frame, context, states, terminal_state, critic_references,
                        rewards, deaths, values, targets, reward_sum, bootstrap, metrics["critic_mse"],
                        pre_survivals, natural_ends, geometric_probabilities, window, metrics,
                        cfg.get("world_root_height_mode", "residual"))
        return metrics

    def set_schedule(self, iteration):
        progress = min(iteration / self.cfg["cosine_iterations"], 1.)
        multiplier = 0.03 + 0.97 * (1 + math.cos(math.pi * progress)) / 2
        for optimizer, scale in ((self.actor_opt, self.cfg.get("actor_learning_rate_scale", 1.0)),
                                 (self.world_opt, 1.0), (self.critic_opt, 1.0)):
            for group in optimizer.param_groups:
                group["lr"] = self.cfg["learning_rate"] * multiplier * scale

    def checkpoint(self):
        return {"actor": self.actor.state_dict(), "critic": self.critic.state_dict(), "world_model": self.world.state_dict(),
                "actor_optimizer": self.actor_opt.state_dict(), "critic_optimizer": self.critic_opt.state_dict(),
                "world_optimizer": self.world_opt.state_dict(), "collected_steps": self.collected_steps,
                "replay_saved": False, "resume_requires_fresh_replay_warmup": True,
                **({"hard_exposure": self.hard_exposure.state_dict(), "sampling_counts": self.sampling_counts}
                    if self.hard_exposure is not None else {})}


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
