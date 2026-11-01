"""One-shot D57 archive and explicitly authorized cleanup, after byte verification.

Unique experiment files are archived or mapped to already verified Release assets.
Source code, the project venv, robot assets and working checkouts are protected.
Only backed-up outputs and explicitly selected dataset caches are deletion targets.
The historical 20261101 cleanup is complete and must never run a second time.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import traceback

ROOT = Path('/root/autodl-tmp/robot-repro/supermimic')
REPO = 'kaiwen123-yang/Supermimic'
TAG = 'sm-d57-storage-archive-20261101'
META = ROOT / 'results/storage_cleanup/20261101'
STAGE = ROOT / 'work/storage-archive-20261101'
ZSTD = '/root/miniconda3/bin/zstd'
CLEANUP_TARGET_NAMES = ('outputs', 'data/raw', 'data/processed')


def command(args, cwd=ROOT):
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f'{args[0]} failed: {p.stderr[-2000:]} {p.stdout[-1000:]}')
    return p.stdout.strip()


def git(*args, cwd=ROOT):
    return command(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
                    '-c', 'http.proxy=http://127.0.0.1:7890', *args], cwd)


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def status(phase, **extra):
    write(META / 'status.json', {'phase': phase, 'updated_unix': time.time(), **extra})
    print(phase, json.dumps(extra), flush=True)


def check_idle():
    active = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            cwd = (p / 'cwd').resolve(strict=True)
            cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        except (OSError, RuntimeError):
            continue
        if ROOT in cwd.parents or cwd == ROOT:
            if any(name in cmd for name in ('scripts/train.py', 'scripts/evaluate.py', 'scripts/render_termination_videos.py',
                                           'scripts/diagnose_checkpoint.py', 'scripts/publish_termination_videos.py',
                                           'scripts/publish_checkpoint.py')):
                active.append({'pid': int(p.name), 'command': cmd})
    if active:
        raise RuntimeError('Project computation/publication still active: ' + json.dumps(active))


def publish_metadata():
    git('fetch', f'https://github.com/{REPO}.git', 'main')
    head = git('rev-parse', 'FETCH_HEAD')
    worktree = ROOT / 'work' / f'storage-publication-{time.time_ns()}'
    git('worktree', 'add', '--detach', str(worktree), head)
    relative = META.relative_to(ROOT)
    shutil.copytree(META, worktree / relative, dirs_exist_ok=True)
    index_path = worktree / 'results/index.json'
    index = json.loads(index_path.read_text())
    index['d57_storage_archive'] = str(relative / 'status.json')
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + '\n')
    git('add', '--', str(relative), 'results/index.json', cwd=worktree)
    git('commit', '-m', 'Record verified D57 SuperMimic storage archive status', cwd=worktree)
    git('push', f'https://github.com/{REPO}.git', 'HEAD:main', cwd=worktree)
    commit = git('rev-parse', 'HEAD', cwd=worktree)
    git('worktree', 'remove', str(worktree))
    return commit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delete-after-verify', action='store_true')
    args = parser.parse_args()
    existing_status = META / 'status.json'
    if existing_status.exists() and json.loads(existing_status.read_text()).get('phase') == 'cleaned':
        print('ARCHIVE_ALREADY_COMPLETED: preserving the restored development environment', flush=True)
        return
    assert ROOT.resolve() == ROOT and (ROOT / 'AGENTS.md').exists()
    assert ROOT not in Path(sys.executable).resolve().parents, 'Use system Python outside the project venv'
    META.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    check_idle()
    video_status = json.loads((ROOT / 'outputs/videos/20261101-termination-s0/publication.json').read_text())
    assert video_status['status'] == 'published_verified'
    manifest_path = META / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        status('inventory')
        packages = command([str(ROOT / '.venv/bin/python'), '-m', 'pip', 'freeze', '--all'])
        packages = re.sub(r'(https?://)[^/\s]+@', r'\1[redacted]@', packages)
        (META / 'installed-packages.txt').write_text(packages + '\n')
        shutil.copy2(ROOT / '.venv/pyvenv.cfg', META / 'pyvenv.cfg')
        shutil.copy2(ROOT / 'data/processed/lafan1_g1_50hz/manifest.json', META / 'original-motion-manifest.json')
        (META / 'source-working-tree.txt').write_text(command(['git', 'status', '--short']) + '\n' + command(['git', 'worktree', 'list', '--porcelain']) + '\n')
        releases = json.loads(command(['gh', 'api', f'repos/{REPO}/releases?per_page=100']))
        existing = {a['digest'][7:]: {'url': a['browser_download_url'], 'bytes': a['size'], 'release': r['html_url']}
                    for r in releases if not r['draft'] for a in r['assets'] if a.get('digest', '').startswith('sha256:')}
        paths = [p for p in (ROOT / 'outputs').rglob('*') if p.is_file() or p.is_symlink()]
        for tree in [ROOT, *(ROOT / '.cache/execution-worktrees').glob('*')]:
            for folder in ('scripts', 'supermimic', 'configs', 'docs'):
                paths.extend(p for p in (tree / folder).rglob('*') if p.is_file() and p.suffix in ('.py', '.sh', '.json', '.toml', '.md'))
        paths.extend(ROOT / name for name in ('README.md', 'AGENTS.md', 'uv.lock', 'pyproject.toml', 'environment.json', '.python-version'))
        entries = []
        for i, path in enumerate(sorted(set(paths))):
            relative = str(path.relative_to(ROOT))
            if path.is_symlink():
                entries.append({'path': relative, 'kind': 'symlink', 'target': os.readlink(path), 'storage': 'archive'})
                continue
            st = path.stat()
            sha = digest(path)
            entry = {'path': relative, 'kind': 'file', 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'sha256': sha,
                     'storage': 'existing_release' if sha in existing and existing[sha]['bytes'] == st.st_size else 'archive'}
            if entry['storage'] == 'existing_release':
                entry['remote'] = existing[sha]
            entries.append(entry)
            if i % 100 == 0:
                print('HASHED', i, len(paths), relative, flush=True)
        rebuilt = []
        for folder in ('data/raw', 'data/processed', 'data/robot'):
            rebuilt.extend({'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                           for p in sorted((ROOT / folder).rglob('*')) if p.is_file())
        manifest = {'project': str(ROOT), 'created_unix': time.time(), 'entries': entries,
                    'rebuildable_data_files': rebuilt, 'sources_lock': 'configs/sources.lock.json',
                    'dataset_manifest_sha256': digest(META / 'original-motion-manifest.json'),
                    'rebuildable_directories': ['.venv', '.cache', 'data/raw', 'data/processed', 'data/robot'],
                    'rebuild_policy': 'Raw LAFAN1 stays at its pinned licensed upstream source; processed data and robot assets rebuild with pinned scripts. Venv rebuilds from uv.lock and installed-packages.txt. No third-party dataset is newly mirrored in this archive.',
                    'disk_before': dict(zip(('total', 'used', 'free'), shutil.disk_usage(ROOT)))}
        write(manifest_path, manifest)
    archive_entries = [e for e in manifest['entries'] if e['storage'] == 'archive']
    file_list = STAGE / 'files.nul'
    file_list.write_bytes(b''.join(e['path'].encode() + b'\0' for e in archive_entries))
    compressed = STAGE / 'compression-complete.json'
    if not compressed.exists():
        if list(STAGE.glob('supermimic.tar.zst.part-*')):
            raise RuntimeError('Incomplete previous compression exists; inspect it before creating a fresh archive')
        status('compressing', files=len(archive_entries), bytes=sum(e.get('bytes', 0) for e in archive_entries))
        import shlex
        pipeline = ('set -o pipefail; tar --format=posix --no-recursion --null -C ' + shlex.quote(str(ROOT)) +
                    ' -T ' + shlex.quote(str(file_list)) + ' -cf - | ' + shlex.quote(ZSTD) +
                    ' -T2 -3 --long=28 -c | split -b 1000M - ' + shlex.quote(str(STAGE / 'supermimic.tar.zst.part-')))
        subprocess.run(['bash', '-c', pipeline], check=True)
        parts = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(STAGE.glob('supermimic.tar.zst.part-*'))]
        write(compressed, {'parts': parts})
    parts = json.loads(compressed.read_text())['parts']
    status('verifying_local_archive', parts=len(parts), bytes=sum(p['bytes'] for p in parts))
    import shlex
    pipeline = 'cat ' + ' '.join(shlex.quote(str(STAGE / p['name'])) for p in parts) + ' | ' + shlex.quote(ZSTD) + ' -d --long=28 -c'
    process = subprocess.Popen(['bash', '-o', 'pipefail', '-c', pipeline], stdout=subprocess.PIPE)
    expected = {e['path']: e for e in archive_entries}
    seen = set()
    with tarfile.open(fileobj=process.stdout, mode='r|') as bundle:
        for item in bundle:
            entry = expected[item.name]
            if item.isfile():
                with bundle.extractfile(item) as source:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                assert actual == entry['sha256'], item.name
            elif item.issym():
                assert item.linkname == entry['target'], item.name
            elif item.islnk():
                assert expected[item.linkname]['sha256'] == entry['sha256'], item.name
            else:
                raise ValueError('Unexpected archive member: ' + item.name)
            seen.add(item.name)
    assert process.wait() == 0 and seen == set(expected)
    status('uploading', parts=len(parts), archive_bytes=sum(p['bytes'] for p in parts))
    old = subprocess.run(['gh', 'release', 'view', TAG, '--repo', REPO, '--json', 'databaseId'], text=True, capture_output=True)
    if old.returncode == 0:
        release_id = json.loads(old.stdout)['databaseId']
    else:
        git('fetch', f'https://github.com/{REPO}.git', 'main')
        head = git('rev-parse', 'FETCH_HEAD')
        release_id = json.loads(command(['gh', 'api', f'repos/{REPO}/releases', '--method', 'POST', '-f', 'tag_name=' + TAG,
            '-f', 'target_commitish=' + head, '-f', 'name=Verified D57 SuperMimic storage archive', '-F', 'draft=true',
            '-f', 'body=Split zstd archive of retained experiment files, including unpublished rolling checkpoints. Existing verified Release assets are reused by SHA256. See manifest and restore instructions.']))['id']
    remote = json.loads(command(['gh', 'api', f'repos/{REPO}/releases/{release_id}']))
    remote_assets = {a['name']: a for a in remote['assets']}
    for i, part in enumerate(parts):
        asset = remote_assets.get(part['name'])
        if asset:
            assert asset['size'] == part['bytes'] and asset['digest'] == 'sha256:' + part['sha256']
        else:
            command(['gh', 'release', 'upload', TAG, str(STAGE / part['name']), '--repo', REPO])
        status('uploading', part_completed=i+1, parts=len(parts), name=part['name'])
    manifest['archive_parts'] = parts
    manifest['archive_format'] = 'Concatenate parts in manifest order, then zstd -d and tar -x; members are relative to the SuperMimic root'
    manifest['release_url'] = f'https://github.com/{REPO}/releases/tag/{TAG}'
    manifest['local_archive_content_verified'] = True
    write(manifest_path, manifest)
    restore = META / 'RESTORE.md'
    restore.write_text('''# Restore SuperMimic on the expanded disk

1. Clone https://github.com/kaiwen123-yang/Supermimic and use the recorded source revision for each run.
2. Download all archive parts from the storage Release in manifest order, verify each SHA256, concatenate them, then decompress with `zstd -d --long=28` and extract the tar inside the project root.
3. For every manifest entry marked `existing_release`, download its exact `remote.url` to the recorded relative path and verify size/SHA256. These files were not duplicated in the archive.
4. Rebuild the isolated environment with `scripts/setup_d57.sh`; dependency locks and the actual installed package list are retained here.
5. Restore input data from the exact revision in `configs/sources.lock.json` with `scripts/prepare_d57.sh`. Raw LAFAN1 is not newly redistributed. Compare regenerated data with `rebuildable_data_files`; retain the original motion manifest recorded here when checking old checkpoints. Do not silently accept a changed dataset hash.

The archive preserves unique outputs and source snapshots; caches and the virtual environment are reproducible, not archived binaries. No MPC/RL, pi-series, shared uv cache, or global Python installation is part of this cleanup.
''')
    for p in (manifest_path, restore, META / 'installed-packages.txt', META / 'pyvenv.cfg', META / 'original-motion-manifest.json'):
        command(['gh', 'release', 'upload', TAG, str(p), '--repo', REPO, '--clobber'])
    remote = json.loads(command(['gh', 'api', f'repos/{REPO}/releases/{release_id}']))
    for part in parts:
        asset = next(a for a in remote['assets'] if a['name'] == part['name'])
        assert asset['size'] == part['bytes'] and asset['digest'] == 'sha256:' + part['sha256']
    for p in (manifest_path, restore, META / 'installed-packages.txt', META / 'pyvenv.cfg', META / 'original-motion-manifest.json'):
        asset = next(a for a in remote['assets'] if a['name'] == p.name)
        assert asset['size'] == p.stat().st_size and asset['digest'] == 'sha256:' + digest(p)
    command(['gh', 'release', 'edit', TAG, '--repo', REPO, '--draft=false', '--latest=false'])
    assert not json.loads(command(['gh', 'api', f'repos/{REPO}/releases/{release_id}']))['draft']
    status('remote_verified', release_url=manifest['release_url'], archive_parts=len(parts))
    publish_metadata()
    if not args.delete_after_verify:
        return
    check_idle()
    expected_outputs = {e['path'] for e in manifest['entries'] if e['path'].startswith('outputs/')}
    actual_outputs = {str(p.relative_to(ROOT)) for p in (ROOT / 'outputs').rglob('*') if p.is_file() or p.is_symlink()}
    assert expected_outputs == actual_outputs, 'Output inventory changed during backup'
    for e in manifest['entries']:
        p = ROOT / e['path']
        if e['kind'] == 'file':
            assert p.stat().st_size == e['bytes'] and digest(p) == e['sha256'], e['path']
        else:
            assert os.readlink(p) == e['target'], e['path']
    targets = [ROOT / name for name in CLEANUP_TARGET_NAMES]
    for p in targets:
        resolved = p.resolve(strict=True)
        assert resolved.parent == ROOT or resolved.parent == ROOT / 'data'
        assert ROOT in resolved.parents and not p.is_symlink(), str(p)
    status('deleting_verified_storage', targets=[str(p) for p in targets])
    for p in targets:
        shutil.rmtree(p)  # Does not follow symlinks inside the checked project directories.
    git('worktree', 'prune')
    for p in STAGE.glob('supermimic.tar.zst.part-*'):
        assert p.parent.resolve() == STAGE.resolve()
        p.unlink()
    after = dict(zip(('total', 'used', 'free'), shutil.disk_usage(ROOT)))
    status('cleaned', release_url=manifest['release_url'], deleted_paths=[str(p) for p in targets],
           disk_before=manifest['disk_before'], disk_after=after,
           restored_from='results/storage_cleanup/20261101/RESTORE.md')
    publish_metadata()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        META.mkdir(parents=True, exist_ok=True)
        removed = [str(ROOT / name) for name in CLEANUP_TARGET_NAMES
                   if not (ROOT / name).exists()]
        status('failed', error=repr(exc), traceback=traceback.format_exc(), removed_paths=removed)
        raise
