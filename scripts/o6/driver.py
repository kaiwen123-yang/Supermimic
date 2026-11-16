"""One fresh continuous child, then serial actual-node scoring and publication."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from common import (CAMPAIGN, RUN_NAME, COLLECTION_LIMIT, PUBLICATION_LOCK,
                    actual_nodes, training_state, now, write_json, hardware)
from publish_results import refresh_and_publish


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--start-at', choices=('train', 'bones', 'lafan', 'publish'), default='train')
    args = parser.parse_args()
    workspace = args.workspace
    campaign = workspace / 'outputs' / CAMPAIGN
    campaign.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).parent

    def stage(status, **extra):
        write_json(campaign / 'stage.json', {'status': status, 'at': now(), 'driver_pid': os.getpid(),
                    'training': training_state(workspace), **extra})

    def publish(label):
        with PUBLICATION_LOCK.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return refresh_and_publish(workspace, label)

    if args.start_at == 'train':
        if (campaign / 'budget.json').exists():
            raise RuntimeError('O6 already invoked: observe the active run or resume scoring/publication only.')
        stage('prepared')
        write_json(workspace / 'results' / CAMPAIGN / 'resources_before_start.json', hardware())
        publish('implementation-prepared')
        budget = {'start_epoch': time.time(), 'started_at': now(),
                  'target_completed_collection_iterations': COLLECTION_LIMIT,
                  'expected_joint_updates_not_a_stop_condition': 127997,
                  'wall_deadline_enabled': False, 'deadline_epoch': None, 'training_wall_seconds_limit': None,
                  'automatic_restart': False, 'initialization': 'from_scratch', 'parent': None}
        write_json(campaign / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        run = workspace / 'outputs' / RUN_NAME
        run.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(scripts / 'train_official.py'), '--workspace', str(workspace)]
        with (run / 'train_official.log').open('a') as stream:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        write_json(campaign / 'training_child.json', {'pid': child.pid, 'started_at': now(),
                   'command': command, 'cwd': os.getcwd(), 'PYTHONPATH': os.environ.get('PYTHONPATH')})
        stage('training')
        publish('training-started')
        code = child.wait()
        exited = {'pid': child.pid, 'exit_code': code, 'observed_exit_at': now()}
        write_json(campaign / 'training_child_exit.json', exited)
        write_json(workspace / 'results' / CAMPAIGN / 'training_child_exit.json', exited)
        budget.update(training_finished_at=now(), campaign_training_wall_seconds=time.time() - budget['start_epoch'])
        write_json(campaign / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        stage('training_' + training_state(workspace)['status'] + '_evaluation_pending')
        publish('training-exited')

    if args.start_at in ('train', 'bones', 'lafan'):
        if not training_state(workspace)['child_exited']:
            raise RuntimeError('Observed training-child exit is required before scoring.')
        sources = ['bones_full', 'lafan40_cross_library'] if args.start_at != 'lafan' else ['lafan40_cross_library']
        if actual_nodes(workspace):
            for source in sources:
                stage('evaluating_bones' if source == 'bones_full' else 'evaluating_lafan')
                publish(source + '-start')
                with (campaign / 'evaluate_library.log').open('a') as stream:
                    child = subprocess.Popen([sys.executable, str(scripts / 'evaluate_library.py'),
                        '--workspace', str(workspace), '--source', source], stdout=stream, stderr=subprocess.STDOUT)
                    write_json(campaign / 'active_scoring_child.json', {'source': source, 'pid': child.pid, 'at': now()})
                    code = child.wait()
                if code:
                    stage('evaluation_failed', scoring_source=source, exit_code=code)
                    publish(source + '-error')
                    raise RuntimeError('Scoring failed; retain completed batches. No training restart.')
    state = training_state(workspace)
    stage('completed' if state['target_reached'] else state['status'])
    publish('completed' if state['target_reached'] else 'interrupted-results')


if __name__ == '__main__':
    main()
