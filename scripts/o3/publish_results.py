"""Publish only O3 lightweight artifacts atop the current remote main."""
from __future__ import annotations
import argparse
import base64
import fcntl
import json
from pathlib import Path
import re
import subprocess
import time
from common import ARMS, CAMPAIGN, CODE_ROOT, PLAN_COMMIT, PARENT_CAMPAIGN, PUBLICATION_LOCK, actual_nodes, now, write_json


def github(path, method='GET', data=None):
    command = ['gh', 'api', f'repos/kaiwen123-yang/Supermimic/{path}', '--method', method]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=None if data is None else json.dumps(data), text=True,
                            capture_output=True, check=True, timeout=180)
    return json.loads(result.stdout)


def read_blob(sha):
    return base64.b64decode(github(f'git/blobs/{sha}')['content']).decode()


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def refresh(workspace):
    run = workspace / 'outputs' / CAMPAIGN
    result = workspace / 'results' / CAMPAIGN
    stage = read_json(run / 'stage.json')
    protocol = read_json(CODE_ROOT / 'configs/o3_official_bones_stability_protocol.json')
    nodes = actual_nodes(workspace)
    arms = {arm: {'run_name': name, 'latest_training': read_json(workspace / 'outputs' / name / 'progress.json'),
                  'saved_nodes': read_json(workspace / 'outputs' / name / 'nodes.json', {}),
                  'actual_config': read_json(workspace / 'outputs' / name / 'actual_config.json')}
            for arm, name in ARMS.items()}
    evaluations = {label: {source: read_json(result / 'milestones' / label / source / 'evaluation.json')
                          for source in ('bones_full', 'lafan40_cross_library')
                          if (result / 'milestones' / label / source / 'evaluation.json').exists()}
                   for label in nodes}
    budget = read_json(run / 'budget.json')
    exits = read_json(run / 'training_children_exit.json', {})
    finished = bool(nodes) and all(len(v) == 2 for v in evaluations.values())
    summary = {'campaign': CAMPAIGN, 'updated_at': now(), 'status': stage['status'],
               'plan_commit': PLAN_COMMIT, 'implementation_status': 'deployed_common_statistics_patch',
               'stage': stage, 'budget': budget, 'arms': arms, 'actual_unique_nodes': nodes,
               'evaluations': evaluations, 'parent': protocol['parent'], 'full_resume': False,
               'initialization': 'matched_weights_only_warm_start', 'training_started': budget is not None,
               'training_finished': set(exits) == set(ARMS), 'training_children_exit': exits,
               'formal_evaluation_started': (result / 'evaluation_execution.json').exists(),
               'formal_evaluation_finished': finished, 'publication': 'included_in_this_commit',
               'BONES_clips': 130394, 'protected_O2_nodes': ['hour_03', 'hour_06', 'final'],
               'O1_P6_acceptance_preserved': True, 'P12': 'paused',
               'large_artifacts': {arm: str(workspace / 'outputs' / name) for arm, name in ARMS.items()},
               'backup_status': 'not_confirmed_by_user', 'automatic_extension': False}
    if summary['status'] == 'completed' and not (summary['training_finished'] and finished):
        summary['status'] = 'results_incomplete'
    paired = {}
    for path in sorted((result / 'paired').glob('*/bones_full/comparison.json')):
        paired[path.parent.parent.name] = read_json(path)
    summary['paired_nodes'] = list(paired)
    summary['primary_paired_node'] = max(paired) if paired else None
    write_json(result / 'summary.json', summary)
    lines = ['# O3 official BONES fixed-LR comparison', '', f"Status: **{summary['status']}**. Updated: {summary['updated_at']}.", '',
        'Same O2 3h WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG on both arms. full_resume=false.',
        'control: fixed 2e-4; quarter: fixed 5e-5. 4096 real environments each; at most 32000 new joint updates per arm.',
        f'Shared campaign training deadline: {budget["deadline_at"] if budget else "not started"}. Initialization and contention are included.', '',
        '| Arm/node | Library | New updates | R | Complete / all |', '|---|---|---:|---:|---:|']
    for label, by_source in evaluations.items():
        for source, item in by_source.items():
            lines.append(f'| {label} | {source} | {item["checkpoint_metadata"]["learning_phases"]} | {item["mean_normalized_return"]:.8f} | {item["completed"]}/{item["clip_count"]} |')
    lines += ['', 'Initial scores reuse O2 3h; final aliases are evaluated once. All unique actual nodes and failed clips are retained.',
        'Two training children must exit before the single BONES worker; a separate LAFAN40 worker follows. LAFAN is cross-library scoring.',
        'Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals. Training reward is not formal R.',
        'O2 3h remains the quality anchor: R=.93501955, 130215/130394 complete. O2 6h remains the difficult-coverage reference.',
        'This single-seed weights-only comparison does not establish a unique cause or stability at the old 12h/130314-update scale.',
        'Full weights, packed data and full logs remain on D57. No next stage, archive or stage cleanup is scheduled.', '']
    result.mkdir(parents=True, exist_ok=True)
    (result / 'README.md').write_text('\n'.join(lines))
    if finished:
        conclusion = ['# O3 bounded comparison results', '', *lines[6:], '',
                      f'Highest saved matched new-update node: {summary["primary_paired_node"]}.']
        for label, comparison in paired.items():
            control, quarter = comparison['all_clip_previous'], comparison['all_clip_current']
            conclusion += [f'{label}: quarter-control R difference={quarter["mean_normalized_return"]-control["mean_normalized_return"]:+.8f}; '
                           f'complete difference={quarter["completed"]-control["completed"]:+d}. '
                           f'Quarter gains {comparison["new_completions"]} and loses {comparison["lost_completions"]} completions versus control.']
        conclusion += ['No parent replacement is automatic. Report quality and coverage together; different-update finals are not a matched comparison.', '']
        (result / 'conclusion.md').write_text('\n'.join(conclusion))
    return summary


def publish(workspace, label, summary):
    run = workspace / 'outputs' / CAMPAIGN
    result = workspace / 'results' / CAMPAIGN
    ledger_path = run / 'published_files.json'
    ledger = read_json(ledger_path, {})
    files = [(f'results/{CAMPAIGN}/{p.relative_to(result).as_posix()}', p) for p in result.rglob('*')
             if p.is_file() and p.suffix in {'.json', '.jsonl', '.csv', '.md', '.npz'}]
    files += [(f'scripts/o3/{p.name}', p) for p in (CODE_ROOT / 'scripts/o3').iterdir() if p.suffix in {'.py', '.sh', '.patch'}]
    files += [('docs/O3_EXECUTION_HANDOFF.md', CODE_ROOT / 'docs/O3_EXECUTION_HANDOFF.md')]
    for name in ('o3_preparation_normalizers.json', 'o3_preparation_existing_real_metrics.json'):
        files.append((f'results/{PARENT_CAMPAIGN}/{name}', workspace / 'results' / PARENT_CAMPAIGN / name))
    # Snapshot changing JSONL partitions, so the Git ledger names exactly the bytes submitted.
    entries, marks = [], {}
    head = github('git/ref/heads/main')['object']['sha']
    base_tree = github(f'git/commits/{head}')['tree']['sha']
    for name, path in files:
        stat = path.stat()
        mark = [stat.st_size, stat.st_mtime_ns]
        marks[name] = mark
        if ledger.get(name) == mark:
            continue
        data = path.read_bytes()[:stat.st_size]
        if path.suffix == '.jsonl':
            data = data[:data.rfind(b'\n') + 1]
        entry = {'path': name, 'mode': '100644', 'type': 'blob'}
        if path.suffix == '.npz' or len(data) > 500000:
            entry['sha'] = github('git/blobs', 'POST', {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})['sha']
        else:
            entry['content'] = data.decode()
        entries.append(entry)
    roots = {v['path']: v for v in github(f'git/trees/{base_tree}')['tree']}
    result_tree = {v['path']: v for v in github(f'git/trees/{roots["results"]["sha"]}')['tree']}
    index = json.loads(read_blob(result_tree['index.json']['sha']))
    item = index['campaigns'][CAMPAIGN]
    for key in ('status', 'implementation_status', 'training_started', 'training_finished', 'formal_evaluation_started', 'formal_evaluation_finished'):
        item[key] = summary[key]
    item.update(runs=summary['arms'], actual_budget=summary['budget'], training_done=summary['training_finished'],
                full_clip_evaluation_done=summary['formal_evaluation_finished'], lightweight_results_published=True)
    for value in index.values():
        if isinstance(value, dict) and value.get('campaign') == CAMPAIGN:
            value.update(status=summary['status'], implementation_status=summary['implementation_status'],
                         training_started=summary['training_started'], training_finished=summary['training_finished'],
                         formal_evaluation_finished=summary['formal_evaluation_finished'])
    phases = {'prepared': '运行适配已部署，待正式启动', 'training': '两路正式训练已启动',
              'training_completed_evaluation_pending': '两路训练已结束，等待评分',
              'evaluating_bones': '两路训练已结束，正在全BONES评分', 'evaluating_lafan': '全BONES评分已结束，正在LAFAN跨库评分',
              'completed': '训练、全部实际节点评分与轻量发布已完成', 'failed': '发生实际错误，保留期限和已有产物待接续',
              'results_incomplete': '实际结果尚未完整，需接续已有评分'}
    phase = phases[summary['status']]
    current = (f'{phase}（{summary["status"]}）。同O2 3h权重与完整normalizer热启动，full_resume=false；'
               'control固定LR2e-4、quarter固定5e-5，各4096环境、新增最多32000联合更新，共享一个8h训练期限。'
               f'状态见results/{CAMPAIGN}/summary.json，接续见docs/O3_EXECUTION_HANDOFF.md。'
               'tmux sm-o3-bones-lr-s0；不重启活动replay或重置期限。保护O2 3h/6h与O1/P6成果，P12继续暂停。')
    agents = read_blob(roots['AGENTS.md']['sha'])
    agents = re.sub(r'(?m)^- \*\*当前主线O3：.*$', lambda _: '- **当前主线O3：** ' + current, agents, count=1)
    agents = re.sub(r'(?m)^## O3官方BONES稳定性（.*）$', lambda _: '## O3官方BONES稳定性（' + phase + '）', agents, count=1)
    agents = re.sub(r'(?m)^- campaign=20261112-o3-official-bones-lr-s0；.*$',
                    lambda _: '- campaign=20261112-o3-official-bones-lr-s0；O3运行适配已部署；当前执行状态以顶部summary和handoff为准。两路run和tmux保持协议身份，不重复启动。', agents, count=1)
    readme = read_blob(roots['README.md']['sha'])
    readme = re.sub(r'(?m)^> \*\*当前主线：O3.*$', lambda _: '> **当前主线：O3官方BONES稳定性。** ' + current, readme, count=1)
    protocol = read_json(CODE_ROOT / 'configs/o3_official_bones_stability_protocol.json')
    protocol.update(status=summary['status'], implementation_status=summary['implementation_status'])
    protocol['current_execution'] = {'O3_adapters_implemented': True, 'server_connected_this_execution': True,
                                    'training_started': summary['training_started'], 'evaluation_started': summary['formal_evaluation_started']}
    for name, content in [('AGENTS.md', agents), ('README.md', readme),
                          ('results/index.json', json.dumps(index, indent=2, ensure_ascii=False) + '\n'),
                          ('configs/o3_official_bones_stability_protocol.json', json.dumps(protocol, indent=2, ensure_ascii=False) + '\n')]:
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'content': content})
    tree = github('git/trees', 'POST', {'base_tree': base_tree, 'tree': entries})
    commit = github('git/commits', 'POST', {'message': f'Publish O3 official BONES {label}', 'tree': tree['sha'], 'parents': [head]})
    github('git/refs/heads/main', 'PATCH', {'sha': commit['sha'], 'force': False})
    ledger.update(marks)
    write_json(ledger_path, ledger)
    return commit['sha']


def refresh_and_publish(workspace, label):
    started = time.monotonic()
    summary = refresh(workspace)
    record = workspace / 'outputs' / CAMPAIGN / f'publication_{label}.json'
    try:
        sha = publish(workspace, label, summary)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        write_json(record, {'status': 'failed', 'at': now(), 'error': str(error), 'stderr': error.stderr,
                            'scores_retained': True, 'next_action': 'retry publication only; never retrain or rescore'})
        summary['publication'] = 'pending_retry'
        if summary['status'] == 'completed':
            summary['status'] = 'results_complete_publication_pending'
        write_json(workspace / 'results' / CAMPAIGN / 'summary.json', summary)
        print(f'O3_PUBLICATION_FAILED {label}: {error}', flush=True)
        return None
    write_json(record, {'status': 'published', 'commit': sha, 'at': now(), 'publication_seconds': time.monotonic() - started})
    print(f'O3_PUBLISHED {label} {sha}', flush=True)
    return sha


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    with PUBLICATION_LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        refresh_and_publish(args.workspace, args.label)
