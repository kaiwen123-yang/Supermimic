"""Publish O4 lightweight artifacts without changing a failed training state."""
from __future__ import annotations
import argparse
import base64
import fcntl
import json
from pathlib import Path
import re
import subprocess
import time
from common import (ARMS, CAMPAIGN, CODE_ROOT, PLAN_COMMIT, PROTOCOL_PATH,
                    NEW_JOINT_UPDATES, PUBLICATION_LOCK, actual_nodes, training_state, now, write_json)


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
    protocol = read_json(PROTOCOL_PATH)
    nodes = actual_nodes(workspace)
    training = training_state(workspace)
    arms = {arm: {'run_name': name, 'latest_training': read_json(workspace / 'outputs' / name / 'progress.json'),
                  'saved_nodes': read_json(workspace / 'outputs' / name / 'nodes.json', {}),
                  'actual_config': read_json(workspace / 'outputs' / name / 'actual_config.json')}
            for arm, name in ARMS.items()}
    evaluations = {label: {source: read_json(result / 'milestones' / label / source / 'evaluation.json')
                          for source in ('bones_full', 'lafan40_cross_library')
                          if (result / 'milestones' / label / source / 'evaluation.json').exists()}
                   for label in nodes}
    budget = read_json(run / 'budget.json')
    finished = training['child_exited'] and bool(nodes) and all(len(v) == 2 for v in evaluations.values())
    status = stage['status']
    if training['status'] in ('failed', 'interrupted'):
        status = training['status']
    elif status == 'completed' and not finished:
        status = 'results_incomplete'
    summary = {'campaign': CAMPAIGN, 'updated_at': now(), 'status': status,
               'plan_commit': PLAN_COMMIT, 'implementation_status': 'deployed_o4_adapter_reusing_o3_statistics',
               'stage': stage, 'budget': budget, 'arms': arms, 'actual_unique_nodes': nodes,
               'evaluations': evaluations, 'parent': protocol['parent'], 'full_resume': False,
               'initialization': 'weights_only_warm_start', 'training_started': budget is not None,
               'training_status': training['status'], 'training_finished': training['child_exited'],
               'training_done': training['target_reached'], 'new_joint_updates': training['new_joint_updates'],
               'target_new_joint_updates': NEW_JOINT_UPDATES, 'training_children_exit': training['children_exit'],
               'formal_evaluation_started': (result / 'evaluation_execution.json').exists(),
               'formal_evaluation_finished': finished, 'formal_evaluation_done': finished,
               'publication': 'included_in_this_commit', 'execution_snapshot_published': True,
               'lightweight_results_published': finished,
               'BONES_clips': 130394, 'protected_O3_anchors': ['quarter/update_16000', 'quarter/update_32000'],
               'protected_O2_nodes': ['hour_03', 'hour_06', 'final'], 'O1_P6_acceptance_preserved': True, 'P12': 'paused',
               'large_artifacts': {arm: str(workspace / 'outputs' / name) for arm, name in ARMS.items()},
               'backup_status': 'not_confirmed_by_user', 'automatic_extension': False, 'automatic_restart': False,
               'latest_training_semantics': 'Historical child progress/exit snapshot; current completion fields are above.'}
    write_json(result / 'summary.json', summary)
    lines = ['# O4 official BONES continuous low-LR run', '',
        f"Status: **{status}**. Training: **{training['status']}**. Updated: {summary['updated_at']}.", '',
        'O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.',
        f"Fixed LR=5e-5; 4096 environments; {training['new_joint_updates']}/{NEW_JOINT_UPDATES} continuous new joint updates.",
        'No wall-clock deadline or return-based early stop. Saves: 16k/32k/64k/96k/132k and actual final.',
        'Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.', '',
        '| Node | Library | New updates | R | Complete / all |', '|---|---|---:|---:|---:|']
    for label, by_source in evaluations.items():
        for source, item in by_source.items():
            lines.append(f'| {label} | {source} | {item["checkpoint_metadata"]["learning_phases"]} | {item["mean_normalized_return"]:.8f} | {item["completed"]}/{item["clip_count"]} |')
    lines += ['', 'Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.',
        'Quarter16k remains the quality anchor (R=.94757578). O2 hour03/hour06 are separate historical references.',
        'Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.',
        'Every node includes parent/adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups.',
        'Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.',
        'LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.',
        'Actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.',
        'Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.', '']
    (result / 'README.md').write_text('\n'.join(lines))
    if finished:
        conclusion = ['# O4 actual-node results', '', *lines[2:], '',
            f"Training target reached: {training['target_reached']}; continuous updates: {training['new_joint_updates']}."]
        for label in nodes:
            directory = result / 'milestones' / label / 'bones_full'
            for name in ('versus_O3_quarter_update_32000', 'versus_previous_node'):
                comparison = read_json(directory / name / 'comparison.json')
                if comparison:
                    old, new = comparison['all_clip_previous'], comparison['all_clip_current']
                    conclusion.append(f'{label} {name}: R change={new["mean_normalized_return"]-old["mean_normalized_return"]:+.8f}; '
                                      f'newly complete={comparison["new_completions"]}, lost={comparison["lost_completions"]}.')
        conclusion += ['', 'Report every node and quality alongside coverage; no automatic parent replacement or budget extension.',
                       'R=.90 is the SONIC reference; the author 25-failure count uses different membership. No cross-seed or permanent-stability claim.', '']
        (result / 'conclusion.md').write_text('\n'.join(conclusion))
    return summary


def publish(workspace, label, summary):
    run = workspace / 'outputs' / CAMPAIGN
    result = workspace / 'results' / CAMPAIGN
    ledger_path = run / 'published_files.json'
    ledger = read_json(ledger_path, {})
    files = [(f'results/{CAMPAIGN}/{p.relative_to(result).as_posix()}', p) for p in result.rglob('*')
             if p.is_file() and p.suffix in {'.json', '.jsonl', '.csv', '.md', '.npz'}]
    files += [(f'scripts/o4/{p.name}', p) for p in (CODE_ROOT / 'scripts/o4').iterdir() if p.suffix in {'.py', '.sh'}]
    files += [('docs/O4_EXECUTION_HANDOFF.md', CODE_ROOT / 'docs/O4_EXECUTION_HANDOFF.md')]
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
    status_keys = ('status', 'implementation_status', 'training_started', 'training_finished', 'training_done',
                   'training_status', 'new_joint_updates', 'formal_evaluation_started', 'formal_evaluation_finished',
                   'formal_evaluation_done', 'lightweight_results_published', 'execution_snapshot_published')
    item = index['campaigns'][CAMPAIGN]
    item.update({key: summary[key] for key in status_keys})
    item.update(runs=summary['arms'], actual_budget=summary['budget'],
                full_clip_evaluation_done=summary['formal_evaluation_finished'],
                publication_scope='O4 execution snapshot and all currently available actual-node results')
    for value in index.values():
        if isinstance(value, dict) and value.get('campaign') == CAMPAIGN:
            value.update({key: summary[key] for key in status_keys})
    phases = {'prepared': '运行适配已部署，待正式启动', 'training': '单路正式训练运行中',
              'training_completed_evaluation_pending': '132000连续联合更新已结束，等待评分',
              'evaluating_bones': '训练已退出，正在全BONES评分', 'evaluating_lafan': '全BONES评分已结束，正在LAFAN跨库评分',
              'completed': '132000连续更新、全部实际节点评分与轻量发布已完成',
              'failed': '训练发生实际错误；仅处理已有节点，不自动重启',
              'interrupted': '连续训练已中断；仅处理已有节点，不自动重启',
              'evaluation_failed': '评分遇到实际错误，保留已完成训练与评分批次',
              'results_incomplete': '训练已退出，实际节点评分尚未完整'}
    phase = phases[summary['status']]
    current = (f'{phase}（{summary["status"]}）。从O3 quarter32k权重与完整normalizer热启动，full_resume=false；'
               '三网络固定LR5e-5、单路4096环境，目标新增132000连续联合更新，无后台小时截止。'
               f'实际训练状态{summary["training_status"]}，新增{summary["new_joint_updates"]}更新；'
               f'状态见results/{CAMPAIGN}/summary.json，接续见docs/O4_EXECUTION_HANDOFF.md。'
               'tmux sm-o4-bones-long-s0；不重启活动训练。保护O3 quarter16k/32k、O2/O1/P6成果，P12继续暂停。')
    agents = read_blob(roots['AGENTS.md']['sha'])
    agents = re.sub(r'(?m)^- \*\*当前主线O4.*$', lambda _: '- **当前主线O4：** ' + current, agents, count=1)
    agents = re.sub(r'(?m)^## O4官方低LR较长连续段（.*）$', lambda _: '## O4官方低LR较长连续段（' + phase + '）', agents, count=1)
    readme = read_blob(roots['README.md']['sha'])
    readme = re.sub(r'(?m)^> \*\*当前主线：O4.*$', lambda _: '> **当前主线：O4官方低LR较长连续训练。** ' + current, readme, count=1)
    readme = readme.replace('当前发布O4单路低LR长段方案，尚未实施或启动', 'O4单路低LR长段已实施，实时状态见顶部summary与执行交接')
    protocol = read_json(PROTOCOL_PATH)
    protocol.update(status=summary['status'], implementation_status=summary['implementation_status'])
    protocol['completion'].update(implementation_deployed=True, training_started=summary['training_started'],
        training_done=summary['training_done'], training_status=summary['training_status'],
        formal_evaluation_done=summary['formal_evaluation_finished'],
        lightweight_results_published=summary['lightweight_results_published'], execution_snapshot_published=True,
        scope_at_publication='O4 adapters and actual execution; training completion requires 132000 continuous new updates.')
    protocol['current_execution'] = {key: summary[key] for key in status_keys}
    generated = [('AGENTS.md', agents), ('README.md', readme),
                 ('results/index.json', json.dumps(index, indent=2, ensure_ascii=False) + '\n'),
                 ('configs/o4_official_bones_long_run_protocol.json', json.dumps(protocol, indent=2, ensure_ascii=False) + '\n')]
    for name in ('O4_OFFICIAL_BONES_LONG_RUN_PLAN.md', 'O4_CODEX_START_PROMPT.md'):
        document = (CODE_ROOT / 'docs' / name).read_text()
        if name.endswith('PLAN.md'):
            document = re.sub(r'(?m)^状态：.*$', lambda _: f'状态：**{phase}**。当前实际状态见 [O4执行交接](O4_EXECUTION_HANDOFF.md) 和 campaign summary；以下保留完整执行方案。', document, count=1)
        else:
            document = re.sub(r'(?m)^> 当前状态：.*$', lambda _: f'> 当前状态：{phase}。以下为原启动提示词；已存在活动O4时只观察接续，不重复启动。实时状态见[执行交接](O4_EXECUTION_HANDOFF.md)。', document, count=1)
        generated.append(('docs/' + name, document))
    for name, content in generated:
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'content': content})
    tree = github('git/trees', 'POST', {'base_tree': base_tree, 'tree': entries})
    commit = github('git/commits', 'POST', {'message': f'Publish O4 official BONES {label}', 'tree': tree['sha'], 'parents': [head]})
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
        summary['execution_snapshot_published'] = False
        summary['lightweight_results_published'] = False
        if summary['status'] == 'completed':
            summary['status'] = 'results_complete_publication_pending'
        write_json(workspace / 'results' / CAMPAIGN / 'summary.json', summary)
        print(f'O4_PUBLICATION_FAILED {label}: {error}', flush=True)
        return None
    write_json(record, {'status': 'published', 'commit': sha, 'at': now(), 'publication_seconds': time.monotonic() - started})
    print(f'O4_PUBLISHED {label} {sha}', flush=True)
    return sha


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    with PUBLICATION_LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        refresh_and_publish(args.workspace, args.label)
