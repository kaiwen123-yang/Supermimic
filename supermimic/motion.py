"""Complete fixed motion library with clip boundaries and physical timestamps."""
from pathlib import Path
import json
import re

import numpy as np
import torch

from .geometry import quat_apply, quat_inv, quat_mul, yaw_quat, rotation_6d


def data_definition(manifest):
    """Semantic provenance; preparation duration and host are not input semantics."""
    definition = {"source": {k: manifest["dataset"][k] for k in ("repo", "revision")},
            "clips": [{k: c[k] for k in ("name", "frames")} for c in manifest["clips"]],
            "control_hz": 50, "joint_order": manifest["joint_order"],
            "body_order": manifest["body_order"],
            "preprocessing_version": manifest.get("preprocessing_version", "lafan-g1-linear-slerp-central-xbody-v1")}
    if "sources" in manifest:
        definition["sources"] = manifest["sources"]
        for target, clip in zip(definition["clips"], manifest["clips"]):
            target["source"] = clip["source"]
    return definition


def checkpoint_data_definition(checkpoint):
    if "data_definition" in checkpoint:
        return checkpoint["data_definition"]
    # Historical checkpoints used this fixed preparation, including runtime fields.
    historical = Path(__file__).resolve().parents[1] / "results/lafan1_g1_preparation/motion_manifest.json"
    return data_definition(json.loads(historical.read_text()))


class MotionLibrary:
    def __init__(self, directory: Path, device="cpu", storage="device"):
        self.manifest_path = directory / "manifest.json"
        manifest = json.loads(self.manifest_path.read_text())
        self.data_definition = data_definition(manifest)
        self.names = [c["name"] for c in manifest["clips"]]
        self.original_names = [c.get("original_name", c["name"]) for c in manifest["clips"]]
        self.source_names = list(manifest.get("sources", {"lafan": {}}))
        self.source_ids = torch.tensor([self.source_names.index(c.get("source", "lafan")) for c in manifest["clips"]], device=device)
        self.families = [c["category"] if "category" in c else re.match(r"[A-Za-z]+", c["name"])[0] for c in manifest["clips"]]
        lengths = [c["frames"] for c in manifest["clips"]]
        offsets = np.concatenate(([0], np.cumsum(lengths[:-1], dtype=np.int64)))
        keys = ("qpos", "qvel", "body_pos", "body_quat", "body_lin_vel", "body_ang_vel")
        self.cpu_reference = storage == "cpu_memmap"
        if self.cpu_reference:
            store = manifest["reference_store"]
            self.values = {key: np.load(Path(store["directory"])/(key+".npy"), mmap_mode="r") for key in keys}
            offsets += store["offset"]
        else:
            with np.load(directory / (manifest["clips"][0]["name"] + ".npz")) as first:
                self.values = {key: torch.empty((sum(lengths), *first[key].shape[1:]), dtype=torch.float32, device=device) for key in keys}
            for clip, offset in zip(manifest["clips"], offsets):
                with np.load(directory / (clip["name"] + ".npz")) as data:
                    if len(data["qpos"]) != clip["frames"]:
                        raise ValueError(f"Changed length: {clip['name']}")
                    for key in keys:
                        self.values[key][int(offset):int(offset)+clip["frames"]].copy_(torch.from_numpy(data[key]))
        self.offsets = torch.tensor(offsets, device=device)
        self.lengths = torch.tensor(lengths, device=device)
        self.device = torch.device(device)

    def configure_hard_set(self, hard_manifest, bones_directory):
        frozen = json.loads(Path(hard_manifest).read_text())
        bones = json.loads((Path(bones_directory) / "manifest.json").read_text())["clips"]
        # Resolve frozen original BONES ids through source metadata, never an offset.
        source_ids = {c["name"]: i for i, c in enumerate(bones)}
        hard_ids = {row["source_clip_id"] for row in frozen["members"]}
        sources = self.source_ids.cpu().tolist()
        self.original_source_clip_ids = [source_ids[name] if sources[i] == self.source_names.index("bones") else None
            for i, name in enumerate(self.original_names)]
        self.hard_mask = torch.tensor([i in hard_ids if i is not None else False
            for i in self.original_source_clip_ids], device=self.device)

    def get(self, clip, frame, keys=None):
        frame = torch.minimum(torch.maximum(frame, torch.zeros_like(frame)), self.lengths[clip] - 1)
        index = self.offsets[clip] + frame
        selected = self.values if keys is None else {key:self.values[key] for key in keys}
        if self.cpu_reference:
            index = index.cpu().numpy()
            return {key: torch.from_numpy(value[index]).to(self.device) for key, value in selected.items()}
        return {key: value[index] for key, value in selected.items()}

    def window(self, clip, frame, frames):
        horizon = torch.arange(frames, device=self.device)
        return ReferenceWindow(self.get(clip[:,None], frame[:,None]+horizon))

    def goal(self, clip, frame, future_frames=10, *, goal_frame="reference_heading", root_quaternion=None):
        """71 features/frame in reference heading or current robot root coordinates.

        This feature layout is an explicit reproduction choice: the paper gives K
        but does not fully enumerate the future-reference feature vector.
        """
        horizon = torch.arange(1, future_frames + 1, device=self.device)
        current = self.get(clip, frame)
        future = self.get(clip[..., None], frame[..., None] + horizon)
        return reference_goal(current, future, goal_frame, root_quaternion)


class ReferenceWindow:
    """One explicit phase's bounded GPU reference, without cached robot goals."""
    def __init__(self, values):
        self.values = values

    def get(self, step):
        return {key:value[:,step] for key,value in self.values.items()}

    def goal(self, step, future_frames=10, *, goal_frame, root_quaternion):
        future = {key:value[:,step+1:step+future_frames+1] for key,value in self.values.items()}
        return reference_goal(self.get(step), future, goal_frame, root_quaternion)


def reference_goal(current, future, goal_frame, root_quaternion):
    if goal_frame == "reference_heading":
        coordinate = yaw_quat(current["qpos"][..., 3:7])
    elif goal_frame == "robot_root":
        coordinate = root_quaternion
    else:
        raise ValueError(f"Unknown goal frame: {goal_frame}")
    # No detach: every imagined root orientation carries Actor gradients.
    inv_heading = quat_inv(coordinate)[..., None, :]
    orientation = quat_mul(inv_heading, future["qpos"][..., 3:7])
    velocity = quat_apply(inv_heading, future["qvel"][..., :3])
    omega = quat_apply(future["qpos"][..., 3:7], future["qvel"][..., 3:6])
    omega = quat_apply(inv_heading, omega)
    features = torch.cat((future["qpos"][..., 7:], future["qvel"][..., 6:] / 10,
                          future["qpos"][..., 2:3], rotation_6d(orientation), velocity / 3, omega / 10), -1)
    return features.flatten(-2)
