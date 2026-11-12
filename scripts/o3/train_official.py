"""Matched weights-only starts; the original collection/WM/policy learning loop."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import time

PROCESS_STARTED = time.time()
import torch
import wandb
import supermimic.tasks
import supermimic.runners.supermimic_runner as runner_module
from mjlab.tasks.registry import load_env_cfg
from supermimic.runners.run_config import load_runner_cfg
from supermimic.runners.supermimic_runner import Ratio, SuperMimicRunner
from supermimic.scripts.train_utils import create_env, setup_device
from common import ARMS, CAMPAIGN, CODE_ROOT, TASK, hardware, now, write_json
from diagnostics import CollectionDiagnostics, normalizers_from_state, optimizer_metadata


class O3Runner(SuperMimicRunner):
    def run_segment(self, workspace, arm, budget, parent):
        run_name = ARMS[arm]
        run_dir = workspace / 'outputs' / run_name
        result_dir = workspace / 'results' / CAMPAIGN / 'arms' / arm
        run_dir.mkdir(parents=True, exist_ok=True)
        self.counts = dict(collection_steps=0, real_transitions=0, learning_phases=0,
                           world_model_batch_updates=0, actor_updates=0, critic_minibatch_updates=0)
        protocol = json.loads((CODE_ROOT / 'configs/o3_official_bones_stability_protocol.json').read_text())
        versions = {name: subprocess.check_output(['git', '-C', str(workspace / name), 'rev-parse', 'HEAD'], text=True).strip()
                    for name in ['supermimic-o3-stability', 'mjlab_research']}
        actual = {'task_id': TASK, 'seed': 0, 'arm': arm, 'run_name': run_name,
                  'env_cfg': asdict(self.env.cfg), 'runner_cfg': asdict(self.cfg), 'source_commits': versions,
                  'source_import_path': runner_module.__file__, 'python': sys.executable,
                  'common_source_patch': 'scripts/o3/official_diagnostics.patch',
                  'initialization': 'matched_weights_only_warm_start', 'full_resume': False,
                  'parent': protocol['parent'], 'budget': budget, 'max_new_joint_updates': 32000,
                  'optimizer_initial': optimizer_metadata(self), 'data_lineage': parent['data_lineage']}
        write_json(run_dir / 'actual_config.json', actual)
        write_json(result_dir / 'actual_config.json', actual)
        wandb.init(project='supermimic', name=run_name, mode='offline', dir=str(run_dir), config=actual)
        clips = json.loads((workspace / 'data/bones130394_official_packed/manifest.json').read_text())['clips']
        hard = {x['source_clip_id'] for x in json.loads((CODE_ROOT / 'configs/p10_hard_motion_set.json').read_text())['members']}
        self.o3_diagnostics = CollectionDiagnostics(self, clips, hard)
        self.env.reset()
        self._seed_sim_history()
        should_train = Ratio(self.env.num_envs / self.cfg.wm.num_batches / self.cfg.wm.batch_size / self.cfg.wm.horizon * self.cfg.replay_ratio)
        nodes, ordinary, protected = {}, [], set()
        log_started = time.monotonic()
        wm_time = policy_time = 0.0
        collected_since_log = 0
        loss_dict = {}
        log_count = 0

        def progress(status, **extra):
            record = {'campaign': CAMPAIGN, 'arm': arm, 'run_name': run_name, 'status': status, 'updated_at': now(),
                      'training_seconds': time.time() - PROCESS_STARTED,
                      'campaign_training_wall_seconds': time.time() - budget['start_epoch'],
                      'deadline_epoch': budget['deadline_epoch'], 'parent': protocol['parent'],
                      'full_resume': False, **self.counts, **extra}
            write_json(run_dir / 'progress.json', record)
            return record

        def save(label=None):
            target = run_dir / 'checkpoints' / f"checkpoint_{self.counts['collection_steps']:09d}.pt"
            target.parent.mkdir(parents=True, exist_ok=True)
            metadata = progress('running', checkpoint=str(target), evaluation_label=label)
            # A final alias does not write or evaluate the same physical node twice.
            if not target.exists():
                payload = {'world_model': self._wm.bundle(), 'actor': self.policy_learner.actor.state_dict(),
                           'critic': self.policy_learner.critic.state_dict(), 'runner_cfg': asdict(self.cfg),
                           'metadata': metadata, 'data_lineage': actual['data_lineage']}
                torch.save(payload, target)
                write_json(target.with_suffix('.json'), metadata)
            if label is not None:
                protected.add(target)
                nodes[label] = {'checkpoint': str(target), 'metadata': metadata,
                                'evaluation_status': 'parent_score_reused' if label == 'initial' else 'pending_after_all_training_exit'}
                write_json(run_dir / 'nodes.json', nodes)
                write_json(result_dir / 'saved_nodes.json', nodes)
                state = {'world_model': self._wm.bundle(), 'actor': self.policy_learner.actor.state_dict()}
                write_json(result_dir / 'normalizers' / f'{label}.json', {
                    'normalizers': normalizers_from_state(state), 'optimizers': optimizer_metadata(self), 'metadata': metadata})
                write_json(result_dir / 'resources' / f'{label}.json', hardware())
                print(f'O3_FIXED_NODE arm={arm} label={label} updates={self.counts["learning_phases"]} checkpoint={target}', flush=True)
            elif target not in ordinary:
                ordinary.append(target)
                while len(ordinary) > 20:
                    old = ordinary.pop(0)
                    if old not in protected:
                        old.unlink()
                        old.with_suffix('.json').unlink()
            return target

        def log_statistics():
            nonlocal log_started, wm_time, policy_time, collected_since_log, log_count
            self.logger.log(it=log_count, total_it=self.cfg.max_iterations // self.cfg.log_interval,
                            collect_time=time.monotonic() - log_started - wm_time - policy_time,
                            wm_learn_time=wm_time, policy_learn_time=policy_time,
                            loss_dict=loss_dict, num_collected_steps=collected_since_log)
            compact = progress('running')
            compact['statistics_kind'] = 'collection_reset_window_and_last_joint_update_snapshot'
            compact['losses_and_imagination_last_update'] = {k: float(v) for k, v in loss_dict.items()}
            compact['window'] = self.o3_diagnostics.flush()
            compact['window_collection_end'] = self.counts['collection_steps']
            with (run_dir / 'training_stats.jsonl').open('a') as stream:
                stream.write(json.dumps(compact) + '\n')
            part = result_dir / 'training_stats' / f'part_{log_count // 200:04d}.jsonl'
            part.parent.mkdir(parents=True, exist_ok=True)
            with part.open('a') as stream:
                stream.write(json.dumps(compact) + '\n')
            log_count += 1
            log_started = time.monotonic()
            wm_time = policy_time = 0.0
            collected_since_log = 0

        save('initial')
        reason = 'shared_campaign_deadline'
        try:
            for step in range(self.cfg.max_iterations):
                if time.time() >= budget['deadline_epoch']:
                    break
                collected = self.step()
                collected_since_log += collected
                self.counts['collection_steps'] += 1
                self.counts['real_transitions'] += collected
                for _ in range(should_train(step)):
                    if self.replay_buffer.num_transitions < self.cfg.wm.horizon:
                        continue
                    data = (self.replay_buffer.sample(self.cfg.wm.horizon, self.cfg.wm.batch_size)
                            for _ in range(self.cfg.wm.num_batches))
                    tick = time.monotonic()
                    wm_logs = self.world_model_learner.update(data)
                    wm_time += time.monotonic() - tick
                    tick = time.monotonic()
                    policy_logs = self.policy_learner.update()
                    policy_time += time.monotonic() - tick
                    loss_dict.update(wm_logs)
                    loss_dict.update(policy_logs)
                    self.counts['learning_phases'] += 1
                    self.counts['world_model_batch_updates'] += self.cfg.wm.num_batches
                    self.counts['actor_updates'] += self.cfg.policy.num_batches
                    self.counts['critic_minibatch_updates'] += 20 * self.cfg.policy.num_batches
                updates = self.counts['learning_phases']
                if step % self.cfg.log_interval == 0:
                    log_statistics()
                label = f'update_{updates:05d}'
                if updates in (8000, 16000, 32000) and label not in nodes:
                    save(label)
                elif step % self.cfg.save_interval == 0:
                    save()
                if updates >= 32000:
                    reason = 'new_joint_update_limit'
                    break
        except BaseException:
            # Preserve a real endpoint, without restarting or inventing a full resume.
            save('final')
            progress('failed', stop_reason='actual_training_exception')
            raise
        if collected_since_log:
            log_statistics()
        checkpoint = save('final')
        completed = progress('training_completed_evaluation_pending', stop_reason=reason,
                             checkpoint=str(checkpoint), training_finished_at=now())
        write_json(result_dir / 'training_endpoint.json', completed)
        self._cleanup()
        print(f'O3_TRAINING_COMPLETED arm={arm} reason={reason} updates={self.counts["learning_phases"]}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    args = parser.parse_args()
    workspace, arm = args.workspace, args.arm
    budget = json.loads((workspace / 'outputs' / CAMPAIGN / 'budget.json').read_text())
    run = workspace / 'outputs' / ARMS[arm]
    write_json(run / 'progress.json', {'status': 'initializing', 'started_at': now(), 'arm': arm,
                                     'deadline_epoch': budget['deadline_epoch']})
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(0)
    protocol = json.loads((CODE_ROOT / 'configs/o3_official_bones_stability_protocol.json').read_text())
    parent = torch.load(protocol['parent']['checkpoint'], map_location='cpu', weights_only=False)
    runner_cfg = load_runner_cfg({'runner_cfg': parent['runner_cfg']})
    runner_cfg.run_name = ARMS[arm]
    runner_cfg.wandb_run_path = None
    runner_cfg.wm.lr = runner_cfg.policy.lr = 2e-4 if arm == 'control' else 5e-5
    device = setup_device('cuda:0')
    cfg = load_env_cfg(TASK, play=False)
    cfg.seed = 0
    cfg.commands['motion'].motion_file = str(workspace / 'data/bones130394_official_packed')
    cfg.commands['motion'].sampling_mode = 'external'
    try:
        env = create_env(cfg, 4096, device)
        runner = O3Runner(env, runner_cfg, TASK, registry_name=None, device=device)
        runner._wm.load_bundle(parent['world_model'])
        runner.policy_learner.actor.load_state_dict(parent['actor'], strict=True)
        runner.policy_learner.critic.load_state_dict(parent['critic'], strict=True)
        lineage = {'data_lineage': parent['data_lineage']}
        del parent
        runner.run_segment(workspace, arm, budget, lineage)
    except BaseException as error:
        write_json(run / 'failure.json', {'status': 'failed', 'recorded_at': now(), 'arm': arm,
            'deadline_epoch': budget['deadline_epoch'], 'error_type': type(error).__name__, 'error': str(error)})
        raise


if __name__ == '__main__':
    main()
