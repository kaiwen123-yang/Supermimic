"""One-time 2026-11-11 export: frozen inventory, batch packing and exact unlink receipts."""
import collections
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import fcntl
import statistics

BASE = Path('/root/autodl-tmp/robot-repro')
STAGE = BASE / 'supermimic/work/storage_export_20261111'
P12 = BASE / 'supermimic-p12-world-window'
ROOT_NAMES = ['supermimic', 'supermimic-p3-h32', 'supermimic-p4-c0',
              'supermimic-p5-stability', 'supermimic-p6-position-feedback',
              'supermimic-p7-reproduction', 'supermimic-p8-stability-scale',
              'supermimic-p9-critic-full-scale', 'supermimic-p10-8k-hard-practice',
              'supermimic-p11-root-height-consistency', 'supermimic-p12-world-window']
ROOTS = [BASE / n for n in ROOT_NAMES]


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def within(p, root):
    return p == root or root in p.parents


def snapshot():
    active, open_paths = [], set()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            argv = (proc / 'cmdline').read_bytes().decode(errors='replace').split('\0')
            cwd = (proc / 'cwd').resolve(strict=True)
            cmd = ' '.join(argv)
            if 'storage_export_h_' in cmd or 'storage_export_20261111' in cmd:
                continue
            relevant = any(within(cwd, root) or str(root) in cmd for root in ROOTS)
            if not relevant:
                continue
            if not any(x in cmd for x in ('python', 'train', 'evaluate', 'publish', 'finish_', 'start_p', 'prepare_', 'fetch_bones')):
                continue
            paths = []
            for fd in (proc / 'fd').iterdir():
                try:
                    target = str(fd.resolve(strict=True))
                    if target.startswith(str(BASE) + '/supermimic'):
                        open_paths.add(target)
                except OSError:
                    pass
            for line in (proc / 'maps').read_text().splitlines():
                parts = line.split(None, 5)
                if len(parts) == 6 and parts[5].startswith(str(BASE) + '/supermimic'):
                    open_paths.add(parts[5])
            for arg in argv:
                if arg.startswith('/') or arg.startswith(('outputs/', 'data/', 'configs/', 'results/')):
                    target = Path(arg) if arg.startswith('/') else cwd / arg
                    if target.exists():
                        paths.append(str(target.resolve()))
                        if target.suffix == '.json' and target.stat().st_size < 10000000:
                            for s in path_strings(json.loads(target.read_text())):
                                dep = Path(s) if s.startswith('/') else cwd / s
                                if dep.exists():
                                    paths.append(str(dep.resolve()))
            active.append({'pid': int(proc.name), 'cwd': str(cwd), 'argv': argv, 'paths': paths})
        except (OSError, ProcessLookupError):
            continue
    return {'observed_unix': time.time(), 'processes': active, 'open_paths': sorted(open_paths),
            'p12_worktree_exists': P12.exists(), 'disk': dict(zip(('total','used','free'), shutil.disk_usage(BASE)))}


def walk_files(folder, links):
    if folder.is_symlink():
        links.append({'path': str(folder), 'target': os.readlink(folder), 'resolved': str(folder.resolve())})
        return
    if not folder.exists():
        return
    for directory, dirs, files in os.walk(folder, followlinks=False):
        p = Path(directory)
        for name in list(dirs):
            child = p / name
            if name in ('.git', '.venv', '__pycache__', '.cache'):
                dirs.remove(name)
            elif child.is_symlink():
                links.append({'path': str(child), 'target': os.readlink(child), 'resolved': str(child.resolve())})
                dirs.remove(name)
        for name in files:
            child = p / name
            if child.is_symlink():
                links.append({'path': str(child), 'target': os.readlink(child), 'resolved': str(child.resolve())})
            elif child.is_file():
                yield child


def path_strings(obj):
    if isinstance(obj, str):
        if obj.startswith(('/root/autodl-tmp/robot-repro/supermimic', 'data/', 'outputs/', 'results/', 'configs/')):
            yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from path_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from path_strings(value)


def inventory():
    observed = snapshot()
    links, entries, metadata = [], [], []
    for root in ROOTS:
        if not root.exists():
            continue
        runs = list((root / 'outputs/runs').glob('*'))
        runmeta, campaigns = {}, set()
        for run in runs:
            cfgfile = run / 'config.json'
            cfg = json.loads(cfgfile.read_text()) if cfgfile.exists() else {}
            campaign = cfg.get('campaign') or run.name.rsplit('-', 1)[0]
            campaigns.add(campaign)
            statusfile = run / 'status.json'
            status_obj = json.loads(statusfile.read_text()) if statusfile.exists() else {}
            deps = []
            for s in path_strings(cfg):
                target = Path(s) if s.startswith('/') else root / s
                deps.append({'configured': s, 'resolved': str(target.resolve()), 'exists': target.exists()})
            ckpts = [int(m.group(1)) for x in run.glob('checkpoint_*.pt') if (m := re.fullmatch(r'checkpoint_(\d+)\.pt', x.name))]
            runmeta[run.name] = {'campaign': campaign, 'final_iteration': status_obj.get('iteration', max(ckpts, default=0)),
                                 'status': status_obj.get('status'), 'dependencies': deps}
        tracked = set(subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0'))
        metadata.append({'root': str(root), 'runs': runmeta,
                         'git_head': subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
                         'git_status': subprocess.check_output(['git','-C',str(root),'status','--short'],text=True)})
        folders = [root/'outputs', root/'data/raw', root/'data/processed', root/'checkpoints']
        for campaign in campaigns:
            folders.append(root/'results'/campaign)
        for run in runmeta:
            folders.append(root/'results'/run)
        seen = set()
        for folder in folders:
            for p in walk_files(folder, links):
                if str(p) in seen:
                    continue
                seen.add(str(p))
                st = p.stat()
                rel = p.relative_to(root).as_posix()
                parts = Path(rel).parts
                run = parts[2] if rel.startswith('outputs/runs/') else root.name
                campaign = runmeta.get(run, {}).get('campaign', root.name)
                action, reason = 'copy_only_keep_server', 'unknown dependency or metadata retained'
                category = '07_results_and_configs'
                if rel.startswith('data/processed/'):
                    category, reason = '02_processed_data/active_copy_only', 'processed data and all real backing files retained'
                    campaign, run = root.name, parts[2]
                elif rel.startswith('data/raw/'):
                    category = '01_source_datasets/BONES' if 'bones' in rel.lower() else '01_source_datasets/LAFAN1'
                    campaign, run = root.name, parts[2]
                    action, reason = 'move_after_confirm', 'historical raw source; training reads processed data'
                    if any((a/'.git').exists() for a in p.parents if within(a, root/'data/raw')):
                        action, reason = 'copy_only_keep_server', 'raw dataset source checkout retained'
                elif p.suffix == '.pt' or rel.startswith('checkpoints/'):
                    category = '03_checkpoints/anchors_copy_only'
                    m = re.fullmatch(r'checkpoint_(\d+)\.pt', p.name)
                    if m and '/runs/' in str(p) and int(m.group(1)) % 1000 != 0 and int(m.group(1)) != runmeta[run]['final_iteration']:
                        category, action, reason = '03_checkpoints/historical', 'move_after_confirm', 'closed run old rolling checkpoint'
                    else:
                        reason = 'parent, milestone, final, latest or unspecified checkpoint retained'
                elif p.suffix.lower() in ('.mp4','.avi','.webm','.mov','.gif'):
                    category, action, reason = '06_videos', 'move_after_confirm', 'closed historical video'
                elif rel.startswith('outputs/') and (p.suffix.lower() in ('.npz','.npy','.h5','.hdf5') or 'trajector' in rel):
                    category, action, reason = '04_trajectories', 'move_after_confirm', 'closed historical trajectory or numeric evidence'
                elif rel.startswith('outputs/') and (p.suffix in ('.log','.jsonl') or 'tfevents' in p.name):
                    category, action, reason = '05_logs', 'move_after_confirm', 'closed historical log'
                elif rel.startswith('outputs/') and p.name.endswith(('.tar.gz','.tar.zst','.tar','.zip','.tgz')):
                    category, action, reason = '04_trajectories', 'move_after_confirm', 'historical packaged artifact'
                if rel in tracked or rel.startswith('results/') or p.suffix in ('.py','.sh','.lock'):
                    action, reason = 'copy_only_keep_server', 'tracked file, fixed evidence, code or lock retained'
                if within(p, P12):
                    action, reason = 'defer_active', 'entire P12 scope reserved, including future files'
                for proc in observed['processes']:
                    procroot = Path(proc['cwd'])
                    if within(p, procroot) or str(p) in proc['paths'] or str(p) in observed['open_paths']:
                        action, reason = 'defer_active', 'live process or open mapped file'
                entries.append({'source_path': str(p), 'relative_path': str(p).lstrip('/'), 'project': str(root),
                                'category': category, 'campaign': campaign, 'run': run,
                                'size_bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'ctime_ns': st.st_ctime_ns,
                                'device': st.st_dev, 'inode': st.st_ino, 'nlink': st.st_nlink,
                                'action': action, 'keep_reason': reason, 'archive_name': None})
    return {'observed': observed, 'projects': metadata, 'links': links, 'entries': entries,
            'protected_scope': [str(P12), 'all source, git/stash, environment, assets, caches and work directories are excluded from deletion'],
            'created_unix': time.time()}


def unchanged(entry):
    p = Path(entry['source_path'])
    if p.is_symlink() or not p.is_file() or str(p.resolve()) != str(p):
        return False
    s = p.stat()
    return (s.st_size, s.st_mtime_ns, s.st_dev, s.st_ino) == (entry['size_bytes'], entry['mtime_ns'], entry['device'], entry['inode'])


def dependency_reason(entry, observed):
    p = Path(entry['source_path'])
    if within(p, P12):
        return 'P12 reserved scope'
    for proc in observed['processes']:
        if within(p, Path(proc['cwd'])):
            return 'project has live computation/publication'
        if any(within(p, Path(x)) for x in proc['paths']):
            return 'live command/config dependency'
    if str(p) in observed['open_paths']:
        return 'open or mapped by live process'
    return None


def training_gate(session, observed):
    """Compare existing normal training logs only; no new training or benchmark."""
    with (session/'timing.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = session/'training_timings.json'
        history = json.loads(target.read_text()) if target.exists() else {}
        for proc in observed['processes']:
            if not any('train.py' in x for x in proc['argv']):
                continue
            root = Path(proc['cwd'])
            for log in (root/'outputs/runs').glob('*/metrics.jsonl'):
                if time.time()-log.stat().st_mtime > 180:
                    continue
                with log.open('rb') as f:
                    f.seek(max(0,log.stat().st_size-2000000))
                    rows = f.read().splitlines()[1:]
                values = []
                for row in rows:
                    try:
                        x = json.loads(row)
                    except json.JSONDecodeError:
                        continue
                    if all(k in x for k in ('collection_seconds','world_seconds','policy_critic_seconds','checkpoint_write_seconds')):
                        values.append((x['iteration'], sum(x[k] for k in ('collection_seconds','world_seconds','policy_critic_seconds','checkpoint_write_seconds'))))
                if len(values) < 40:
                    continue
                key = str(log)
                h = history.setdefault(key, {'baseline': statistics.median(v for _,v in values[-40:-20]), 'slow_windows': 0, 'last_iteration': 0})
                if values[-1][0]-h['last_iteration'] < 100:
                    continue
                h['recent_median'] = statistics.median(v for _,v in values[-20:])
                h['last_iteration'] = values[-1][0]
                h['slow_windows'] = h['slow_windows']+1 if h['recent_median'] > h['baseline']*1.5 else 0
                if h['slow_windows'] >= 3:
                    write(session/'PAUSE.json', {'reason':'sustained training slowdown; only migration paused','log':key,**h})
        write(target, history)
    return not (session/'PAUSE.json').exists()


def pack(request_path):
    b = json.loads(request_path.read_text())
    session = request_path.parent
    observed = snapshot()
    if not training_gate(session, observed):
        return {'status':'paused','reason':'sustained training slowdown'}
    entries, skipped = [], []
    for entry in b['entries']:
        reason = None if unchanged(entry) else 'source identity/size/mtime changed or missing'
        reason = reason or dependency_reason(entry, observed)
        if reason:
            skipped.append({'source_path': entry['source_path'], 'reason': reason})
        else:
            entries.append(entry)
    if not entries:
        return {'status':'deferred','skipped':skipped}
    direct = len(entries)==1 and b['direct_archive']
    if direct:
        output = Path(entries[0]['source_path'])
    else:
        expected_bytes = sum(e['size_bytes'] for e in entries)
        with (session/'packing_space.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            reservation_path = session/'reservations.json'
            reservations = json.loads(reservation_path.read_text()) if reservation_path.exists() else {}
            if shutil.disk_usage(BASE).free-sum(reservations.values())-expected_bytes < 30*1024**3:
                return {'status':'deferred','reason':'preserve 30 GiB training headroom','skipped':skipped}
            reservations[b['id']] = expected_bytes
            write(reservation_path, reservations)
        output = session/b['archive_name']
        temporary = output.with_name(output.name+'.partial')
        listing = session/(b['id']+'.files.nul')
        listing.write_bytes(b''.join(e['relative_path'].encode()+b'\0' for e in entries))
        tarcmd = ['tar','--format=posix','--hard-dereference','--no-recursion','--null','--verbatim-files-from','-C','/','-T',str(listing),'-cf','-']
        try:
            with temporary.open('xb') as out:
                if b['compression']=='zstd':
                    first = subprocess.Popen(tarcmd,stdout=subprocess.PIPE)
                    second = subprocess.run(['/root/miniconda3/bin/zstd','-T2','-1','-q','-c'],stdin=first.stdout,stdout=out)
                    first.stdout.close()
                    if first.wait()!=0 or second.returncode!=0:
                        raise RuntimeError('tar/zstd packing failed; source retained')
                else:
                    subprocess.run(tarcmd,stdout=out,check=True)
            if not all(unchanged(e) for e in entries):
                raise RuntimeError('source changed while packing; source retained')
            temporary.rename(output)
        finally:
            with (session/'packing_space.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                reservations = json.loads(reservation_path.read_text())
                reservations.pop(b['id'],None)
                write(reservation_path,reservations)
    st = output.stat()
    return {'status':'packed','id':b['id'],'server_archive_path':str(output),'server_bytes':st.st_size,
            'archive_mtime_ns':st.st_mtime_ns,'archive_inode':st.st_ino,'archive_is_source':direct,
            'entries':entries,'skipped':skipped,'packed_unix':time.time()}


def finalize(request_path, acknowledgement):
    b = json.loads(request_path.read_text())
    packed = json.loads(request_path.with_suffix('.packed.json').read_text())
    if acknowledgement['local_bytes']!=packed['server_bytes'] or acknowledgement['local_read_status']!='complete':
        raise RuntimeError('local byte and full-read acknowledgement required')
    observed = snapshot()
    deleted, kept = [], []
    for e in packed['entries']:
        p = Path(e['source_path'])
        reason = e['keep_reason'] if e['action']!='move_after_confirm' else None
        allowed = any(within(p, r/'outputs') or within(p, r/'data/raw') for r in ROOTS if r!=P12)
        if not allowed:
            reason = reason or 'outside exact authorized deletion areas'
        reason = reason or dependency_reason(e,observed)
        if not unchanged(e):
            reason = reason or 'source identity/size/mtime changed or missing'
        if reason:
            kept.append({'source_path':str(p),'size_bytes':e['size_bytes'],'reason':reason})
        else:
            p.unlink()
            deleted.append({'source_path':str(p),'size_bytes':e['size_bytes'],'deleted_unix':time.time()})
            with (request_path.parent/(b['id']+'.deleted.jsonl')).open('a') as receipt:
                receipt.write(json.dumps(deleted[-1])+'\n')
                receipt.flush()
                os.fsync(receipt.fileno())
    archive = Path(packed['server_archive_path'])
    temp_deleted = False
    if not packed['archive_is_source'] and archive.exists():
        st = archive.stat()
        if archive.parent==request_path.parent and (st.st_size,st.st_mtime_ns,st.st_ino)==(packed['server_bytes'],packed['archive_mtime_ns'],packed['archive_inode']):
            archive.unlink()
            temp_deleted=True
    result={'id':b['id'],'local_confirmation':acknowledgement,'deleted':deleted,'kept':kept,
            'deleted_bytes':sum(e['size_bytes'] for e in deleted),'kept_bytes':sum(e['size_bytes'] for e in kept),
            'server_temp_removed':temp_deleted,'disk_after':dict(zip(('total','used','free'),shutil.disk_usage(BASE))),
            'completed_unix':time.time()}
    write(request_path.with_suffix('.receipt.json'),result)
    return result


def serve(session,slot):
    last = None
    while not (session/'FINISHED.json').exists():
        pointer = session/f'slot{slot}.json'
        if pointer.exists() and not (session/'PAUSE.json').exists():
            batch_id = json.loads(pointer.read_text())['id']
            if batch_id != last:
                request_path=session/(batch_id+'.json')
                try:
                    result=pack(request_path)
                except Exception as exc:
                    result={'status':'error','id':batch_id,'error':repr(exc)}
                write(request_path.with_suffix('.packed.json'),result)
                print(json.dumps({'time':time.time(),'id':batch_id,'status':result['status']}),flush=True)
                last=batch_id
        time.sleep(1)


if __name__ == '__main__':
    if sys.argv[1] == 'inventory':
        print(json.dumps(inventory(), ensure_ascii=False))
    elif sys.argv[1] == 'snapshot':
        print(json.dumps(snapshot(), ensure_ascii=False))
    elif sys.argv[1] == 'serve':
        serve(Path(sys.argv[2]),sys.argv[3])
    elif sys.argv[1] == 'submit':
        request=json.load(sys.stdin)
        session=STAGE/request['session']
        write(session/(request['id']+'.json'),request)
        write(session/f'slot{sys.argv[2]}.json',{'id':request['id']})
        print(json.dumps({'submitted':request['id']}))
    elif sys.argv[1] == 'poll':
        p=STAGE/sys.argv[2]/(sys.argv[3]+'.packed.json')
        print(p.read_text() if p.exists() else '{"status":"packing"}')
    elif sys.argv[1] == 'finalize':
        print(json.dumps(finalize(STAGE/sys.argv[2]/(sys.argv[3]+'.json'),json.load(sys.stdin))))
    elif sys.argv[1] == 'finish':
        write(STAGE/sys.argv[2]/'FINISHED.json',json.load(sys.stdin))
