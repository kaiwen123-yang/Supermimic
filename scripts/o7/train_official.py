"""Fresh all-Adam run: collection-clock cosine, 320000 collections, no deadline."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import math
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
from common import (RUN_NAME, SOURCE_NAME, CAMPAIGN, CODE_ROOT, TASK, PROTOCOL_PATH,
                    COLLECTION_LIMIT, CHECKPOINT_COLLECTIONS, hardware, now, write_json)
from diagnostics import CollectionDiagnostics, normalizers_from_state
from optimizer_diagnostics import OptimizerDiagnostics


class O7Runner(SuperMimicRunner):
    def optimizer_collections(self):
        return {'wm': self.world_model_learner.optimizers,
                'actor': self.policy_learner.actor_optimizers,
                'critic': self.policy_learner.critic_optimizers}

    def set_learning_rate(self, completed_collections):
        lr = 2e-4 * (.03 + .97 * .5 * (1 + math.cos(math.pi * min(completed_collections, 250000) / 250000)))
        # All device scalar objects are created by adam_wd0 before graph capture.
        # Updating their contents preserves the addresses used by captured steps.
        for optimizers in self.optimizer_collections().values():
            for optimizer in optimizers:
                for group in optimizer.param_groups:
                    group['lr'].fill_(lr)

    def actual_learning_rates(self):
        # Called only at ordinary log/save points, never per collection.
        return {name: [[float(group['lr'].detach()) for group in optimizer.param_groups]
                       for optimizer in optimizers]
                for name, optimizers in self.optimizer_collections().items()}

    def run_segment(self, workspace, budget):
        run_name = RUN_NAME
        run_dir = workspace / 'outputs' / run_name
        result_dir = workspace / 'results' / CAMPAIGN
        run_dir.mkdir(parents=True, exist_ok=True)
        self.counts = dict(collection_steps=0, real_transitions=0, learning_phases=0,
                           world_model_batch_updates=0, actor_updates=0, critic_minibatch_updates=0)
        protocol = json.loads(PROTOCOL_PATH.read_text())
        parameter_diagnostics = OptimizerDiagnostics(self)
        versions = {name: subprocess.check_output(['git', '-C', str(workspace / name), 'rev-parse', 'HEAD'], text=True).strip()
                    for name in [SOURCE_NAME, 'mjlab_research']}
        manifest_path = workspace / 'data/bones130394_official_packed/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        lineage = {k: v for k, v in manifest.items() if k != 'clips'}
        lineage['manifest_path'] = str(manifest_path)
        actual = {'task_id': TASK, 'seed': 0, 'run_name': run_name,
                  'env_cfg': asdict(self.env.cfg), 'runner_cfg': asdict(self.cfg), 'source_commits': versions,
                  'source_import_path': runner_module.__file__, 'python': sys.executable,
                  'common_source_patch': 'scripts/o7/official_diagnostics.patch',
                  'optimizer_source_patch': 'scripts/o7/official_optimizer_modes.patch',
                  'collection_action_noise': {'extra_gaussian_call': False, 'std': 0.0,
                      'policy_noise_field_present': False, 'action': 'actor output directly to simulator and replay',
                      'source_commit': protocol['source']['official_commit']},
                  'optimizer_mode': 'adam_wd0', 'torch_provenance': parameter_diagnostics.provenance(),
                  'initialization': 'from_scratch', 'full_resume': False,
                  'parent': None, 'ancestral_joint_updates': 0, 'budget': budget,
                  'max_completed_collections': COLLECTION_LIMIT, 'learning_rate_schedule': protocol['learning_rate'],
                  'schedule_adapter': str(Path(__file__).resolve()), 'cwd': str(Path.cwd()),
                  'reused_helpers': ['scripts/o7/diagnostics.py', 'scripts/o7/metrics.py', 'scripts/o3/evidence.py'],
                  'fresh_components': protocol['initialization']['fresh'],
                  'optimizer_initial': parameter_diagnostics.optimizer_metadata(), 'data_lineage': lineage}
        write_json(run_dir / 'actual_config.json', actual)
        write_json(result_dir / 'actual_config.json', actual)
        wandb.init(project='supermimic', name=run_name, mode='offline', dir=str(run_dir), config=actual)
        clips = manifest.pop('clips')
        hard = {x['source_clip_id'] for x in json.loads((CODE_ROOT / 'configs/p10_hard_motion_set.json').read_text())['members']}
        self.o3_diagnostics = CollectionDiagnostics(self, clips, hard)
        self.env.reset()
        self._seed_sim_history()
        should_train = Ratio(self.env.num_envs / self.cfg.wm.num_batches / self.cfg.wm.batch_size / self.cfg.wm.horizon * self.cfg.replay_ratio)
        nodes, ordinary, protected = {}, [], set()
        diagnosed = set()
        log_started = time.monotonic()
        wm_time = policy_time = 0.0
        collected_since_log = 0
        loss_dict = {}
        log_count = 0

        def progress(status, **extra):
            record = {'campaign': CAMPAIGN, 'run_name': run_name, 'status': status, 'updated_at': now(),
                      'training_seconds': time.time() - PROCESS_STARTED,
                      'campaign_training_wall_seconds': time.time() - budget['start_epoch'],
                      'wall_deadline_enabled': False, 'deadline_epoch': None, 'parent': None,
                      'ancestral_joint_updates': 0, 'initialization': 'from_scratch',
                      'actual_optimizer_group_lr': self.actual_learning_rates(),
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
                                'evaluation_status': 'not_scheduled_random_initial' if label == 'initial' else 'pending_after_all_training_exit'}
                write_json(run_dir / 'nodes.json', nodes)
                write_json(result_dir / 'saved_nodes.json', nodes)
                state = {'world_model': self._wm.bundle(), 'actor': self.policy_learner.actor.state_dict()}
                write_json(result_dir / 'normalizers' / f'{label}.json', {
                    'normalizers': normalizers_from_state(state), 'optimizers': parameter_diagnostics.optimizer_metadata(), 'metadata': metadata})
                if target not in diagnosed:
                    write_json(result_dir / 'parameter_norms' / f'{label}.json',
                               {'metadata': metadata, **parameter_diagnostics.snapshot()})
                    diagnosed.add(target)
                write_json(result_dir / 'resources' / f'{label}.json', hardware())
                print(f'O7_FIXED_NODE collection={self.counts["collection_steps"]} label={label} updates={self.counts["learning_phases"]} checkpoint={target}', flush=True)
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
        reason = 'collection_iteration_limit'
        try:
            for step in range(self.cfg.max_iterations):
                collected = self.step()
                collected_since_log += collected
                self.counts['collection_steps'] += 1
                self.counts['real_transitions'] += collected
                self.set_learning_rate(self.counts['collection_steps'])
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
                collections = self.counts['collection_steps']
                if step % self.cfg.log_interval == 0:
                    log_statistics()
                label = f'collection_{collections:06d}'
                if collections in CHECKPOINT_COLLECTIONS and label not in nodes:
                    save(label)
                elif step % self.cfg.save_interval == 0:
                    save()
        except BaseException as error:
            # Preserve a real endpoint, without restarting or inventing a full resume.
            checkpoint = save('final')
            endpoint = progress('interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                                stop_reason='actual_training_exception', checkpoint=str(checkpoint),
                                training_finished_at=now(), error_type=type(error).__name__, error=str(error))
            write_json(result_dir / 'training_endpoint.json', endpoint)
            raise
        if collected_since_log:
            log_statistics()
        checkpoint = save('final')
        completed = progress('training_completed_evaluation_pending' if self.counts['collection_steps'] == COLLECTION_LIMIT else 'interrupted', stop_reason=reason,
                             checkpoint=str(checkpoint), training_finished_at=now())
        write_json(result_dir / 'training_endpoint.json', completed)
        self._cleanup()
        print(f'O7_TRAINING_EXIT collection={self.counts["collection_steps"]} reason={reason} updates={self.counts["learning_phases"]}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace
    budget = json.loads((workspace / 'outputs' / CAMPAIGN / 'budget.json').read_text())
    run = workspace / 'outputs' / RUN_NAME
    write_json(run / 'progress.json', {'status': 'initializing', 'started_at': now(),
                                     'deadline_epoch': budget['deadline_epoch']})
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(0)
    protocol = json.loads(PROTOCOL_PATH.read_text())
    reference = json.loads((CODE_ROOT / protocol['source']['configuration_reference']).read_text())
    # The 7e dataclass removed this field. Do not serialize an active old .1 value.
    reference['runner_cfg']['policy'].pop('noise', None)
    runner_cfg = load_runner_cfg({'runner_cfg': reference['runner_cfg']})
    runner_cfg.run_name = RUN_NAME
    runner_cfg.wandb_run_path = None
    runner_cfg.max_iterations = COLLECTION_LIMIT
    runner_cfg.wm.lr = runner_cfg.policy.lr = 2e-4
    runner_cfg.wm.optimizer_mode = runner_cfg.policy.optimizer_mode = 'adam_wd0'
    device = setup_device('cuda:0')
    cfg = load_env_cfg(TASK, play=False)
    cfg.seed = 0
    cfg.commands['motion'].motion_file = str(workspace / 'data/bones130394_official_packed')
    cfg.commands['motion'].sampling_mode = 'external'
    try:
        env = create_env(cfg, 4096, device)
        runner = O7Runner(env, runner_cfg, TASK, registry_name=None, device=device)
        runner.run_segment(workspace, budget)
    except BaseException as error:
        write_json(run / 'failure.json', {'status': 'failed', 'recorded_at': now(),
            'deadline_epoch': budget['deadline_epoch'], 'error_type': type(error).__name__, 'error': str(error)})
        raise


if __name__ == '__main__':
    main()
