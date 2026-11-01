"""Paper-sized networks and explicit, documented state representation.

Physical state: qpos[36], qvel[35], previous executed action[29].
MLP features remove world XY and canonicalize yaw; physical rollout states remain
in world coordinates for the analytic reward. Feature scales are fixed choices,
not the paper's undisclosed nominal-error normalization.
"""
import torch
from torch import nn
from .geometry import quat_apply, quat_inv, quat_mul, quat_from_rotvec, quat_to_rotvec, yaw_quat, rotation_6d


def mlp(widths, final_gain=1.0):
    layers = []
    for i, (a, b) in enumerate(zip(widths[:-1], widths[1:])):
        linear = nn.Linear(a, b)
        nn.init.xavier_uniform_(linear.weight, gain=final_gain if i == len(widths) - 2 else 1.0)
        nn.init.zeros_(linear.bias)
        layers.append(linear)
        if i != len(widths) - 2:
            layers.append(nn.ELU())
    return nn.Sequential(*layers)


def state_features(state):
    q, v, prev = state[..., :36], state[..., 36:71], state[..., 71:]
    heading_inv = quat_inv(yaw_quat(q[..., 3:7]))
    return torch.cat((q[..., 2:3], rotation_6d(quat_mul(heading_inv, q[..., 3:7])),
                      quat_apply(heading_inv, v[..., :3]) / 3, v[..., 3:6] / 10,
                      q[..., 7:], v[..., 6:] / 10, prev), -1)


def context_features(context):
    return torch.cat(((context[..., :1] - 0.75) / 0.45, context[..., 1:30] / 0.01,
                      context[..., 30:] / 0.05), -1)


class Actor(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = mlp([710, 2048, 1024, 512, 256, 32])
        self.decoder = mlp([930 + 32, 2048, 1024, 512, 256, 29], final_gain=0.01)
        self.register_buffer("observation_scale", torch.tensor([1.] * 29 + [0.1] * 29 + [0.1] * 3 + [1.] * 3 + [1.] * 29))

    def forward(self, history, goal):
        latent = torch.tanh(self.encoder(goal))
        observation = (history * self.observation_scale).flatten(-2)
        return self.decoder(torch.cat((latent, observation), -1))


class Critic(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = mlp([100 + 710 + 33 + 9, 256, 128, 1], final_gain=0.01)

    def forward(self, state, goal, context, reference_qpos):
        # The critic sees the state-relative reference pose; the deployed actor
        # does not. Without this privileged part of g, canonicalization erases
        # the XY/yaw errors needed to predict the global root-tracking return.
        relative_pos = quat_apply(quat_inv(yaw_quat(state[..., 3:7])), reference_qpos[..., :3] - state[..., :3]) / 0.3
        relative_rot = rotation_6d(quat_mul(quat_inv(state[..., 3:7]), reference_qpos[..., 3:7]))
        return self.network(torch.cat((state_features(state), goal, context_features(context), relative_pos, relative_rot), -1)).squeeze(-1)


class WorldModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.dynamics = mlp([100 + 29 + 33, 2048, 2048, 2048, 70], final_gain=0.01)
        self.termination = mlp([2, 256, 128, 1], final_gain=0.01)
        nn.init.constant_(self.termination[-1].bias, -4.0)
        self.register_buffer("position_residual_scale", torch.tensor([0.05] * 3 + [0.1] * 32))
        self.register_buffer("velocity_residual_scale", torch.tensor([1.] * 3 + [3.] * 32))

    def forward(self, state, action, context):
        q, v = state[..., :36], state[..., 36:71]
        heading = yaw_quat(q[..., 3:7])
        prediction = self.dynamics(torch.cat((state_features(state), action, context_features(context)), -1))
        dp = prediction[..., :35] * self.position_residual_scale
        dv = prediction[..., 35:] * self.velocity_residual_scale
        position = q[..., :3] + 0.02 * v[..., :3] + quat_apply(heading, dp[..., :3])
        orientation = quat_mul(q[..., 3:7], quat_from_rotvec(0.02 * v[..., 3:6] + dp[..., 3:6]))
        orientation = orientation / torch.linalg.vector_norm(orientation, dim=-1, keepdim=True).clamp_min(1e-8)
        joints = q[..., 7:] + 0.02 * v[..., 6:] + dp[..., 6:]
        velocity = torch.cat((v[..., :3] + quat_apply(heading, dv[..., :3]), v[..., 3:] + dv[..., 3:]), -1)
        return torch.cat((position, orientation, joints, velocity, action), -1)

    @staticmethod
    def termination_features(state, reference_qpos):
        q = state[..., :36]
        # R_zz = 1 - 2(x^2 + y^2), equal to the gravity-z comparison up to sign.
        height = torch.abs(q[..., 2] - reference_qpos[..., 2]) / 0.25
        tilt = 2 * torch.abs(q[..., 4:6].square().sum(-1) - reference_qpos[..., 4:6].square().sum(-1)) / 0.8
        return torch.stack((height, tilt), -1)

    def termination_logits(self, state, reference_qpos):
        # Both experiment arms retain this learned head and its original BCE
        # objective, including the gradient through predicted states.
        return self.termination(self.termination_features(state, reference_qpos)).squeeze(-1)

    def termination_probability_from_features(self, features, mode="learned", temperature=0.05):
        if mode == "learned":
            return torch.sigmoid(self.termination(features).squeeze(-1))
        if mode != "analytic_smooth" or temperature <= 0:
            raise ValueError("Unknown termination mode or nonpositive smoothing temperature")
        # Smooth OR of the same normalized height and gravity-z thresholds.
        # Temperature 0.05 means 0.0125 m and 0.04 gravity-z units. It is fixed
        # before the experiment; physical collection/evaluation still use hard rules.
        component_probability = torch.sigmoid((features - 1.0) / temperature)
        return 1.0 - (1.0 - component_probability).prod(-1)

    def termination_probability(self, state, reference_qpos, mode="learned", temperature=0.05):
        return self.termination_probability_from_features(
            self.termination_features(state, reference_qpos), mode, temperature)


def state_prediction_error(prediction, target):
    rotation = quat_to_rotvec(quat_mul(prediction[..., 3:7], quat_inv(target[..., 3:7])))
    delta = torch.cat((prediction[..., :3] - target[..., :3], rotation,
                       prediction[..., 7:36] - target[..., 7:36],
                       (prediction[..., 36:39] - target[..., 36:39]) / 3,
                       (prediction[..., 39:71] - target[..., 39:71]) / 10), -1)
    return delta.square().mean(-1)
