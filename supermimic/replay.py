"""Per-environment ring replay; no windows cross actual episode boundaries."""
import torch


class Replay:
    def __init__(self, capacity, environments, device):
        self.capacity, self.environments, self.device = capacity, environments, device
        self.total = 0
        self.values = {}
        for name, width, dtype in (("state", 100, torch.float32), ("next_state", 100, torch.float32),
                                   ("action", 29, torch.float32), ("context", 33, torch.float32),
                                   ("observation", 93, torch.float32), ("clip", None, torch.int32),
                                   ("frame", None, torch.int32), ("episode", None, torch.int64),
                                   ("terminated", None, torch.bool)):
            shape = (capacity, environments) + (() if width is None else (width,))
            self.values[name] = torch.empty(shape, dtype=dtype, device=device)

    @torch.no_grad()
    def add(self, transition):
        slot = self.total % self.capacity
        for key in self.values:
            self.values[key][slot].copy_(transition[key])
        self.total += 1

    def sample(self, count, window=1):
        oldest = max(0, self.total - self.capacity)
        low, high = oldest + 9, self.total - window + 1
        if high <= low:
            raise RuntimeError("Replay needs at least history+window contiguous steps")
        accepted_t, accepted_e, remaining = [], [], count
        for _ in range(16):
            size = max(remaining * 2, 64)
            t = torch.randint(low, high, (size,), device=self.device)
            e = torch.randint(self.environments, (size,), device=self.device)
            first_episode = self.values["episode"][t % self.capacity, e]
            last_episode = self.values["episode"][(t + window - 1) % self.capacity, e]
            valid = first_episode == last_episode
            t, e = t[valid][:remaining], e[valid][:remaining]
            accepted_t.append(t)
            accepted_e.append(e)
            remaining -= len(t)
            if remaining == 0:
                break
        if remaining:
            raise RuntimeError(f"Insufficient continuous replay: missing {remaining} windows")
        t, e = torch.cat(accepted_t), torch.cat(accepted_e)
        index = (t[:, None] + torch.arange(window, device=self.device)) % self.capacity
        result = {key: value[index, e[:, None]] for key, value in self.values.items()}
        hi = (t[:, None] + torch.arange(-9, 1, device=self.device)) % self.capacity
        history = self.values["observation"][hi, e[:, None]]
        same_episode = self.values["episode"][hi, e[:, None]] == result["episode"][:, :1]
        first_valid = same_episode.long().argmax(-1)
        initial_obs = history[torch.arange(count, device=self.device), first_valid]
        result["history"] = torch.where(same_episode[..., None], history, initial_obs[:, None])
        result["clip"] = result["clip"].long()
        result["frame"] = result["frame"].long()
        return result
