"""All actual nodes versus existing O2 anchors and matched new-update nodes."""
import json
from common import CAMPAIGN, PARENT_CAMPAIGN, CODE_ROOT, write_json
from metrics import load_scores, compare_nodes, aggregate


def compare_evaluation(workspace, nodes, label, source, rows, output):
    parent_root = workspace / 'results' / PARENT_CAMPAIGN / 'milestones'
    for anchor in ('hour_03', 'hour_06'):
        previous = load_scores(parent_root / anchor / source)
        directory = output / ('versus_O2_' + anchor)
        write_json(directory / 'comparison.json', compare_nodes(previous, rows, directory))
    if source == 'bones_full':
        # Load the previously published identity lists; do not change training sampling.
        review = json.loads((CODE_ROOT / 'results' / PARENT_CAMPAIGN / 'review_per_clip_20261112.json').read_text())
        failures = {r['source_clip_id'] for r in review['hour_03_failed_clips']}
        common = set(review['paired']['hour_03_to_hour_06']['both_failed_ids'])
        write_json(output / 'fixed_parent_failure_groups.json', {
            'existing_review_source': f'results/{PARENT_CAMPAIGN}/review_per_clip_20261112.json',
            'existing_review_sections': list(review),
            'parent_179_ids': sorted(failures), 'common_57_ids': sorted(common),
            'parent_179': aggregate([r for r in rows if r['source_clip_id'] in failures]),
            'common_57': aggregate([r for r in rows if r['source_clip_id'] in common])})
    updates = nodes[label]['metadata']['learning_phases']
    for other, node in nodes.items():
        if node['arm'] == nodes[label]['arm'] or node['metadata']['learning_phases'] != updates:
            continue
        previous = workspace / 'results' / CAMPAIGN / 'milestones' / other / source
        if (previous / 'evaluation.json').exists():
            directory = workspace / 'results' / CAMPAIGN / 'paired' / f'update_{updates:05d}' / source
            old = load_scores(previous)
            control, quarter = (old, rows) if nodes[label]['arm'] == 'quarter' else (rows, old)
            write_json(directory / 'comparison.json', {'new_joint_updates': updates, 'previous_arm': 'control',
                'current_arm': 'quarter', **compare_nodes(control, quarter, directory)})
