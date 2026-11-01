"""Inspect a saved termination head's decision surface; not a physics success test."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from supermimic.checkpointing import pin_checkpoint
from supermimic.networks import WorldModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    with pin_checkpoint(args.checkpoint) as pinned:
        checkpoint = torch.load(pinned, map_location="cpu", weights_only=False, mmap=True)
        model = WorldModel().eval()
        model.load_state_dict(checkpoint["world_model"])
        mode = checkpoint["config"].get("imagination_termination", "learned")
        temperature = checkpoint["config"].get("termination_smoothing_temperature", 0.05)
        heights = [0., .1, .2, .249, .251, .3, .4, .5, .75]
        tilts = [0., .4, .79, .81, 1., 1.2, 1.6]
        with torch.no_grad():
            height_probabilities = model.termination_probability_from_features(
                torch.tensor([[h/.25, 0.] for h in heights]), mode, temperature).tolist()
            tilt_probabilities = model.termination_probability_from_features(
                torch.tensor([[0., t/.8] for t in tilts]), mode, temperature).tolist()
            grid = torch.linspace(0., 4., 4001)
            probabilities = model.termination_probability_from_features(
                torch.stack((grid, torch.zeros_like(grid)), -1), mode, temperature)
            hits = grid[probabilities >= .5]
            tilt_probabilities_grid = model.termination_probability_from_features(
                torch.stack((torch.zeros_like(grid), grid), -1), mode, temperature)
            tilt_hits = grid[tilt_probabilities_grid >= .5]
        result = {"iteration": checkpoint["iteration"], "checkpoint_sha256": hashlib.sha256(pinned.read_bytes()).hexdigest(),
                  "imagination_termination": mode, "termination_smoothing_temperature": temperature,
                  "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "scope": "Counterfactual feature grid of the active imagination termination rule; no physical episode or policy-success claim",
                  "actual_hard_height_threshold_m": .25, "actual_hard_gravity_z_threshold": .8,
                  "height_at_zero_tilt": [{"height_error_m": h, "predicted_probability": p, "actual_hard_termination": h > .25}
                                          for h, p in zip(heights, height_probabilities)],
                  "tilt_at_zero_height": [{"gravity_z_error": t, "predicted_probability": p, "actual_hard_termination": t > .8}
                                          for t, p in zip(tilts, tilt_probabilities)],
                  "height_at_first_probability_over_half_m": float(hits[0])*.25 if len(hits) else None,
                  "gravity_z_at_first_probability_over_half": float(tilt_hits[0])*.8 if len(tilt_hits) else None,
                  "height_grid_resolution_m": .00025, "gravity_z_grid_resolution": .0008}
        target = args.checkpoint.absolute().parent / f"termination_boundary_{checkpoint['iteration']:07d}.json"
        target.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
