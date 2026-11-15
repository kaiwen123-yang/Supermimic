"""Read only the six protocol checkpoints on CPU; no model or environment."""
import argparse
import json
from pathlib import Path
import torch
from common import CAMPAIGN, PROTOCOL_PATH, now, write_json
from optimizer_diagnostics import norm_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--parameter-map', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    mapping = json.loads(args.parameter_map.read_text())
    metadata = {r['network'] + '/' + r['parameter_name']:
                {k: v for k, v in r.items() if k not in ('RMS', 'Frobenius_norm', 'relative_to_initial', 'optimizer_group')}
                for r in mapping['parameters']}
    initial = {r['network'] + '/' + r['parameter_name']: r['Frobenius_norm'] for r in mapping['parameters']}
    protocol = json.loads(PROTOCOL_PATH.read_text())
    output = args.workspace / 'results' / CAMPAIGN / 'historical_o4_weight_norms.json'
    result = {'status': 'reading', 'parameter_map': str(args.parameter_map), 'nodes': [],
              'scope': 'exact six checkpoints, CPU only; group names are structural; historical optimizer state was not saved',
              'relative_norm_reference': 'O3 quarter32k common parent as loaded by normal O5 initialization'}
    for node in protocol['historical_weight_norm_audit']['nodes']:
        try:
            payload = torch.load(node['checkpoint'], map_location='cpu', weights_only=False)
            states = {'wm': payload['world_model']['dynamics'], 'actor': payload['actor'], 'critic': payload['critic']}
            parameters = {key: states[row['network']][row['parameter_name']] for key, row in metadata.items()}
            record = {**node, 'status': 'read', **norm_rows(parameters, metadata, initial)}
            del parameters, states, payload
        except (OSError, RuntimeError, EOFError, KeyError) as error:
            record = {**node, 'status': 'unavailable', 'error': str(error)}
        result['nodes'].append(record)
        result['updated_at'] = now()
        write_json(output, result)
    result['status'] = 'completed'
    write_json(output, result)


if __name__ == '__main__':
    main()
