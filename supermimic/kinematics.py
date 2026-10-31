"""Batched differentiable FK and body-origin velocities from the compiled model."""
from __future__ import annotations

import mujoco
import torch
from torch import nn

from .geometry import quat_apply, quat_mul, quat_from_rotvec
from .robot import TRACKED_BODIES


class ForwardKinematics(nn.Module):
    def __init__(self, model: mujoco.MjModel):
        super().__init__()
        self.parents = model.body_parentid.tolist()
        self.body_joint = []
        self.q_indices = []
        self.v_indices = []
        for body in range(model.nbody):
            count = int(model.body_jntnum[body])
            if count > 1:
                raise ValueError("The locked G1 has at most one joint per body")
            jid = int(model.body_jntadr[body]) if count else -1
            self.body_joint.append(jid)
            self.q_indices.append(int(model.jnt_qposadr[jid]) if count else -1)
            self.v_indices.append(int(model.jnt_dofadr[jid]) if count else -1)
            if count and body != 1 and model.jnt_type[jid] != mujoco.mjtJoint.mjJNT_HINGE:
                raise ValueError("Expected a G1 hinge joint")
        for name, value in (("body_pos", model.body_pos), ("body_quat", model.body_quat),
                            ("joint_axis", model.jnt_axis), ("joint_pos", model.jnt_pos), ("qpos0", model.qpos0)):
            self.register_buffer(name, torch.as_tensor(value.copy(), dtype=torch.float64))
        self.tracked_ids = [model.body(name).id for name in TRACKED_BODIES]

    def forward(self, qpos, qvel):
        zero = torch.zeros_like(qpos[..., :3])
        identity = torch.cat((torch.ones_like(qpos[..., :1]), zero), -1)
        positions, quaternions, velocities, angular = [zero], [identity], [zero], [zero]
        for body in range(1, len(self.parents)):
            if body == 1:
                positions.append(qpos[..., :3])
                quaternions.append(qpos[..., 3:7])
                velocities.append(qvel[..., :3])
                angular.append(quat_apply(qpos[..., 3:7], qvel[..., 3:6]))
                continue
            parent = self.parents[body]
            pp, pq, pv, pw = positions[parent], quaternions[parent], velocities[parent], angular[parent]
            before_pos = pp + quat_apply(pq, self.body_pos[body].expand_as(pp))
            before_quat = quat_mul(pq, self.body_quat[body].expand_as(pq))
            jid = self.body_joint[body]
            if jid < 0:
                p, q, w = before_pos, before_quat, pw
                v = pv + torch.linalg.cross(pw, p - pp)
            else:
                qi, vi = self.q_indices[body], self.v_indices[body]
                offset = self.joint_pos[jid].expand_as(pp)
                axis = self.joint_axis[jid].expand_as(pp)
                anchor = before_pos + quat_apply(before_quat, offset)
                q = quat_mul(before_quat, quat_from_rotvec(axis * (qpos[..., qi:qi+1] - self.qpos0[qi])))
                p = anchor - quat_apply(q, offset)
                joint_w = quat_apply(before_quat, axis) * qvel[..., vi:vi+1]
                w = pw + joint_w
                v = pv + torch.linalg.cross(pw, p - pp) + torch.linalg.cross(joint_w, p - anchor)
            positions.append(p)
            quaternions.append(q)
            velocities.append(v)
            angular.append(w)
        ids = self.tracked_ids
        return {
            "body_pos": torch.stack([positions[i] for i in ids], -2),
            "body_quat": torch.stack([quaternions[i] for i in ids], -2),
            "body_lin_vel": torch.stack([velocities[i] for i in ids], -2),
            "body_ang_vel": torch.stack([angular[i] for i in ids], -2),
        }
