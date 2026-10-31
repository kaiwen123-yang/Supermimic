"""Direct MuJoCo Warp control adapter; physics never participates in autograd."""
from __future__ import annotations

import numpy as np
import torch
import warp as wp
import mujoco_warp as mjw

from .robot import load_model, joint_arrays


class G1Simulator:
    def __init__(self, num_envs: int, device="cuda:0"):
        self.device = torch.device(device)
        self.num_envs = num_envs
        self.host_model = load_model()
        wp.init()
        # Capture on a Warp-owned non-default stream. CUDA graph capture on the
        # imported PyTorch legacy/default stream is not supported by this runtime.
        self.stream = wp.get_stream(str(self.device))
        self.torch_stream = wp.stream_to_torch(self.stream)
        with wp.ScopedStream(self.stream):
            self.model = mjw.put_model(self.host_model, batch_sizes={"geom_friction": num_envs, "body_ipos": num_envs})
            self.data = mjw.make_data(self.host_model, nworld=num_envs, nconmax=96, njmax=512)
            self.qpos = wp.to_torch(self.data.qpos)
            self.qvel = wp.to_torch(self.data.qvel)
            self.ctrl = wp.to_torch(self.data.ctrl)
            self.warmstart = wp.to_torch(self.data.qacc_warmstart)
            self.time = wp.to_torch(self.data.time)
            # Compile physical kernels before graph capture.
            mjw.forward(self.model, self.data)
            mjw.step(self.model, self.data)
            with wp.ScopedCapture() as capture:
                for _ in range(4):
                    mjw.step(self.model, self.data)
                # mj_step leaves derived positions at the pre-integration state.
                mjw.forward(self.model, self.data)
            self.graph = capture.graph
        torch.cuda.current_stream(self.device).wait_stream(self.torch_stream)
        p = joint_arrays()
        self.q0 = torch.tensor(p["q0"], dtype=torch.float32, device=device)
        self.action_scale = torch.tensor(p["action_scale"], dtype=torch.float32, device=device)
        self.context = torch.zeros((num_envs, 33), device=device)
        self.context[:, 0] = 1
        self.nominal_ipos = torch.tensor(self.host_model.body_ipos.copy(), dtype=torch.float32, device=device)
        self.torso_id = self.host_model.body("torso_link").id
        self.foot_ids = [i for i in range(self.host_model.ngeom) if "_foot" in (self.host_model.geom(i).name or "")]
        limits = self.host_model.jnt_range[1:]
        mid, half = limits.mean(-1), (limits[:, 1] - limits[:, 0]) * 0.9 / 2
        self.soft_lower = torch.tensor(mid - half, dtype=torch.float32, device=device)
        self.soft_upper = torch.tensor(mid + half, dtype=torch.float32, device=device)

    @torch.no_grad()
    def reset(self, qpos, qvel, ids=None, randomize=False):
        if ids is None:
            ids = torch.arange(self.num_envs, device=self.device)
        self.qpos[ids] = qpos
        self.qvel[ids] = qvel
        self.warmstart[ids] = 0
        self.time[ids] = 0
        count = len(ids)
        self.context[ids] = 0
        self.context[ids, 0] = 1
        if randomize:
            self.context[ids, 0] = 0.3 + 0.9 * torch.rand(count, device=self.device)
            self.context[ids, 1:30] = (torch.rand(count, 29, device=self.device) * 2 - 1) * 0.01
            self.context[ids, 30:] = (torch.rand(count, 3, device=self.device) * 2 - 1) * torch.tensor([0.025, 0.05, 0.05], device=self.device)
        friction = wp.to_torch(self.model.geom_friction)
        friction[ids[:, None], torch.tensor(self.foot_ids, device=self.device)[None, :], 0] = self.context[ids, :1]
        ipos = wp.to_torch(self.model.body_ipos)
        ipos[ids, self.torso_id] = self.nominal_ipos[self.torso_id] + self.context[ids, 30:]
        self.ctrl[ids] = self.q0 + self.context[ids, 1:30]

    @torch.no_grad()
    def step(self, action):
        caller_stream = torch.cuda.current_stream(self.device)
        self.torch_stream.wait_stream(caller_stream)
        with torch.cuda.stream(self.torch_stream):
            self.ctrl.copy_(self.q0 + self.context[:, 1:30] + self.action_scale * action)
            # Reset solver cache at each control step, making its omission from
            # learned state explicit rather than retaining hidden solver history.
            self.warmstart.zero_()
            with wp.ScopedStream(self.stream):
                wp.capture_launch(self.graph)
        caller_stream.wait_stream(self.torch_stream)
        return self.qpos, self.qvel
