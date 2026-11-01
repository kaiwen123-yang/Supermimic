"""Read one real checkpoint back from the uploaded archive and restore its state.

Runs on D57 only. It reads a prefix of the first remote volume, stops the two
download/decompression processes after the chosen tar member, and keeps no
downloaded weight copy after the audit. No training or simulation is performed.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path('/root/autodl-tmp/robot-repro/supermimic')
sys.path.insert(0, str(ROOT))
import torch
from supermimic.networks import Actor, Critic, WorldModel


def gh(*args):
    return json.loads(subprocess.check_output(['gh', *args], text=True))


def main():
    torch.set_num_threads(1)
    meta = ROOT / 'results/storage_cleanup/20261101'
    stage = ROOT / 'work/storage-archive-20261101'
    manifest = json.loads((meta / 'manifest.json').read_text())
    parts = json.loads((stage / 'compression-complete.json').read_text())['parts']
    target = next(e for e in manifest['entries'] if e['kind'] == 'file' and e['storage'] == 'archive' and e['path'].endswith('.pt'))
    tag = 'sm-d57-storage-archive-20261101'
    release_id = gh('release', 'view', tag, '--repo', 'kaiwen123-yang/Supermimic', '--json', 'databaseId')['databaseId']
    release = gh('api', f'repos/kaiwen123-yang/Supermimic/releases/{release_id}')
    asset = next(a for a in release['assets'] if a['name'] == parts[0]['name'])
    assert asset['state'] == 'uploaded' and asset['size'] == parts[0]['bytes']
    assert asset['digest'] == 'sha256:' + parts[0]['sha256']
    with tempfile.TemporaryDirectory(prefix='restore-audit-', dir=stage) as temporary:
        directory = Path(temporary)
        assert directory.resolve().parent == stage.resolve()
        restored = directory / 'checkpoint.pt'
        with (directory / 'transfer.log').open('wb') as errors:
            fetch = subprocess.Popen(['gh', 'release', 'download', tag, '--repo', 'kaiwen123-yang/Supermimic',
                '--pattern', parts[0]['name'], '--output', '-'], stdout=subprocess.PIPE, stderr=errors)
            unpack = subprocess.Popen(['/root/miniconda3/bin/zstd', '-d', '--long=28', '-c'],
                stdin=fetch.stdout, stdout=subprocess.PIPE, stderr=errors)
            fetch.stdout.close()
            try:
                with tarfile.open(fileobj=unpack.stdout, mode='r|') as archive:
                    for item in archive:
                        if item.name == target['path']:
                            assert item.isfile() and item.size == target['bytes']
                            with archive.extractfile(item) as source, restored.open('wb') as destination:
                                while chunk := source.read(4 * 1024 * 1024):
                                    destination.write(chunk)
                            break
                if not restored.exists():
                    raise RuntimeError('Selected checkpoint was not present in the first remote volume')
            finally:
                # These are only this audit's child processes, not any uploader.
                for process in (unpack, fetch):
                    if process.poll() is None:
                        process.terminate()
                for process in (unpack, fetch):
                    process.wait(timeout=20)
        with restored.open('rb') as f:
            actual_hash = hashlib.file_digest(f, 'sha256').hexdigest()
        assert actual_hash == target['sha256']
        checkpoint = torch.load(restored, map_location='cpu', weights_only=False)
        models = {'actor': Actor(), 'critic': Critic(), 'world_model': WorldModel()}
        optimizer_steps = {}
        for name, model in models.items():
            model.load_state_dict(checkpoint[name], strict=True)
            optimizer_key = 'world_optimizer' if name == 'world_model' else name + '_optimizer'
            optimizer = torch.optim.Adam(model.parameters())
            optimizer.load_state_dict(checkpoint[optimizer_key])
            values = [int(state['step']) for state in optimizer.state.values() if 'step' in state]
            optimizer_steps[name] = sorted(set(values))
        assert checkpoint['dataset_manifest_sha256'] == manifest['dataset_manifest_sha256']
        report = {'status': 'restored_verified', 'verified_unix': time.time(),
            'source': 'GitHub Release bytes, not the local archive copy', 'archive_release_id': release_id,
            'remote_volume': parts[0], 'checkpoint_path': target['path'], 'checkpoint_bytes': target['bytes'],
            'checkpoint_sha256': actual_hash, 'iteration': checkpoint['iteration'],
            'actor_updates': checkpoint['actor_updates'], 'models_loaded_strictly': list(models),
            'optimizer_steps': optimizer_steps, 'sampler_state_present': all(k in checkpoint for k in ('sampler_returns','sampler_memory')),
            'rng_state_present': all(k in checkpoint for k in ('torch_rng','cuda_rng')),
            'replay_saved': checkpoint.get('replay_saved'), 'temporary_weight_copy_removed_on_exit': True,
            'scope': 'One representative remote checkpoint restored; all archive contents were separately SHA256-verified locally, and every remote volume must match its full digest before cleanup',
            'no_training_or_simulation': True}
        (meta / 'restore_validation.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
