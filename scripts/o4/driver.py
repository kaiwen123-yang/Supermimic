"""One continuous child, then all actual BONES and LAFAN nodes, without a deadline."""
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
            raise RuntimeError('O4 was already invoked. Observe active training; never automatically restart a continuous segment.')
        stage('prepared')
        write_json(workspace / 'results' / CAMPAIGN / 'resources_before_start.json', hardware())
        publish('implementation-prepared')
        budget = {'start_epoch': time.time(), 'started_at': now(), 'new_joint_updates': NEW_JOINT_UPDATES,
                  'wall_deadline_enabled': False, 'deadline_epoch': None, 'training_wall_seconds_limit': None,
                  'automatic_restart_after_process_exit': False,
                  'scope': 'one continuous optimizer/replay/sampler process; ancestor updates are provenance only'}
        write_json(run / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        stage('training')
        arm = 'low_lr'
        arm_dir = workspace / 'outputs' / ARMS[arm]
        arm_dir.mkdir(parents=True, exist_ok=True)
        with (arm_dir / 'train_official.log').open('a') as stream:
            proc = subprocess.Popen([sys.executable, str(scripts / 'train_official.py'),
                                     '--workspace', str(workspace), '--arm', arm],
                                    stdout=stream, stderr=subprocess.STDOUT)
            write_json(run / 'training_children.json', {arm: {'pid': proc.pid, 'started_at': now()}})
            publish('training-started')
            code = proc.wait()
        exits = {arm: {'pid': proc.pid, 'exit_code': code, 'observed_exit_at': now()}}
        write_json(run / 'training_children_exit.json', exits)
        write_json(workspace / 'results' / CAMPAIGN / 'training_children_exit.json', exits)
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
