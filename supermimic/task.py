"""Shared actor observation, analytic reward and hard evaluation termination."""
import torch

from .geometry import quat_apply, quat_inv, quat_mul, quat_to_rotvec, yaw_quat


def observation(qpos, qvel, previous_action, q0, calibration_offset):
    gravity = torch.zeros_like(qvel[..., :3])
    gravity[..., 2] = -1
    return torch.cat((qpos[..., 7:] - q0 - calibration_offset, qvel[..., 6:],
                      qvel[..., 3:6], quat_apply(quat_inv(qpos[..., 3:7]), gravity), previous_action), -1)


def reward_and_termination(bodies, reference, qpos, action, previous_action, soft_lower, soft_upper):
    robot_p, robot_q = bodies["body_pos"], bodies["body_quat"]
    ref_p, ref_q = reference["body_pos"], reference["body_quat"]
    # Inherited BeyondMimic relative-body alignment. Root terms remain global.
    delta_q = yaw_quat(quat_mul(robot_q[..., 0, :], quat_inv(ref_q[..., 0, :])))
    anchor = torch.cat((robot_p[..., 0, :2], ref_p[..., 0, 2:3]), -1)
    aligned_p = anchor[..., None, :] + quat_apply(delta_q[..., None, :], ref_p - ref_p[..., :1, :])
    aligned_q = quat_mul(delta_q[..., None, :], ref_q)
    position_error = (robot_p - aligned_p).square().sum(-1).mean(-1)
    rotation_error = quat_to_rotvec(quat_mul(robot_q, quat_inv(aligned_q))).square().sum(-1).mean(-1)
    linear_error = (bodies["body_lin_vel"] - reference["body_lin_vel"]).square().sum(-1).mean(-1)
    angular_error = (bodies["body_ang_vel"] - reference["body_ang_vel"]).square().sum(-1).mean(-1)
    root_pos_error = (robot_p[..., 0, :] - ref_p[..., 0, :]).square().sum(-1)
    root_rot_error = quat_to_rotvec(quat_mul(robot_q[..., 0, :], quat_inv(ref_q[..., 0, :]))).square().sum(-1)
    components = torch.stack((torch.exp(-position_error / 0.3**2), torch.exp(-rotation_error / 0.4**2),
                              torch.exp(-linear_error), torch.exp(-angular_error / 3.14**2),
                              0.5 * torch.exp(-root_pos_error / 0.3**2),
                              0.5 * torch.exp(-root_rot_error / 0.4**2),
                              -0.1 * (action - previous_action).square().sum(-1),
                              -2 * (torch.relu(soft_lower - qpos[..., 7:]) + torch.relu(qpos[..., 7:] - soft_upper)).sum(-1)), -1)
    reward = components.sum(-1) * 0.02
    gravity = torch.zeros_like(robot_p[..., 0, :])
    gravity[..., 2] = -1
    robot_gz = quat_apply(quat_inv(robot_q[..., 0, :]), gravity)[..., 2]
    ref_gz = quat_apply(quat_inv(ref_q[..., 0, :]), gravity)[..., 2]
    height_error = torch.abs(robot_p[..., 0, 2] - ref_p[..., 0, 2])
    tilt_error = torch.abs(robot_gz - ref_gz)
    done = (height_error > 0.25) | (tilt_error > 0.8)
    return reward, done, {
        "components": components * 0.02,
        "root_position_error_m": root_pos_error.sqrt(),
        "root_orientation_error_rad": root_rot_error.sqrt(),
        "relative_body_position_error_m": position_error.sqrt(),
        "root_height_error_m": height_error, "tilt_error": tilt_error,
    }
