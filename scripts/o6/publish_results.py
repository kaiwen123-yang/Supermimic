"""Publish actual O6 execution and lightweight evidence, preserving failure state."""
from __future__ import annotations
import argparse
import base64
import fcntl
import json
from pathlib import Path
import re
import subprocess
import time
from common import (CAMPAIGN, RUN_NAME, CODE_ROOT, PLAN_COMMIT, PROTOCOL_PATH,
                    COLLECTION_LIMIT, PUBLICATION_LOCK, actual_nodes, training_state, now, read_json, write_json)


def github(path, method='GET', data=None):
    command = ['gh', 'api', f'repos/kaiwen123-yang/Supermimic/{path}', '--method', method]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=None if data is None else json.dumps(data), text=True,
                            capture_output=True, check=True, timeout=180)
    return json.loads(result.stdout)


def read_blob(sha):
    return base64.b64decode(github(f'git/blobs/{sha}')['content']).decode()


def refresh(workspace):
    campaign = workspace / 'outputs' / CAMPAIGN
    run = workspace / 'outputs' / RUN_NAME
    result = workspace / 'results' / CAMPAIGN
    stage = read_json(campaign / 'stage.json', {'status': 'prepared'})
    nodes = actual_nodes(workspace)
    training = training_state(workspace)
    evaluations = {label: {source: read_json(result / 'milestones' / label / source / 'evaluation.json')
                          for source in ('bones_full', 'lafan40_cross_library')
                          if (result / 'milestones' / label / source / 'evaluation.json').exists()}
                   for label in nodes}
    finished = training['child_exited'] and bool(nodes) and all(len(v) == 2 for v in evaluations.values())
    status = stage['status']
    if training['status'] in ('failed', 'interrupted'):
        status = training['status']
    elif status == 'completed' and not finished:
        status = 'results_incomplete'
    summary = {'campaign': CAMPAIGN, 'run_name': RUN_NAME, 'updated_at': now(), 'status': status,
               'plan_commit': PLAN_COMMIT, 'implementation_status': 'deployed_o6_fresh_adam_collection_cosine',
               'stage': stage, 'budget': read_json(campaign / 'budget.json'), 'training': training,
               'latest_training': read_json(run / 'progress.json'), 'actual_config': read_json(run / 'actual_config.json'),
               'saved_nodes': read_json(run / 'nodes.json', {}), 'actual_unique_nodes': nodes, 'evaluations': evaluations,
               'parent': None, 'initialization': 'from_scratch', 'full_resume': False, 'ancestral_joint_updates': 0,
               'training_started': training['child'] is not None, 'training_status': training['status'],
               'training_finished': training['child_exited'], 'training_done': training['target_reached'],
               'completed_collection_iterations': training['completed_collection_iterations'],
               'target_completed_collection_iterations': COLLECTION_LIMIT,
               'actual_joint_updates': training['actual_joint_updates'], 'real_transitions': training['real_transitions'],
               'formal_evaluation_started': (result / 'evaluation_execution.json').exists(),
               'formal_evaluation_finished': finished, 'formal_evaluation_done': finished,
               'publication': 'included_in_this_commit', 'execution_snapshot_published': True,
               'lightweight_results_published': finished, 'BONES_clips': 130394,
               'O1_P6_acceptance_preserved': True, 'P12': 'paused', 'automatic_next_stage': False,
               'large_artifacts': str(run), 'backup_status': 'not_confirmed_by_user',
               'automatic_extension': False, 'automatic_restart': False,
               'latest_training_semantics': 'Child progress/exit snapshot; collection-budget completion is in training.',
               'historical_comparison_scope': 'Published scores only; no parent, matched control or O1 forgetting claim.'}
    write_json(result / 'summary.json', summary)
    lines = ['# O6 fresh official Adam + cosine', '',
        f"Status: **{status}**; training **{training['status']}**. Updated {summary['updated_at']}.", '',
        f"Completed collections {summary['completed_collection_iterations']}/{COLLECTION_LIMIT}; actual joint updates {summary['actual_joint_updates']}; real transitions {summary['real_transitions']}.",
        'Fresh seed0 WM/Actor/Critic/normalizers/optimizer/replay/sampler. parent=null; no historical weights or statistics loaded.',
        'One BONES130394 run, GenCoord/proprio/history10, 4096 envs; all Adam WD0. Initial LR2e-4, collection-clock cosine to6e-6 at250k, then floor to320k.',
        'The collection budget determines completion; 127997 joint is an expectation, never an extra stopping requirement.',
        'No wall deadline or return early stop; real failure is retained without automatic training restart.', '',
        '| Node | Library | Collection | Actual joint | R | Complete / all |',
        '|---|---|---:|---:|---:|---:|']
    for label, sources in evaluations.items():
        for source, item in sources.items():
            meta = item['checkpoint_metadata']
            lines.append(f"| {label} | {source} | {meta['collection_steps']} | {meta['learning_phases']} | {item['mean_normalized_return']:.8f} | {item['completed']}/{item['clip_count']} |")
    lines += ['', 'Collection80k/160k/250k/320k and the unique actual endpoint are scored after child exit: one BONES worker, then one LAFAN40 worker.',
        'Final aliases are deduplicated. Initial random-model scores are not scheduled.',
        'Same formal BONES rollouts retain fixed IDs63672/16/101155/124371 stride5 quality series and up to8 final failure windows.',
        'Formal returns accumulate every physical transition. Fixed examples are diagnostic, not representative random samples.',
        'Adjacent and historical comparisons report full-library coverage and common-complete R/XY/body orientation; the final comparison emphasizes250k→320k.',
        'LAFAN is cross-library scoring. O1/P6 acceptance remains valid; P12 paused. No O7 is scheduled.',
        'Large checkpoints/logs/videos/trajectories remain on D57. No Release, archive or stage cleanup.', '']
    (result / 'README.md').write_text('\n'.join(lines))
    if finished:
        conclusion = ['# O6 actual results', '', *lines[2:]]
        directory = result / 'milestones/collection_320000/bones_full/versus_previous_node'
        comparison = read_json(directory / 'comparison.json')
        if comparison and comparison['previous_node'] == 'collection_250000':
            old, new = comparison['all_clip_previous'], comparison['all_clip_current']
            a, b = comparison['common_complete']['previous'], comparison['common_complete']['current']
            decision = {'phase': 'collection250000→320000', 'full_library_return_change': new['mean_normalized_return']-old['mean_normalized_return'],
                'failed_previous_current': [old['failed'], new['failed']], 'recovered': comparison['new_completions'],
                'lost': comparison['lost_completions'], 'common_complete': comparison['common_complete'],
                'comparison_source': 'milestones/collection_320000/bones_full/versus_previous_node/comparison.json'}
            conclusion += ['', f"Floor phase250k→320k: full-library R {old['mean_normalized_return']:.8f}→{new['mean_normalized_return']:.8f}; failures {old['failed']}→{new['failed']}; recovered {comparison['new_completions']}, lost {comparison['lost_completions']}."]
            if b['clip_count']:
                changes = [new['mean_normalized_return']-old['mean_normalized_return'], old['failed']-new['failed'],
                    b['mean_normalized_return']-a['mean_normalized_return'],
                    a['quality']['root_xy_error_m']-b['quality']['root_xy_error_m'],
                    a['quality']['relative_body_orientation_error_rad']-b['quality']['relative_body_orientation_error_rad']]
                decision['all_listed_metrics_maintained_or_improved'] = all(v >= 0 for v in changes)
                decision['positive_means_improvement'] = dict(zip(['full_R', 'fewer_failures', 'common_R', 'common_XY_reduction', 'common_body_ori_reduction'], changes))
                conclusion += [f"Common-complete n={b['clip_count']}: R {a['mean_normalized_return']:.8f}→{b['mean_normalized_return']:.8f}; XY {a['quality']['root_xy_error_m']:.6f}→{b['quality']['root_xy_error_m']:.6f}m; body orientation {a['quality']['relative_body_orientation_error_rad']:.6f}→{b['quality']['relative_body_orientation_error_rad']:.6f}rad.",
                    'All listed floor-phase metrics maintained/improved.' if all(v >= 0 for v in changes) else 'The floor phase did not maintain every listed quality/coverage metric; retain the individual changes above.']
            write_json(result / 'floor_phase_decision.json', decision)
        else:
            conclusion += ['', 'Both fixed250k and320k nodes are required for a floor-phase conclusion; missing nodes were not fabricated.']
        conclusion += ['', 'This is one complete chosen fresh Adam/cosine recipe, not an isolated cosine ablation or an exact recovered author run. No cross-seed or longer-budget stability claim.', '']
        (result / 'conclusion.md').write_text('\n'.join(conclusion))
    write_handoff(workspace, summary)
    return summary


def write_handoff(workspace, summary):
    campaign = workspace / 'outputs' / CAMPAIGN
    run = workspace / 'outputs' / RUN_NAME
    lines = ['# O6 执行交接', '', f"更新时间：{summary['updated_at']}；实际状态：**{summary['status']}**。", '',
        f"- collection：{summary['completed_collection_iterations']}/320000；实际joint：{summary['actual_joint_updates']}；真实transition：{summary['real_transitions']}。",
        '- tmux：`sm-o6-adam-cosine-s0`。已存在budget或活动进程时不重复启动训练。',
        f'- 工作区：`{workspace}`；用户工作树：`{CODE_ROOT}`。',
        '- 官方隔离源码：`supermimic-o6-adam-cosine`，abc124c＋O3统计patch＋O5优化器patch；研究库dd51a9f。',
        '- 实际启动入口：`work/o6/run_d57.sh`；cwd/PYTHONPATH/import均为O6。复用既有Python和资产。',
        '- seed0从零，parent=null，wandb_run_path=None；三网络与normalizer全新，无历史checkpoint加载。',
        '- 全Adam WD0，初始2e-4；每次collection后、learner前对三网全部LR设备张量原位fill_；250k降至6e-6保持到320k。',
        '- 320000 collection是完成条件；127997 joint仅为预期。无后台小时截止、无回报早停。',
        '- 固定80k/160k/250k/320k只保存；训练child退出后依次全BONES和LAFAN评分、逐节点轻量发布。',
        '- 同次正式评分保存固定四条时序和final最多8失败尾窗。历史分数复用，不重跑旧模型。',
        f'- driver日志：`{campaign / "driver.log"}`；训练日志：`{run / "train_official.log"}`。',
        f'- PID/退出：`{campaign / "training_child.json"}`、`{campaign / "training_child_exit.json"}`。',
        f'- 实时训练：`{run / "progress.json"}`；节点：`{run / "nodes.json"}`。',
        f'- 阶段：`{campaign / "stage.json"}`；汇总：`{workspace / "results" / CAMPAIGN / "summary.json"}`。',
        '', '若仅评分失败，在确认没有活动评分后从run_d57.sh --start-at bones或lafan接续；已完成批次自动复用。',
        '若仅发布失败，执行work/o6/publish_results.py --workspace WORKSPACE --label publication-retry；不得重训或重评。',
        '真实训练异常不自动重启；checkpoint未保存完整optimizer/replay/sampler/RNG，不拼接成连续run。',
        '保留O1/P6验收及O2/O3/O4/O5历史节点，P12暂停，不开O7。大产物留服务器，不Release/tar/本机归档或阶段清理。', '']
    (CODE_ROOT / 'docs/O6_EXECUTION_HANDOFF.md').write_text('\n'.join(lines))


def publish(workspace, label, summary):
    campaign = workspace / 'outputs' / CAMPAIGN
    result = workspace / 'results' / CAMPAIGN
    ledger_path = campaign / 'published_files.json'
    ledger = read_json(ledger_path, {})
    files = [(f'results/{CAMPAIGN}/{p.relative_to(result).as_posix()}', p) for p in result.rglob('*')
             if p.is_file() and p.suffix in {'.json', '.jsonl', '.csv', '.md', '.npz'}]
    files += [(f'scripts/o6/{p.name}', p) for p in (CODE_ROOT / 'scripts/o6').iterdir() if p.suffix in {'.py', '.sh', '.patch'}]
    files += [('docs/O6_EXECUTION_HANDOFF.md', CODE_ROOT / 'docs/O6_EXECUTION_HANDOFF.md')]
    # The deployed upstream patches are already tracked, and are explicitly included.
    files += [(name, CODE_ROOT / name) for name in ('scripts/o3/official_diagnostics.patch', 'scripts/o5/official_optimizer_modes.patch')]
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
                   'training_status', 'completed_collection_iterations', 'actual_joint_updates', 'real_transitions',
                   'formal_evaluation_started', 'formal_evaluation_finished', 'formal_evaluation_done',
                   'lightweight_results_published', 'execution_snapshot_published')
    item = index['campaigns'].setdefault(CAMPAIGN, {})
    item.update({key: summary[key] for key in status_keys})
    item.update(run=RUN_NAME, parent=None, initialization='from_scratch', actual_budget=summary['budget'],
                summary=f'results/{CAMPAIGN}/summary.json', handoff='docs/O6_EXECUTION_HANDOFF.md',
                full_clip_evaluation_done=summary['formal_evaluation_finished'])
    for value in index.values():
        if isinstance(value, dict) and value.get('campaign') == CAMPAIGN:
            value.update({key: summary[key] for key in status_keys})
            value['execution_scope_at_publication'] = 'Actual O6 implementation and execution; see summary and handoff.'
    phase = {'prepared': '运行适配已部署，待启动', 'training': '单路从零正式训练运行中',
             'training_completed_evaluation_pending': '320000次采集训练已完成，待评分',
             'evaluating_bones': '训练已退出，正在全BONES评分', 'evaluating_lafan': '正在LAFAN跨库评分',
             'completed': '训练、全部实际节点评分与轻量发布已完成',
             'failed': '训练实际失败，保留已有节点', 'interrupted': '训练中断，保留已有节点',
             'evaluation_failed': '评分失败，保留已完成训练和批次',
             'results_incomplete': '训练已退出，评分尚不完整'}.get(summary['status'], summary['status'])
    current = (f'{phase}（{summary["status"]}）。seed0从零、parent=null，官方GenCoord/proprio/history10，BONES130394、4096环境；'
        '三网全Adam WD0，LR2e-4按完成collection余弦衰减到250k的6e-6，保持到320k。'
        f'当前collection={summary["completed_collection_iterations"]}/320000，实际joint={summary["actual_joint_updates"]}。'
        f'无小时截止；tmux sm-o6-adam-cosine-s0，活动任务不重启。状态results/{CAMPAIGN}/summary.json，接续docs/O6_EXECUTION_HANDOFF.md。'
        '训练退出后四节点评分与轻量发布。O5不重启；O1/P6验收保留，P12暂停，不开O7。')
    agents = re.sub(r'(?m)^- \*\*当前(?:下一阶段|新增主线)O6.*$', lambda _: '- **当前新增主线O6：** ' + current,
                    read_blob(roots['AGENTS.md']['sha']), count=1)
    agents = re.sub(r'(?m)^## O6下一轮实施（.*）$', lambda _: '## O6下一轮实施（' + phase + '）', agents, count=1)
    agents = agents.replace('为完整约定；本次未部署、未运行。', '为完整约定；当前真实状态见O6_EXECUTION_HANDOFF.md。')
    readme = re.sub(r'(?m)^> \*\*当前(?:下一阶段|新增主线)O6.*$', lambda _: '> **当前新增主线O6：** ' + current,
                    read_blob(roots['README.md']['sha']), count=1)
    protocol = read_json(PROTOCOL_PATH)
    protocol.update(status=summary['status'], implementation_status=summary['implementation_status'])
    protocol['source']['new_schedule_adapter'] = 'scripts/o6/train_official.py'
    protocol['completion'].update(implementation_deployed=True, training_started=summary['training_started'],
        training_done=summary['training_done'], formal_evaluation_done=summary['formal_evaluation_finished'],
        lightweight_results_published=summary['lightweight_results_published'], execution_snapshot_published=True,
        scope_at_publication='Actual O6 execution. Completion requires320000 collections and observed normal child exit; scoring separately recorded.')
    protocol['current_execution'] = {key: summary[key] for key in status_keys}
    generated = [('AGENTS.md', agents), ('README.md', readme),
                 ('results/index.json', json.dumps(index, indent=2, ensure_ascii=False) + '\n'),
                 ('configs/o6_official_adam_cosine_protocol.json', json.dumps(protocol, indent=2, ensure_ascii=False) + '\n')]
    for name in ('O6_OFFICIAL_ADAM_COSINE_PLAN.md', 'O6_CODEX_START_PROMPT.md'):
        document = (CODE_ROOT / 'docs' / name).read_text()
        if name.endswith('PLAN.md'):
            document = document.replace('状态：**计划，尚未在 D57 部署或启动任何 O6 进程。**', f'状态：**{phase}**；见[执行交接](O6_EXECUTION_HANDOFF.md)。')
            document = document.replace('**本文件发布仅表示计划交付，服务器部署、训练、评分状态由后续实际执行更新。**', '**当前部署、训练、评分状态见执行交接与campaign summary。**')
        else:
            document = re.sub(r'(?m)^状态：.*$', lambda _: f'状态：**{phase}**。以下保留启动约定；已有活动O6只观察接续，不重复启动。见[执行交接](O6_EXECUTION_HANDOFF.md)。', document, count=1)
        generated.append(('docs/' + name, document))
    for name, content in generated:
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'content': content})
    tree = github('git/trees', 'POST', {'base_tree': base_tree, 'tree': entries})
    commit = github('git/commits', 'POST', {'message': f'Publish O6 official Adam cosine {label}', 'tree': tree['sha'], 'parents': [head]})
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
        summary.update(publication='pending_retry', execution_snapshot_published=False, lightweight_results_published=False)
        if summary['status'] == 'completed':
            summary['status'] = 'results_complete_publication_pending'
        write_json(workspace / 'results' / CAMPAIGN / 'summary.json', summary)
        print(f'O6_PUBLICATION_FAILED {label}: {error}', flush=True)
        return None
    write_json(record, {'status': 'published', 'commit': sha, 'at': now(), 'publication_seconds': time.monotonic() - started})
    print(f'O6_PUBLISHED {label} {sha}', flush=True)
    return sha


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    with PUBLICATION_LOCK.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        refresh_and_publish(args.workspace, args.label)
