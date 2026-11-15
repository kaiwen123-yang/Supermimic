"""Two continuous children, then actual BONES/LAFAN nodes, without a deadline."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import (ARMS, CAMPAIGN, NEW_JOINT_UPDATES, PUBLICATION_LOCK,
                    actual_nodes, training_state, now, write_json, hardware)
from publish_results import refresh_and_publish


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--start-at', choices=('train', 'bones', 'lafan', 'publish'), default='train')
    args = parser.parse_args()
    workspace = args.workspace
    run = workspace / 'outputs' / CAMPAIGN
    run.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).parent

    def stage(status, **extra):
        write_json(run / 'stage.json', {'status': status, 'at': now(), 'driver_pid': os.getpid(),
                                     'training': training_state(workspace), **extra})

    def publish(label):
        with PUBLICATION_LOCK.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return refresh_and_publish(workspace, label)

    if args.start_at == 'train':
        if (run / 'budget.json').exists():
            raise RuntimeError('O5 was already invoked. Observe active training; never automatically restart a continuous segment.')
        stage('prepared')
        write_json(workspace / 'results' / CAMPAIGN / 'resources_before_start.json', hardware())
        publish('implementation-prepared')
        budget = {'start_epoch': time.time(), 'started_at': now(), 'new_joint_updates_per_arm': NEW_JOINT_UPDATES,
                  'total_new_joint_updates': NEW_JOINT_UPDATES * len(ARMS),
                  'wall_deadline_enabled': False, 'deadline_epoch': None, 'training_wall_seconds_limit': None,
                  'automatic_restart_after_process_exit': False,
                  'scope': 'two independent continuous optimizer/replay/sampler processes; ancestor updates are provenance only'}
        write_json(run / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        stage('training')
        children, started, exits = {}, {}, {}
        for arm, name in ARMS.items():
            arm_dir = workspace / 'outputs' / name
            arm_dir.mkdir(parents=True, exist_ok=True)
            with (arm_dir / 'train_official.log').open('a') as stream:
                children[arm] = subprocess.Popen([sys.executable, str(scripts / 'train_official.py'),
                    '--workspace', str(workspace), '--arm', arm], stdout=stream, stderr=subprocess.STDOUT)
            started[arm] = {'pid': children[arm].pid, 'started_at': now()}
            write_json(run / 'training_children.json', started)
        publish('training-started')
        audit = None
        while len(exits) != len(children):
            for arm, proc in children.items():
                code = proc.poll()
                if arm not in exits and code is not None:
                    exits[arm] = {'pid': proc.pid, 'exit_code': code, 'observed_exit_at': now()}
                    write_json(run / 'training_children_exit.json', exits)
                    write_json(workspace / 'results' / CAMPAIGN / 'training_children_exit.json', exits)
            if audit is None:
                maps = [workspace / 'results' / CAMPAIGN / 'arms' / arm / 'parameter_norms/initial.json' for arm in ARMS]
                available = next((p for p in maps if p.exists()), None)
                if available:
                    with (run / 'historical_norms.log').open('a') as stream:
                        audit = subprocess.Popen([sys.executable, str(scripts / 'historical_norms.py'),
                            '--workspace', str(workspace), '--parameter-map', str(available)],
                            stdout=stream, stderr=subprocess.STDOUT)
            if len(exits) != len(children):
                time.sleep(10)
        budget['training_finished_at'] = now()
        budget['campaign_training_wall_seconds'] = time.time() - budget['start_epoch']
        write_json(run / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        if audit is not None:
            write_json(run / 'historical_norms_exit.json', {'exit_code': audit.wait(), 'at': now()})
        # wait() returned: an abnormal exit does not discard actual saved nodes.
        state = training_state(workspace)
        stage('training_' + state['status'] + '_evaluation_pending')
        publish('training-exited')

    if args.start_at in ('train', 'bones', 'lafan'):
        if not training_state(workspace)['child_exited']:
            raise RuntimeError('A recorded, observed training-child exit is required before scoring.')
        sources = ['bones_full', 'lafan40_cross_library'] if args.start_at != 'lafan' else ['lafan40_cross_library']
        if actual_nodes(workspace):
            for source in sources:
                stage('evaluating_bones' if source == 'bones_full' else 'evaluating_lafan')
                publish(source + '-start')
                with (run / 'evaluate_library.log').open('a') as stream:
                    proc = subprocess.Popen([sys.executable, str(scripts / 'evaluate_library.py'),
                                             '--workspace', str(workspace), '--source', source],
                                            stdout=stream, stderr=subprocess.STDOUT)
                    write_json(run / 'active_scoring_child.json', {'source': source, 'pid': proc.pid, 'at': now()})
                    code = proc.wait()
                if code:
                    stage('evaluation_failed', scoring_source=source, exit_code=code)
                    publish(source + '-error')
                    raise RuntimeError('Scoring failed; keep saved batches and training state. No training restart.')
    state = training_state(workspace)
    stage('completed' if state['target_reached'] else state['status'])
    publish('completed' if state['target_reached'] else 'interrupted-results')


if __name__ == '__main__':
    main()
