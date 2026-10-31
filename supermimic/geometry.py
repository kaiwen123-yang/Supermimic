"""Differentiable rotations in scalar-first (w, x, y, z) convention."""
import torch


def quat_mul(a, b):
    av, bv = a[..., 1:], b[..., 1:]
    return torch.cat((a[..., :1] * b[..., :1] - (av * bv).sum(-1, keepdim=True),
                      a[..., :1] * bv + b[..., :1] * av + torch.linalg.cross(av, bv)), -1)


def quat_inv(q):
    return torch.cat((q[..., :1], -q[..., 1:]), -1)


def quat_apply(q, v):
    qv, v = torch.broadcast_tensors(q[..., 1:], v)
    uv = torch.linalg.cross(qv, v)
    return v + 2 * (q[..., :1] * uv + torch.linalg.cross(qv, uv))


def quat_from_rotvec(v):
    angle = torch.linalg.vector_norm(v, dim=-1, keepdim=True)
    return torch.cat((torch.cos(angle / 2), 0.5 * torch.sinc(angle / (2 * torch.pi)) * v), -1)


def quat_to_rotvec(q):
    q = torch.where(q[..., :1] < 0, -q, q)
    norm = torch.linalg.vector_norm(q[..., 1:], dim=-1, keepdim=True)
    angle = 2 * torch.atan2(norm, q[..., :1])
    factor = torch.where(norm > 1e-7, angle / norm.clamp_min(1e-7), 2 * torch.ones_like(norm))
    return factor * q[..., 1:]


def yaw_quat(q):
    w, x, y, z = q.unbind(-1)
    yaw = torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    zero = torch.zeros_like(yaw)
    return torch.stack((torch.cos(yaw / 2), zero, zero, torch.sin(yaw / 2)), -1)


def rotation_6d(q):
    e1 = torch.zeros_like(q[..., 1:])
    e1[..., 0] = 1
    e2 = torch.zeros_like(e1)
    e2[..., 1] = 1
    return torch.cat((quat_apply(q, e1), quat_apply(q, e2)), -1)
