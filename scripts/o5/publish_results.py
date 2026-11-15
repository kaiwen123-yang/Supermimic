"""Publish O5 lightweight artifacts without changing a failed training state."""
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
                  'actual_config': read_json(workspace / 'outputs' / name / 'actual_config.json'),
                  'training': training['arms'][arm]}
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
               'plan_commit': PLAN_COMMIT, 'implementation_status': 'deployed_o5_isolated_optimizer_modes',
               'stage': stage, 'budget': budget, 'arms': arms, 'actual_unique_nodes': nodes,
               'evaluations': evaluations, 'parent': protocol['parent'], 'full_resume': False,
               'initialization': 'weights_only_warm_start', 'training_started': budget is not None,
               'training_status': training['status'], 'training_finished': training['child_exited'],
               'training_done': training['target_reached'], 'new_joint_updates': training['new_joint_updates'],
               'target_new_joint_updates_per_arm': NEW_JOINT_UPDATES,
               'total_new_joint_updates': training['total_new_joint_updates'],
               'target_new_joint_updates_total': NEW_JOINT_UPDATES * len(ARMS),
               'training': training, 'training_children_exit': training['children_exit'],
               'formal_evaluation_started': (result / 'evaluation_execution.json').exists(),
               'formal_evaluation_finished': finished, 'formal_evaluation_done': finished,
               'publication': 'included_in_this_commit', 'execution_snapshot_published': True,
               'lightweight_results_published': finished,
               'BONES_clips': 130394, 'protected_O3_anchors': ['quarter/update_16000', 'quarter/update_32000'],
               'protected_O2_nodes': ['hour_03', 'hour_06', 'final'], 'O1_P6_acceptance_preserved': True, 'P12': 'paused',
               'protected_O4_nodes': ['update_16000', 'update_32000', 'update_64000', 'update_96000', 'update_132000'],
               'historical_weight_norms_status': read_json(result / 'historical_o4_weight_norms.json', {}).get('status', 'pending'),
               'large_artifacts': {arm: str(workspace / 'outputs' / name) for arm, name in ARMS.items()},
               'backup_status': 'not_confirmed_by_user', 'automatic_extension': False, 'automatic_restart': False,
               'latest_training_semantics': 'Historical child progress/exit snapshot; current completion fields are above.'}
    summary['initial_scores'] = {'status': 'reused_without_simulation',
        'bones_full': 'results/20261112-o3-official-bones-lr-s0/milestones/quarter/update_32000/bones_full',
        'lafan40_cross_library': 'results/20261112-o3-official-bones-lr-s0/milestones/quarter/update_32000/lafan40_cross_library'}
    write_json(result / 'summary.json', summary)
    lines = ['# O5 official optimizer comparison', '',
        f"Status: **{status}**. Training: **{training['status']}**. Updated: {summary['updated_at']}.", '',
        'O3 quarter/update_32000 WM/Actor/Critic and full normalizers; new optimizer/replay/sampler/RNG. full_resume=false.',
        f"Fixed LR=5e-5; 4096 environments per arm; updates per arm {training['new_joint_updates']}, target {NEW_JOINT_UPDATES} each; total {training['total_new_joint_updates']}/64000.",
        'muon_wd0 preserves official grouping and removes Muon decay; adam_wd0 uses all-parameter Adam with zero decay.',
        'No wall-clock deadline or return-based early stop. Saves: initial/8k/16k/32k and actual final for each arm.',
        'Ancestor 63924 updates are provenance only. Failed/interrupted training is never restarted automatically.', '',
        '| Node | Library | New updates | R | Complete / all |', '|---|---|---:|---:|---:|']
    for label, by_source in evaluations.items():
        for source, item in by_source.items():
            lines.append(f'| {label} | {source} | {item["checkpoint_metadata"]["learning_phases"]} | {item["mean_normalized_return"]:.8f} | {item["completed"]}/{item["clip_count"]} |')
    lines += ['', 'Initial scores reuse O3 quarter32k: BONES R=.94430475, 130307/130394 complete, 87 failed. Final aliases are evaluated once.',
        'Quarter16k remains the quality anchor (R=.94757578). Historical O4: 16k R=.92672114/71 failed; 32k R=.90437763/93 failed; reuse without simulation. O2 remains a separate historical reference.',
        'Training must exit before one BONES worker scores all actual nodes, followed by one LAFAN40 worker.',
        'Every node includes parent/within-arm-adjacent comparisons, common-complete quality, hard/skills/duration and frozen failure groups. Equal-update arms and parent+O4+A+B intersections are under comparisons/.',
        'Dense/bootstrap/value metrics are last-update snapshots; collection/reset metrics are log-window totals.',
        'LAFAN is cross-library scoring after BONES-only training. Existing O1/P6 acceptance is preserved.',
        'Each arm actual final retains at most eight short failure windows from the same evaluation; no extra rollout or prediction.',
        'Large artifacts remain on D57; no Release, archive, stage cleanup or next stage is scheduled.', '']
    (result / 'README.md').write_text('\n'.join(lines))
    if finished:
        conclusion = ['# O5 actual-node results', '', *lines[2:], '',
            f"Training target reached: {training['target_reached']}; continuous updates: {training['new_joint_updates']}."]
        for label in nodes:
            directory = result / 'milestones' / label / 'bones_full'
            for name in ('versus_O3_quarter_update_32000', 'versus_previous_node', 'versus_historical_O4'):
                comparison = read_json(directory / name / 'comparison.json')
                if comparison:
                    old, new = comparison['all_clip_previous'], comparison['all_clip_current']
                    conclusion.append(f'{label} {name}: R change={new["mean_normalized_return"]-old["mean_normalized_return"]:+.8f}; '
                                      f'newly complete={comparison["new_completions"]}, lost={comparison["lost_completions"]}.')
        for arm in ARMS:
            for updates in (16000, 32000):
                node = result / 'milestones' / arm / f'update_{updates:05d}' / 'bones_full'
                for name in ('versus_O3_quarter_update_32000', 'versus_previous_node', 'versus_historical_O4'):
                    comparison = read_json(node / name / 'comparison.json')
                    if not comparison:
                        continue
                    a, b = comparison['common_complete']['previous'], comparison['common_complete']['current']
                    if b['clip_count']:
                        conclusion.append(f"{arm} +{updates} {name}, common-complete n={b['clip_count']}: "
                            f"R {a['mean_normalized_return']:.8f} → {b['mean_normalized_return']:.8f}; "
                            f"XY {a['quality']['root_xy_error_m']:.6f} → {b['quality']['root_xy_error_m']:.6f} m; "
                            f"body orientation {a['quality']['relative_body_orientation_error_rad']:.6f} → {b['quality']['relative_body_orientation_error_rad']:.6f} rad.")
        comparison = read_json(result / 'comparisons/bones_full/update_32000/between_arms.json')
        if comparison and comparison['common_complete']['current']['clip_count']:
            old, new = comparison['all_clip_previous'], comparison['all_clip_current']
            a, b = comparison['common_complete']['previous'], comparison['common_complete']['current']
            directions = [new['mean_normalized_return'] - old['mean_normalized_return'],
                          b['mean_normalized_return'] - a['mean_normalized_return'],
                          a['quality']['root_xy_error_m'] - b['quality']['root_xy_error_m'],
                          a['quality']['relative_body_orientation_error_rad'] - b['quality']['relative_body_orientation_error_rad']]
            retention = []
            for node_name in (comparison['previous_node'], comparison['current_node']):
                parent_cmp = read_json(result / 'milestones' / node_name / 'bones_full/versus_O3_quarter_update_32000/comparison.json')
                retention.append(parent_cmp['lost_completions'])
            directions.append(retention[0] - retention[1])
            if all(d >= 0 for d in directions) and any(d > 0 for d in directions):
                decision = f"{comparison['current_node']} has consistent fixed-32k advantages on the listed return/precision/parent-retention metrics."
            elif all(d <= 0 for d in directions) and any(d < 0 for d in directions):
                decision = f"{comparison['previous_node']} has consistent fixed-32k advantages on the listed return/precision/parent-retention metrics."
            else:
                decision = 'Fixed32k has a return/precision/parent-retention tradeoff; no single winner is selected.'
            write_json(result / 'fixed32k_decision.json', {
                'decision': decision, 'previous_node': comparison['previous_node'], 'current_node': comparison['current_node'],
                'positive_favors_current': dict(zip(['whole_library_R', 'same_set_R', 'same_set_XY_reduction',
                    'same_set_body_orientation_reduction', 'parent_success_losses_reduction'], directions)),
                'parent_success_losses_previous_current': retention,
                'trend_16k_to32k': {arm: read_json(result / 'milestones' / arm /
                    'update_32000/bones_full/versus_previous_node/comparison.json') for arm in ARMS},
                'limits': 'Historical O4 is not concurrent; 32k does not establish132k stability, unique causation, or full paper Adam+cosine reproduction.'})
            conclusion += ['', decision]
        conclusion += ['', 'Use fixed32k and16k→32k trends together; retain coverage/precision tradeoffs. No automatic parent replacement or budget extension.',
                       'O4 is historical, not a concurrent randomized control.32k does not prove132k stability or full paper Adam+cosine reproduction.',
                       'R=.90 is the SONIC reference; the author25-failure count uses different membership. No cross-seed or permanent-stability claim.', '']
        (result / 'conclusion.md').write_text('\n'.join(conclusion))
    write_handoff(workspace, summary)
    return summary


def write_handoff(workspace, summary):
    run = workspace / 'outputs' / CAMPAIGN
    training = summary['training']
    lines = ['# O5 执行交接', '', f"更新时间：{summary['updated_at']}。当前实际状态：**{summary['status']}**。", '',
        '- tmux：`sm-o5-optimizer-s0`。若已有活动进程或budget.json，只观察接续，不重复启动训练。',
        f'- 工作区：`{workspace}`；用户代码工作树：`{CODE_ROOT}`。',
        '- 官方源码：`supermimic-o5-optimizer`，基于abc124c；O3统计补丁一次，加O5优化器patch。研究库dd51a9f。',
        '- 共同父O3 quarter32k；WM bundle、Actor、Critic、全部normalizer恢复；optimizer/replay/sampler/RNG新建。full_resume=false。',
        '- A muon_wd0保留官方分组，仅Muon decay=0；B全Adam decay=0。三网络LR固定5e-5，每路4096环境。',
        '- 每臂32000新增连续joint，合计64000；initial/8k/16k/32k/final，无小时截止、不按回报早停。',
        '- 两训练child退出后串行全BONES再LAFAN评分及轻量发布；父/O4历史成绩复用。真实失败不自动重启。',
        '', '| Arm | 当前训练状态 | 新增 / 32000 | 已观察退出 |', '|---|---|---:|---|']
    for arm, state in training['arms'].items():
        lines.append(f"| {arm} | {state['status']} | {state['new_joint_updates']} | {state['child_exited']} |")
    lines += ['', f"合计：{training['total_new_joint_updates']}/64000。",
        f"- 驱动日志：`{run / 'driver.log'}`。",
        f"- PID记录：`{run / 'training_children.json'}`；真实退出：`{run / 'training_children_exit.json'}`。",
        '- 各run的`train_official.log`、`progress.json`和`nodes.json`保留实时与退出快照。',
        f"- 当前状态：`{run / 'stage.json'}`；汇总：`{workspace / 'results' / CAMPAIGN / 'summary.json'}`。",
        '- 六历史节点的CPU范数读取在任一arm正常initial映射就绪后开始；不额外构建模型。',
        '', '交接不重建replay、不重置LR、不停止后台。若仅评分或发布失败，定点接续该阶段，不重训或覆盖已有分数。',
        'latest_training是子进程运行/退出快照；summary顶层与逐臂training字段为当前完成状态。',
        '判断以32k和16k→32k全库R、共同完整R/XY/body orientation及父成功保持为主；历史O4不作为同步随机对照。',
        '32k不等于132k长期稳定或完整论文配方复现。保留O3 quarter16k/32k、O4全部节点、O2/O1/P6及所有历史保护成果。',
        'P12暂停，不自动开O6。大产物留D57；不Release、不tar、不自动归档或阶段清理。', '']
    (CODE_ROOT / 'docs/O5_EXECUTION_HANDOFF.md').write_text('\n'.join(lines))


def publish(workspace, label, summary):
    run = workspace / 'outputs' / CAMPAIGN
    result = workspace / 'results' / CAMPAIGN
    ledger_path = run / 'published_files.json'
    ledger = read_json(ledger_path, {})
    files = [(f'results/{CAMPAIGN}/{p.relative_to(result).as_posix()}', p) for p in result.rglob('*')
             if p.is_file() and p.suffix in {'.json', '.jsonl', '.csv', '.md', '.npz'}]
    files += [(f'scripts/o5/{p.name}', p) for p in (CODE_ROOT / 'scripts/o5').iterdir() if p.suffix in {'.py', '.sh', '.patch'}]
    files += [('docs/O5_EXECUTION_HANDOFF.md', CODE_ROOT / 'docs/O5_EXECUTION_HANDOFF.md')]
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
                   'training_status', 'new_joint_updates', 'total_new_joint_updates', 'formal_evaluation_started', 'formal_evaluation_finished',
                   'formal_evaluation_done', 'lightweight_results_published', 'execution_snapshot_published')
    item = index['campaigns'][CAMPAIGN]
    item.update({key: summary[key] for key in status_keys})
    item.update(runs=summary['arms'], actual_budget=summary['budget'],
                full_clip_evaluation_done=summary['formal_evaluation_finished'],
                publication_scope='O5 implementation and actual execution snapshot with all available actual-node results')
    for value in index.values():
        if isinstance(value, dict) and value.get('campaign') == CAMPAIGN:
            value.update({key: summary[key] for key in status_keys})
            value['execution_scope_at_publication'] = 'O5 actual implementation and execution; see summary and handoff.'
    phases = {'prepared': '运行适配已部署，待正式启动', 'training': '双路正式训练运行中',
              'training_completed_evaluation_pending': '两路各32000连续联合更新已结束，等待评分',
              'evaluating_bones': '训练已退出，正在全BONES评分', 'evaluating_lafan': '全BONES评分已结束，正在LAFAN跨库评分',
              'completed': '两路各32000连续更新、全部实际节点评分与轻量发布已完成',
              'failed': '训练发生实际错误；仅处理已有节点，不自动重启',
              'interrupted': '连续训练已中断；仅处理已有节点，不自动重启',
              'evaluation_failed': '评分遇到实际错误，保留已完成训练与评分批次',
              'results_incomplete': '训练已退出，实际节点评分尚未完整'}
    phase = phases[summary['status']]
    current = (f'{phase}（{summary["status"]}）。从O3 quarter32k权重与完整normalizer热启动，full_resume=false；'
               '三网络固定LR5e-5、两路各4096环境，各新增32000连续联合更新，合计64000，无后台小时截止。Muon无衰减与全Adam无衰减对照。'
               f'实际训练状态{summary["training_status"]}，新增{summary["new_joint_updates"]}更新；'
               f'状态见results/{CAMPAIGN}/summary.json，接续见docs/O5_EXECUTION_HANDOFF.md。'
               'tmux sm-o5-optimizer-s0；不重启活动训练。保护O3 quarter16k/32k、O4全部固定节点和O2/O1/P6成果，P12继续暂停，不自动开O6。')
    agents = read_blob(roots['AGENTS.md']['sha'])
    agents = re.sub(r'(?m)^- \*\*当前新增主线O5.*$', lambda _: '- **当前新增主线O5：** ' + current, agents, count=1)
    agents = re.sub(r'(?m)^## O5官方优化器短段对照（.*）$', lambda _: '## O5官方优化器短段对照（' + phase + '）', agents, count=1)
    readme = read_blob(roots['README.md']['sha'])
    readme = re.sub(r'(?m)^> \*\*当前新增主线：O5.*$', lambda _: '> **当前新增主线：O5官方优化器对照。** ' + current, readme, count=1)
    readme = readme.replace('O5同父优化器短对照计划已发布、执行待启动', 'O5同父优化器短对照已实施，实际状态见顶部summary').replace('当前O5方案已发布但尚未启动', '当前O5已实施，实际状态见顶部summary')
    protocol = read_json(PROTOCOL_PATH)
    protocol.update(status=summary['status'], implementation_status=summary['implementation_status'])
    protocol['completion'].update(implementation_deployed=True, training_started=summary['training_started'],
        training_done=summary['training_done'], training_status=summary['training_status'],
        formal_evaluation_done=summary['formal_evaluation_finished'],
        lightweight_results_published=summary['lightweight_results_published'], execution_snapshot_published=True,
        scope_at_publication='O5 adapters and actual execution; training completion requires 32000 continuous new updates per arm.')
    protocol['current_execution'] = {key: summary[key] for key in status_keys}
    generated = [('AGENTS.md', agents), ('README.md', readme),
                 ('results/index.json', json.dumps(index, indent=2, ensure_ascii=False) + '\n'),
                 ('configs/o5_official_optimizer_protocol.json', json.dumps(protocol, indent=2, ensure_ascii=False) + '\n')]
    for name in ('O5_OFFICIAL_OPTIMIZER_PLAN.md', 'O5_CODEX_START_PROMPT.md'):
        document = (CODE_ROOT / 'docs' / name).read_text()
        if name.endswith('PLAN.md'):
            document = document.replace('本次发布仅包含复核、计划、协议和启动词；运行适配与 D57 训练尚未开始。', f'运行适配已部署；当前状态 **{phase}**，见[执行交接](O5_EXECUTION_HANDOFF.md)与campaign summary。以下保留完整执行方案。')
        else:
            document = re.sub(r'(?m)^状态：.*$', lambda _: f'状态：{phase}。以下为原启动提示词；已存在活动O5时只观察接续，不重复启动。实时状态见[执行交接](O5_EXECUTION_HANDOFF.md)。', document, count=1)
        generated.append(('docs/' + name, document))
    for name, content in generated:
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'content': content})
    tree = github('git/trees', 'POST', {'base_tree': base_tree, 'tree': entries})
    commit = github('git/commits', 'POST', {'message': f'Publish O5 official BONES {label}', 'tree': tree['sha'], 'parents': [head]})
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
        print(f'O5_PUBLICATION_FAILED {label}: {error}', flush=True)
        return None
    write_json(record, {'status': 'published', 'commit': sha, 'at': now(), 'publication_seconds': time.monotonic() - started})
    print(f'O5_PUBLISHED {label} {sha}', flush=True)
    return sha


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    with PUBLICATION_LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        refresh_and_publish(args.workspace, args.label)
