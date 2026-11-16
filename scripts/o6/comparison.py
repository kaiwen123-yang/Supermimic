"""Actual O6 nodes and historical references; no parent or causal-control labels."""
import json
import numpy as np
from common import CAMPAIGN, CODE_ROOT, write_json
from metrics import load_scores, compare_nodes, aggregate, groups


def paired_summary(previous, current, output, source):
    result = compare_nodes(previous, current, output)
    old = {r['source_clip_id']: r for r in previous}
    common = [r for r in current if r['completed'] and old[r['source_clip_id']]['completed']]
    result['common_complete_groups'] = {
        'previous': groups([old[r['source_clip_id']] for r in common], source),
        'current': groups(common, source)}
    result['all_clip_groups'] = {'previous': groups(previous, source), 'current': groups(current, source)}
    delta = np.asarray([r['normalized_return'] - old[r['source_clip_id']]['normalized_return'] for r in current])
    result['per_clip_return_change'] = {
        'direction': 'current minus previous, matched original source_clip_id',
        'mean': float(delta.mean()), 'improved': int((delta > 0).sum()),
        'decreased': int((delta < 0).sum()), 'unchanged': int((delta == 0).sum()),
        'quantile_levels': [0, .01, .05, .25, .5, .75, .95, .99, 1],
        'quantiles': np.quantile(delta, [0, .01, .05, .25, .5, .75, .95, .99, 1]).tolist(),
        'individual_values': 'derive from the published full per-clip scores using source_clip_id'}
    return result


def compare_evaluation(workspace, nodes, label, source, rows, output):
    historical = CODE_ROOT / 'results'
    o3 = historical / '20261112-o3-official-bones-lr-s0/milestones/quarter'
    anchors = {'O3_quarter_16000': o3 / 'update_16000' / source}
    is_endpoint = 'final' in nodes[label]['aliases']
    if is_endpoint:
        anchors['O3_quarter_32000'] = o3 / 'update_32000' / source
        o5 = historical / '20261115-o5-official-optimizer-s0/milestones'
        for arm, count in [('muon_wd0', 32000), ('adam_wd0', 16000), ('adam_wd0', 32000)]:
            anchors[f'O5_{arm}_{count}'] = o5 / arm / f'update_{count:05d}' / source
        o2 = historical / '20261111-o2-official-bones-s0/milestones'
        for node in ('hour_03', 'hour_06', 'final'):
            anchors['O2_' + node] = o2 / node / source
    for anchor, path in anchors.items():
        directory = output / ('versus_' + anchor)
        write_json(directory / 'comparison.json', {
            'previous_node': anchor, 'current_node': label,
            'comparison_scope': 'historical success overlap; not parent retention or a matched causal control',
            **paired_summary(load_scores(path), rows, directory, source)})
    collections = nodes[label]['metadata']['collection_steps']
    earlier = [key for key, node in nodes.items() if node['metadata']['collection_steps'] < collections]
    if earlier:
        previous = max(earlier, key=lambda key: nodes[key]['metadata']['collection_steps'])
        directory = output / 'versus_previous_node'
        write_json(directory / 'comparison.json', {'previous_node': previous, 'current_node': label,
            **paired_summary(load_scores(workspace / 'results' / CAMPAIGN / 'milestones' / previous / source),
                             rows, directory, source)})
    if source == 'bones_full':
        fixed = json.loads((CODE_ROOT / 'configs/o4_fixed_analysis_groups.json').read_text())
        by_id = {r['source_clip_id']: r for r in rows}
        write_json(output / 'fixed_analysis_groups.json', {
            'definition': 'configs/o4_fixed_analysis_groups.json; historical fixed groups only, no sampling change',
            'groups': {key: aggregate([by_id[i] for i in ids]) for key, ids in fixed.items() if key.endswith('_ids')}})
    if is_endpoint:
        multiway = {key: load_scores(workspace / 'results' / CAMPAIGN / 'milestones' / key / source)
                    for key in earlier}
        multiway[label] = rows
        common = set.intersection(*[{r['source_clip_id'] for r in values if r['completed']}
                                   for values in multiway.values()])
        directory = workspace / 'results' / CAMPAIGN / 'comparisons' / source
        write_json(directory / 'all_actual_O6_common_complete.json', {
            'nodes': list(multiway), 'common_complete_count': len(common),
            'set_definition': 'intersection of completed source_clip_id across every actual unique O6 scoring node',
            'full_library': {key: aggregate(values) for key, values in multiway.items()},
            'common_complete': {key: aggregate([r for r in values if r['source_clip_id'] in common])
                                for key, values in multiway.items()},
            'common_complete_groups': {key: groups([r for r in values if r['source_clip_id'] in common], source)
                                       for key, values in multiway.items()},
            'member_ids_recoverable_from': 'complete published per-clip tables; no per-clip best checkpoint selection'})

