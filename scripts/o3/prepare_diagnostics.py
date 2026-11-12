"""Read existing O2 checkpoints and console; no Runner, CUDA or inference."""
import argparse
import json
import re
from pathlib import Path
import torch

from common import now, write_json, write_csv
from diagnostics import normalizers_from_state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    run = args.workspace / 'outputs/o2-official-bones-s0'
    output = args.workspace / 'results/20261111-o2-official-bones-s0'
    nodes = json.loads((run / 'nodes.json').read_text())
    normalizer_file = output / 'o3_preparation_normalizers.json'
    if normalizer_file.exists():
        records = json.loads(normalizer_file.read_text())['nodes']
    else:
        records = {}
        for label in ('hour_03', 'hour_06', 'final'):
            payload = torch.load(nodes[label]['checkpoint'], map_location='cpu', weights_only=False)
            records[label] = {'checkpoint': nodes[label]['checkpoint'], 'metadata': payload['metadata'],
                'normalizers': normalizers_from_state(payload)}
            del payload
        write_json(normalizer_file, {'at': now(), 'method': 'CPU existing checkpoint buffers only', 'nodes': records})
    # Console logs are already emitted by the upstream logger. Keep their exact field labels.
    rows = []
    current = {}
    number = r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)'
    for line_number, line in enumerate((run / 'train_official.log').open(errors='replace'), 1):
        if not any(key in line for key in ('Learning iteration', 'reward', 'Reward', 'episode', 'Episode', 'Time elapsed', 'Total steps')):
            continue
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        iteration = re.search(r'Learning iteration\s+(\d+)', clean, re.I)
        if iteration:
            if current:
                rows.append(current)
            current = {'logger_iteration': int(iteration[1])}
        if ':' in clean and re.search(r'episode|reward|total steps', clean, re.I) and not clean.startswith('wandb:'):
            key, value = clean.rsplit(':', 1)
            match = re.search(number, value)
            if match:
                current[key.strip()] = float(match[1])
        if 'Time elapsed:' in clean:
            current['console_elapsed'] = clean.split('Time elapsed:')[-1].strip()
            current['source_line'] = line_number
    if current:
        rows.append(current)
    # Sample existing log records, not simulated trajectories; retain endpoints.
    chosen = rows[::max(1, len(rows)//120)]
    if rows and (not chosen or chosen[-1] != rows[-1]):
        chosen.append(rows[-1])
    stats = [json.loads(line) for line in (run / 'training_stats.jsonl').read_text().splitlines()]
    for record in chosen:
        index = record.get('logger_iteration')
        if index is not None and index < len(stats):
            record.update(collection_steps=stats[index]['collection_steps'], training_seconds=stats[index]['training_seconds'],
                          recorded_at=stats[index]['updated_at'])
    write_json(output / 'o3_preparation_existing_real_metrics.json', {
        'at': now(), 'source': str(run / 'train_official.log'), 'existing_records': len(rows), 'records': chosen,
        'semantics': 'Existing upstream logger episode buffers; hard-reset logger semantics, not formal R or all-done episode statistics',
        'unavailable': ['per-transition motion_end/time_out overlap counts', 'per-episode complete reset accounting'],
        'no_new_runner_inference_or_simulation': True})
    print('O3_PREPARATION_COMPLETED', len(records), len(rows), flush=True)


if __name__ == '__main__':
    main()
