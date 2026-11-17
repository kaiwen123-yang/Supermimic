"""O7/O6 matched-node and O7 late-retention comparisons from existing scores."""
import numpy as np
from common import CAMPAIGN, CODE_ROOT, write_json
from metrics import load_scores, compare_nodes, aggregate, groups, NAME_GROUPS, HARD_IDS, SKILLS


def change_distribution(previous, current):
    old = {r['source_clip_id']: r for r in previous}
    quantiles = [0, .01, .05, .25, .5, .75, .95, .99, 1]
    result = {}
    for field in ('normalized_return', 'root_xy_error_m', 'relative_body_orientation_error_rad'):
        delta = np.asarray([r[field] - old[r['source_clip_id']][field] for r in current])
        result[field] = {'direction': 'current minus previous', 'count': len(delta),
                         'improvement_direction': 'positive' if field == 'normalized_return' else 'negative'}
        if len(delta):
            result[field].update(mean=float(delta.mean()), positive=int((delta > 0).sum()),
                negative=int((delta < 0).sum()), unchanged=int((delta == 0).sum()),
                quantile_levels=quantiles, quantiles=np.quantile(delta, quantiles).tolist())
    return result


def paired_summary(previous, current, output, source):
    result = compare_nodes(previous, current, output)
    old = {r['source_clip_id']: r for r in previous}
    common = [r for r in current if r['completed'] and old[r['source_clip_id']]['completed']]
    common_old = [old[r['source_clip_id']] for r in common]
    result['common_complete_groups'] = {'previous': groups(common_old, source), 'current': groups(common, source)}
    result['all_clip_groups'] = {'previous': groups(previous, source), 'current': groups(current, source)}
    result['all_clip_change_distribution'] = change_distribution(previous, current)
    result['common_complete_change_distribution'] = change_distribution(common_old, common)
    identities = {'recovered': [], 'new_failures': [], 'persistent_failures': []}
    for row in current:
        before = old[row['source_clip_id']]
        if before['completed'] and row['completed']:
            continue
        name = ('recovered' if row['completed'] else
                'new_failures' if before['completed'] else 'persistent_failures')
        identities[name].append({'source_clip_id': row['source_clip_id'], 'name': row['name'],
            'previous_return': before['normalized_return'], 'current_return': row['normalized_return'],
            'previous_complete': before['completed'], 'current_complete': row['completed']})
    write_json(output / 'failure_identities.json', identities)
    result['failure_identities'] = 'failure_identities.json'
    result['persistent_failures'] = len(identities['persistent_failures'])
    return result


def compare_evaluation(workspace, nodes, label, source, rows, output):
    historical = CODE_ROOT / 'results'
    o6_root = historical / '20261116-o6-official-adam-cosine-s0/milestones'
    collection = nodes[label]['metadata']['collection_steps']
    matched_label = f'collection_{collection:06d}'
    baseline = o6_root / matched_label / source
    if (baseline / 'per_clip_index.json').exists():
        directory = output / 'versus_O6_same_collection'
        write_json(directory / 'comparison.json', {
            'previous_node': 'O6/' + matched_label, 'current_node': 'O7/' + label,
            'baseline_result_commit': '8f23f4b26fc84598dc19429963ddb8cd18cd37ee',
            'comparison_scope': 'Same collection budget, fresh seed0 Adam/cosine recipe and project members; '
                                'removing the Gaussian draw also changes subsequent RNG consumption.',
            **paired_summary(load_scores(baseline), rows, directory, source)})
    else:
        write_json(output / 'matched_baseline_unavailable.json', {
            'collection': collection, 'reason': 'No O6 formal node at this actual collection; no old replay or fabricated pairing.'})
    earlier = [key for key, node in nodes.items() if node['metadata']['collection_steps'] < collection]
    if earlier:
        previous = max(earlier, key=lambda key: nodes[key]['metadata']['collection_steps'])
        directory = output / 'versus_previous_node'
        write_json(directory / 'comparison.json', {'previous_node': previous, 'current_node': label,
            **paired_summary(load_scores(workspace / 'results' / CAMPAIGN / 'milestones' / previous / source),
                             rows, directory, source)})
    if source == 'bones_full':
        member_groups = {name: [r['source_clip_id'] for r in rows if name in r['name'].lower()]
                         for name in NAME_GROUPS + SKILLS}
        member_groups['hard639'] = [r['source_clip_id'] for r in rows if r['source_clip_id'] in HARD_IDS]
        member_groups['long_motions_at_least60s'] = [r['source_clip_id'] for r in rows if r['reference_transitions'] >= 3000]
        write_json(output / 'fixed_group_members.json', {
            'definition': 'All members, not only failures; duration=reference_transitions/50. No dataset filtering.',
            'counts': {key: len(ids) for key, ids in member_groups.items()}, 'source_clip_ids': member_groups})
    if 'final' in nodes[label]['aliases']:
        historical_muon = historical / '20261115-o5-official-optimizer-s0/milestones/muon_wd0/update_32000' / source
        directory = output / 'versus_O5_muon_32000'
        write_json(directory / 'comparison.json', {
            'previous_node': 'O5/muon_wd0/update_32000', 'current_node': 'O7/' + label,
            'comparison_scope': 'Historical capability reference only; not a matched optimizer/noise experiment.',
            **paired_summary(load_scores(historical_muon), rows, directory, source)})
        multiway = {key: load_scores(workspace / 'results' / CAMPAIGN / 'milestones' / key / source)
                    for key in earlier}
        multiway[label] = rows
        common = set.intersection(*[{r['source_clip_id'] for r in values if r['completed']}
                                   for values in multiway.values()])
        directory = workspace / 'results' / CAMPAIGN / 'comparisons' / source
        write_json(directory / 'all_actual_O7_common_complete.json', {
            'nodes': list(multiway), 'common_complete_count': len(common),
            'set_definition': 'Completed source_clip_id intersection across every actual unique O7 scoring node.',
            'full_library': {key: aggregate(values) for key, values in multiway.items()},
            'common_complete': {key: aggregate([r for r in values if r['source_clip_id'] in common])
                                for key, values in multiway.items()},
            'common_complete_groups': {key: groups([r for r in values if r['source_clip_id'] in common], source)
                                       for key, values in multiway.items()},
            'member_ids_recoverable_from': 'Complete published per-clip tables; no per-clip best checkpoint selection.'})
