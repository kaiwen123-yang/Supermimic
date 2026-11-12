"""One persisted campaign deadline, two children, then serial scoring workers."""
import argparse
from datetime import datetime, timezone, timedelta
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from common import ARMS, CAMPAIGN, PUBLICATION_LOCK, now, write_json, hardware
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
        write_json(run / 'stage.json', {'status': status, 'at': now(), 'driver_pid': os.getpid(), **extra})

    def publish(label):
        with PUBLICATION_LOCK.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return refresh_and_publish(workspace, label)

    if args.start_at == 'train':
        # Existing deadline is kept on any real invocation; never silently restart children.
        if (run / 'budget.json').exists():
            raise RuntimeError('Existing O3 campaign budget: inspect live children and artifacts; no automatic restart')
        stage('prepared')
        write_json(workspace / 'results' / CAMPAIGN / 'resources_before_start.json', hardware())
        publish('implementation-prepared')
        start = time.time()
        budget = {'start_epoch': start, 'deadline_epoch': start + 28800, 'shared_training_seconds': 28800,
                  'started_at': now(), 'deadline_at': datetime.fromtimestamp(start + 28800, timezone(timedelta(hours=8))).isoformat(),
                  'scope': 'entire campaign including child imports, initialization, contention and interruptions'}
        write_json(run / 'budget.json', budget)
        write_json(workspace / 'results' / CAMPAIGN / 'budget.json', budget)
        stage('training')
        children = []
        for arm, name in ARMS.items():
            arm_dir = workspace / 'outputs' / name
            arm_dir.mkdir(parents=True, exist_ok=True)
            stream = (arm_dir / 'train_official.log').open('a')
            proc = subprocess.Popen([sys.executable, str(scripts / 'train_official.py'), '--workspace', str(workspace), '--arm', arm],
                                    stdout=stream, stderr=subprocess.STDOUT)
            children.append((arm, proc, stream))
        write_json(run / 'training_children.json', {arm: {'pid': proc.pid, 'started_at': now()} for arm, proc, _ in children})
        publish('training-started')
        exits = {}
        for arm, proc, stream in children:
            code = proc.wait()
            stream.close()
            exits[arm] = {'pid': proc.pid, 'exit_code': code, 'observed_exit_at': now()}
            write_json(run / 'training_children_exit.json', exits)
        # Both wait() calls returned before any scoring worker can be started.
        write_json(workspace / 'results' / CAMPAIGN / 'training_children_exit.json', exits)
        if any(item['exit_code'] for item in exits.values()):
            stage('failed', children=exits)
            publish('training-error')
            raise RuntimeError('Actual training failure; preserve endpoint/deadline and inspect before further execution')
        stage('training_completed_evaluation_pending')
        publish('training-exited')
    if args.start_at in ('train', 'bones', 'lafan'):
        exits = json.loads((run / 'training_children_exit.json').read_text())
        if set(exits) != set(ARMS) or any(item['exit_code'] for item in exits.values()):
            raise RuntimeError('Both successful child exits are required before scoring')
        sources = ['bones_full', 'lafan40_cross_library'] if args.start_at != 'lafan' else ['lafan40_cross_library']
        for source in sources:
            stage('evaluating_bones' if source == 'bones_full' else 'evaluating_lafan')
            publish(source + '-start')
            with (run / 'evaluate_library.log').open('a') as stream:
                proc = subprocess.Popen([sys.executable, str(scripts / 'evaluate_library.py'), '--workspace', str(workspace), '--source', source],
                                        stdout=stream, stderr=subprocess.STDOUT)
                write_json(run / 'active_scoring_child.json', {'source': source, 'pid': proc.pid, 'at': now()})
                code = proc.wait()
            if code:
                stage('failed', scoring_source=source, exit_code=code)
                publish(source + '-error')
                raise RuntimeError('Scoring child failed; retained batch files support missing-batch continuation')
    stage('completed')
    publish('completed')


if __name__ == '__main__':
    main()
