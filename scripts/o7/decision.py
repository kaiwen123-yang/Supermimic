"""Readable O7 conclusions from already generated paired-score summaries."""
from common import read_json, write_json


def group_rows(groups):
    return {'hard639': groups['fixed_hard639'], 'nonhard': groups['non_hard'],
            **groups['skills'], **groups['named_groups'],
            'long>=60s': groups['long_motions_at_least60s']}


def matched_node_conclusion(result, nodes):
    lines = ['', '## O6/O7 at the same completed collection count', '',
             '| Collection | Library | O6 R | O7 R | O6/O7 failed | Recovered/new/persistent failed | Common n | Common R O6→O7 | Common XY/m O6→O7 | Common body orientation/rad O6→O7 |',
             '|---:|---|---:|---:|---:|---|---:|---|---|---|']
    pairs = {}
    for label in nodes:
        for source in ('bones_full', 'lafan40_cross_library'):
            path = result / 'milestones' / label / source / 'versus_O6_same_collection/comparison.json'
            pair = read_json(path)
            if pair is None:
                continue
            pairs[label + '/' + source] = pair
            old, new = pair['all_clip_previous'], pair['all_clip_current']
            a, b = pair['common_complete']['previous'], pair['common_complete']['current']
            r = xy = ori = 'no common completions'
            if b['clip_count']:
                r = f"{a['mean_normalized_return']:.8f}→{b['mean_normalized_return']:.8f}"
                xy = f"{a['quality']['root_xy_error_m']:.6f}→{b['quality']['root_xy_error_m']:.6f}"
                ori = f"{a['quality']['relative_body_orientation_error_rad']:.6f}→{b['quality']['relative_body_orientation_error_rad']:.6f}"
            lines.append(f"| {nodes[label]['metadata']['collection_steps']} | {source} | {old['mean_normalized_return']:.8f} | {new['mean_normalized_return']:.8f} | {old['failed']}/{new['failed']} | {pair['new_completions']}/{pair['lost_completions']}/{pair['persistent_failures']} | {b['clip_count']} | {r} | {xy} | {ori} |")
    key = 'collection_320000/bones_full'
    final = pairs.get(key)
    if final:
        old, new = final['all_clip_previous'], final['all_clip_current']
        a, b = final['common_complete']['previous'], final['common_complete']['current']
        old_groups, new_groups = (group_rows(final['all_clip_groups'][side]) for side in ('previous', 'current'))
        lines += ['', '| Full fixed group | N | O6/O7 complete | O6 R | O7 R |',
                  '|---|---:|---:|---:|---:|']
        for name in old_groups:
            g, h = old_groups[name], new_groups[name]
            lines.append(f"| {name} | {h['clip_count']} | {g['completed']}/{h['completed']} | {g['mean_normalized_return']:.8f} | {h['mean_normalized_return']:.8f} |")
        if b['clip_count']:
            precision_retained = (b['mean_normalized_return'] >= a['mean_normalized_return'] and
                                  b['quality']['root_xy_error_m'] <= a['quality']['root_xy_error_m'])
            monkey_gain = new_groups['monkey_jump']['completed'] - old_groups['monkey_jump']['completed']
            failed_delta = new['failed'] - old['failed']
            if failed_delta < 0 and precision_retained and monkey_gain > 0:
                assessment = 'Lower final failure count, retained common-set R/XY and improved monkey coverage support the stated benefit in this seed and recipe.'
            elif failed_delta < 0 and precision_retained:
                assessment = 'Final coverage improves while common-set R/XY are retained; the monkey coverage gap did not improve. Report that distinction.'
            elif failed_delta == 0 and precision_retained:
                assessment = 'Final failure count is unchanged with common-set R/XY retained. There is no reduction in overall failures; group and identity changes remain relevant.'
            else:
                assessment = 'The final node does not jointly reduce failures and retain both common-set R and XY. Report the individual coverage/precision changes as the result.'
            decision = {'assessment': assessment, 'O7_minus_O6_failed': failed_delta,
                        'common_R_XY_retained': precision_retained, 'monkey_complete_gain': monkey_gain,
                        'full_library_return_delta': new['mean_normalized_return'] - old['mean_normalized_return'],
                        'common_complete': final['common_complete'],
                        'fixed_group_previous_current': final['all_clip_groups'],
                        'scope': 'Fixed final320k; all matched nodes and O7 late phase reported separately. No automatic O8.'}
            write_json(result / 'noise_removal_decision.json', decision)
            lines += ['', assessment]
    late = read_json(result / 'milestones/collection_320000/bones_full/versus_previous_node/comparison.json')
    if late and late['previous_node'] == 'collection_250000':
        lines += ['', '## O7 late-phase fixed groups (250k→320k)', '',
                  '| Group | Complete250k/320k | All R250k→320k | Common n | Common R250k→320k | Common XY/m250k→320k |',
                  '|---|---:|---|---:|---|---|']
        whole = [group_rows(late['all_clip_groups'][side]) for side in ('previous', 'current')]
        shared = [group_rows(late['common_complete_groups'][side]) for side in ('previous', 'current')]
        for name in whole[0]:
            g, h = whole[0][name], whole[1][name]
            a, b = shared[0][name], shared[1][name]
            r = xy = 'no common completions'
            if b['clip_count']:
                r = f"{a['mean_normalized_return']:.8f}→{b['mean_normalized_return']:.8f}"
                xy = f"{a['quality']['root_xy_error_m']:.6f}→{b['quality']['root_xy_error_m']:.6f}"
            lines.append(f"| {name} | {g['completed']}/{h['completed']} | {g['mean_normalized_return']:.8f}→{h['mean_normalized_return']:.8f} | {b['clip_count']} | {r} | {xy} |")
    lines += ['', 'Per-node paired JSON contains common-set change distributions and recovered/new/persistent failure identities. Six fixed time series are examples, not population estimates. The130394/129514 member alignment remains unresolved.']
    return lines
