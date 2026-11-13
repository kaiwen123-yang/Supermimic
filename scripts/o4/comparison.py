"""Single-run comparisons to O3 anchors, adjacent nodes and frozen analysis groups."""
import json
from common import (CAMPAIGN, PARENT_CAMPAIGN, HISTORICAL_O2_CAMPAIGN,
                    PARENT_SCORE_NODE, CODE_ROOT, write_json)
from metrics import load_scores, compare_nodes, aggregate, groups


def paired_summary(previous, current, output, source):
    result = compare_nodes(previous, current, output)
    old = {r['source_clip_id']: r for r in previous}
    common = [r for r in current if r['completed'] and old[r['source_clip_id']]['completed']]
    result['common_complete_groups'] = {
        'previous': groups([old[r['source_clip_id']] for r in common], source),
        'current': groups(common, source)}
    result['all_clip_groups'] = {'previous': groups(previous, source), 'current': groups(current, source)}
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
    earlier = [(key, node) for key, node in nodes.items()
               if node['metadata']['learning_phases'] < updates]
    if earlier:
        previous_label, _ = max(earlier, key=lambda item: item[1]['metadata']['learning_phases'])
        path = workspace / 'results' / CAMPAIGN / 'milestones' / previous_label / source
        directory = output / 'versus_previous_node'
        write_json(directory / 'comparison.json', {'previous_node': previous_label, 'current_node': label,
                   **paired_summary(load_scores(path), rows, directory, source)})

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
