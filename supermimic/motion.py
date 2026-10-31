"""Complete fixed motion library with clip boundaries and physical timestamps."""
from pathlib import Path
import hashlib
import json

import numpy as np
import torch

from .geometry import quat_apply, quat_inv, quat_mul, yaw_quat, rotation_6d


class MotionLibrary:
    def __init__(self, directory: Path, device="cpu"):
        self.manifest_path = directory / "manifest.json"
        self.manifest_hash = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        manifest = json.loads(self.manifest_path.read_text())
        self.names = [c["name"] for c in manifest["clips"]]
        arrays = {key: [] for key in ("qpos", "qvel", "body_pos", "body_quat", "body_lin_vel", "body_ang_vel")}
        offsets, lengths = [], []
        for clip in manifest["clips"]:
            with np.load(directory / (clip["name"] + ".npz")) as data:
                if len(data["qpos"]) != clip["frames"]:
                    raise ValueError(f"Changed length: {clip['name']}")
                offsets.append(sum(lengths))
                lengths.append(clip["frames"])
                for key in arrays:
                    arrays[key].append(data[key])
        self.values = {key: torch.from_numpy(np.concatenate(value)).to(device) for key, value in arrays.items()}
        self.offsets = torch.tensor(offsets, device=device)
        self.lengths = torch.tensor(lengths, device=device)
        self.device = torch.device(device)

    def get(self, clip, frame):
        frame = torch.minimum(torch.maximum(frame, torch.zeros_like(frame)), self.lengths[clip] - 1)
        index = self.offsets[clip] + frame
        return {key: value[index] for key, value in self.values.items()}

    def goal(self, clip, frame, future_frames=10):
        """71 features/frame; reference-relative heading, no robot state estimate.

        This feature layout is an explicit reproduction choice: the paper gives K
        but does not fully enumerate the future-reference feature vector.
        """
        horizon = torch.arange(1, future_frames + 1, device=self.device)
        current = self.get(clip, frame)
        future = self.get(clip[..., None], frame[..., None] + horizon)
        inv_heading = quat_inv(yaw_quat(current["qpos"][..., 3:7]))[..., None, :]
        orientation = quat_mul(inv_heading, future["qpos"][..., 3:7])
        velocity = quat_apply(inv_heading, future["qvel"][..., :3])
        omega = quat_apply(future["qpos"][..., 3:7], future["qvel"][..., 3:6])
        omega = quat_apply(inv_heading, omega)
        features = torch.cat((future["qpos"][..., 7:], future["qvel"][..., 6:] / 10,
                              future["qpos"][..., 2:3], rotation_6d(orientation), velocity / 3, omega / 10), -1)
        return features.flatten(-2)
