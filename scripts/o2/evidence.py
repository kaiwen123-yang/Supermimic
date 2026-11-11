"""Bounded same-rollout failure windows; no extra model or physics calls."""
import json

import numpy as np
import torch

from common import write_json
from metrics import HARD_IDS, SKILLS


class FailureWindows:
    def __init__(self, output, batch_size, state, motion, context, origins):
        self.output = output
        self.motion = motion
        self.origins = origins
        self.context = context
        self.records = json.loads((output / "index.json").read_text()) if (output / "index.json").exists() else {}
        self.state = torch.empty((33, *state.shape), device=state.device, dtype=state.dtype)
        self.reference = torch.empty((33, batch_size, 71), device=state.device)
        self.frames = torch.empty((33, batch_size), device=state.device, dtype=torch.long)
        self.action = torch.empty((32, batch_size, 29), device=state.device)
        self.reward = torch.empty((32, batch_size), device=state.device)
        self.put_state(0, state)

    def put_state(self, step, state):
        self.state[step % 33] = state
        frames = self.motion.time_steps
        self.frames[step % 33] = frames
        loader = self.motion.motion
        self.reference[step % 33] = torch.cat([getattr(loader, field)[frames] for field in
            ("root_pos_w", "root_quat_w", "root_lin_vel_w", "root_ang_vel_w", "joint_pos", "joint_vel")], dim=-1)

    def step(self, step, state, actions, rewards, new_failures, clips, reasons, hard_names):
        self.action[(step - 1) % 32] = actions
        self.reward[(step - 1) % 32] = rewards
        self.put_state(step, state)
        for slot in new_failures.nonzero(as_tuple=False).squeeze(-1).tolist():
            clip = clips[slot]
            source_id = clip["source_clip_id"]
            skill = next((key for key in SKILLS if key in clip["name"].lower()), None)
            group = skill or ("other_hard" if source_id in HARD_IDS else "non_hard")
            capacity = 1 if skill else 2
            entries = self.records.setdefault(group, [])
            if len(entries) >= capacity and source_id >= max(e["source_clip_id"] for e in entries):
                continue
            if len(entries) == capacity:
                replace = max(entries, key=lambda e: e["source_clip_id"])
                entries.remove(replace)
                name = replace["file"]
            else:
                name = f"{group}_{len(entries)}.npz"
            k = min(32, step)
            si = torch.arange(step - k, step + 1, device=state.device) % 33
            ti = torch.arange(step - k, step, device=state.device) % 32
            reason = ";".join(n for j, n in enumerate(hard_names) if bool(reasons[slot, j]))
            self.output.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(self.output / name,
                robot_state=self.state[si, slot].cpu().numpy(), reference_state=self.reference[si, slot].cpu().numpy(),
                reference_frame_id=self.frames[si, slot].cpu().numpy(), actions=self.action[ti, slot].cpu().numpy(),
                native_rewards=self.reward[ti, slot].cpu().numpy(), actual_context=self.context[slot].cpu().numpy(),
                env_origin=self.origins[slot].cpu().numpy(), valid_length=np.asarray(k), hard_reason=np.asarray(reason))
            entries.append({"source_clip_id": source_id, "name": clip["name"], "file": name,
                            "valid_length": k, "executed_transitions_at_first_failure": step, "hard_reason": reason})
            entries.sort(key=lambda e: e["source_clip_id"])
        write_needed = bool(new_failures.any())
        if write_needed:
            write_json(self.output / "index.json", self.records)
