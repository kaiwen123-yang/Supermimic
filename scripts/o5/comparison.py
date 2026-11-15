"""Within-arm, matched-budget and fixed multiway comparisons from saved scores."""
import json
import numpy as np
from common import (CAMPAIGN, PARENT_CAMPAIGN, HISTORICAL_O2_CAMPAIGN,
                    HISTORICAL_O4_CAMPAIGN, PARENT_SCORE_NODE, CODE_ROOT, write_json)
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
    # Published parents are available in the synced code worktree, independently
    # of this run's newly generated workspace/results.
    parent_root = CODE_ROOT / 'results' / PARENT_CAMPAIGN / 'milestones'
    anchors = {'O3_quarter_update_32000': parent_root / PARENT_SCORE_NODE / source,
               'O3_quarter_update_16000': parent_root / 'quarter/update_16000' / source}
    for anchor in ('hour_03', 'hour_06'):
        anchors['O2_' + anchor] = CODE_ROOT / 'results' / HISTORICAL_O2_CAMPAIGN / 'milestones' / anchor / source
    for anchor, path in anchors.items():
        previous = load_scores(path)
        directory = output / ('versus_' + anchor)
        write_json(directory / 'comparison.json', {'previous_node': anchor, 'current_node': label,
                   **paired_summary(previous, rows, directory, source)})

    updates = nodes[label]['metadata']['learning_phases']
    arm = nodes[label]['arm']
    earlier = [(key, node) for key, node in nodes.items()
               if node['arm'] == arm and node['metadata']['learning_phases'] < updates]
    if earlier:
        previous_label, _ = max(earlier, key=lambda item: item[1]['metadata']['learning_phases'])
        path = workspace / 'results' / CAMPAIGN / 'milestones' / previous_label / source
        directory = output / 'versus_previous_node'
        write_json(directory / 'comparison.json', {'previous_node': previous_label, 'current_node': label,
                   **paired_summary(load_scores(path), rows, directory, source)})

    historical = (CODE_ROOT / 'results' / HISTORICAL_O4_CAMPAIGN / 'milestones' /
                  'low_lr' / f'update_{updates:05d}' / source)
    if updates in (16000, 32000):
        directory = output / 'versus_historical_O4'
        write_json(directory / 'comparison.json', {'historical_not_concurrent_control': True,
            'previous_node': f'O4/low_lr/update_{updates:05d}', 'current_node': label,
            **paired_summary(load_scores(historical), rows, directory, source)})
    peers = [(key, node) for key, node in nodes.items()
             if node['arm'] != arm and node['metadata']['learning_phases'] == updates]
    for peer_label, peer in peers:
        peer_dir = workspace / 'results' / CAMPAIGN / 'milestones' / peer_label / source
        if not (peer_dir / 'evaluation.json').exists():
            continue
        other = load_scores(peer_dir)
        directory = workspace / 'results' / CAMPAIGN / 'comparisons' / source / f'update_{updates:05d}'
        write_json(directory / 'between_arms.json', {'previous_node': peer_label, 'current_node': label,
            **paired_summary(other, rows, directory, source)})
        if updates in (16000, 32000):
            multiway = {'parent_O3_quarter32k': load_scores(anchors['O3_quarter_update_32000']),
                        'historical_O4': load_scores(historical), arm: rows, peer['arm']: other}
            common = set.intersection(*[{r['source_clip_id'] for r in values if r['completed']}
                                       for values in multiway.values()])
            write_json(directory / 'parent_O4_A_B_common_complete.json', {
                'joint_updates_added': updates, 'common_complete_count': len(common),
                'set_definition': 'intersection of completed source_clip_id in parent, O4 and both O5 arms at this update',
                'full_library': {key: aggregate(values) for key, values in multiway.items()},
                'common_complete': {key: aggregate([r for r in values if r['source_clip_id'] in common])
                                    for key, values in multiway.items()},
                'historical_O4_is_not_concurrent_control': True})

    if source == 'bones_full':
        fixed = json.loads((CODE_ROOT / 'configs/o4_fixed_analysis_groups.json').read_text())
        by_id = {r['source_clip_id']: r for r in rows}
        parent = {r['source_clip_id']: r for r in load_scores(anchors['O3_quarter_update_32000'])}
        summaries = {}
        for name, ids in fixed.items():
            if not name.endswith('_ids'):
                continue
            current = [by_id[i] for i in ids]
            previous = [parent[i] for i in ids]
            directory = output / 'fixed_groups' / name.removesuffix('_ids')
            summaries[name] = paired_summary(previous, current, directory, source)
        retained = [r for r in rows if parent[r['source_clip_id']]['completed']]
        summaries['O3_parent_completed130307'] = {
            'current': aggregate(retained), 'lost_ids': [r['source_clip_id'] for r in retained if not r['completed']]}
        write_json(output / 'fixed_analysis_groups.json', {
            'source': 'configs/o4_fixed_analysis_groups.json',
            'comparison_parent': 'O3 quarter/update_32000', 'training_sampling_unchanged': True,
            'groups': summaries})
