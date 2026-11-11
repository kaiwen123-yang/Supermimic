"""Explicitly authorized 2026-11-11 NPZ cleanup; never removes directories.

The H archives must have been fully read by the local verifier. The original
export batch manifests supply the exact file list. No hashing or model loading.
"""
import collections
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

BASE=Path('/root/autodl-tmp/robot-repro')
EXPORT=BASE/'supermimic/work/storage_export_20261111/20261111_1144'
STAGE=BASE/'supermimic/work/npz_cleanup_20261111_2034'
O1=BASE/'supermimic-official-workspace'
P4=BASE/'supermimic-p4-c0/data/processed/lafan1_g1_50hz'
MEMMAP=BASE/'supermimic-p9-critic-full-scale/data/processed/bones_full_lafan_p9'
ALLOWED=(BASE/'supermimic-p8-stability-scale/data/processed/bones_g1_50hz_full',
         BASE/'supermimic-p8-stability-scale/data/processed/bones_g1_50hz_40h_s0',
         BASE/'supermimic-p9-critic-full-scale/data/processed/bones_g1_50hz_full_p9')
STAGE.mkdir(parents=True,exist_ok=True)

def write(path,obj):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w') as stream:
        json.dump(obj,stream,separators=(',',':'))
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    temp.replace(path)

def inside(path,root):
    return path==root or root in path.parents

def identity(path):
    p=Path(path)
    s=p.stat()
    return {'source_path':str(p),'size_bytes':s.st_size,'mtime_ns':s.st_mtime_ns,
            'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated_bytes':s.st_blocks*512}

def unchanged(record):
    p=Path(record['source_path'])
    try:s=p.lstat()
    except FileNotFoundError:return False
    return stat.S_ISREG(s.st_mode) and not p.is_symlink() and str(p.resolve())==str(p) and (
        s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(record['device'],record['inode'],record['size_bytes'],record['mtime_ns'])

def dependency_check():
    manifest=O1/'data/lafan40_official_npz/manifest.json'
    data=json.loads(manifest.read_text())
    if data['clip_count']!=40:raise RuntimeError('O1 data definition changed')
    if {p.name for p in (O1/'data').iterdir()}!={'lafan40_existing50hz','lafan40_official_npz'}:
        raise RuntimeError('O1 data directory now has additional inputs; review before cleanup')
    dependency_files=[manifest]
    for clip in data['clips']:
        official=Path(clip['official_motion_path']).resolve(strict=True)
        source=Path(clip['source']).resolve(strict=True)
        if official.parent!=(O1/'data/lafan40_official_npz').resolve() or source.parent!=P4.resolve():
            raise RuntimeError('O1 input path changed: '+str(official))
        dependency_files.extend([official,source])
    for child in (O1/'data').iterdir():
        resolved=child.resolve(strict=True)
        if any(inside(resolved,directory) or inside(directory,resolved) for directory in ALLOWED):
            raise RuntimeError('O1 data directory now references an authorized deletion directory')
    full_manifest=json.loads((ALLOWED[2]/'manifest.json').read_text())
    if Path(full_manifest['reference_store']['directory']).resolve()!=MEMMAP.resolve():
        raise RuntimeError('P9 backing store changed')
    for name in ['qpos','qvel','body_pos','body_quat','body_lin_vel','body_ang_vel']:
        p=MEMMAP/(name+'.npy')
        if not p.is_file() or p.is_symlink():raise RuntimeError('P9 backing array missing or redirected')
    blocked=[];o1_processes=[];open_npz=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:
            argv=(proc/'cmdline').read_bytes().decode(errors='replace').split('\0')
            cmd=' '.join(argv)
            if 'cleanup_retired_bones_npz_20261111.py' in cmd or 'npz_cleanup_20261111_2034' in cmd:continue
            cwd=(proc/'cwd').resolve(strict=True)
            if inside(cwd,O1) and 'train_official.py' in cmd:
                o1_processes.append({'pid':int(proc.name),'cwd':str(cwd)})
            if any(inside(cwd,BASE/name) or str(BASE/name)+'/' in cmd for name in ['supermimic-p8-stability-scale','supermimic-p9-critic-full-scale']):
                if any(token in cmd for token in ['python','train','evaluate','prepare']):
                    blocked.append({'pid':int(proc.name),'cwd':str(cwd),'program':argv[:2]})
            for fd in (proc/'fd').iterdir():
                try:target=os.readlink(fd).removesuffix(' (deleted)')
                except OSError:continue
                p=Path(target)
                if p.suffix=='.npz' and p.parent in ALLOWED:open_npz.append({'pid':int(proc.name),'path':target})
            for line in (proc/'maps').read_text().splitlines():
                parts=line.split(None,5)
                if len(parts)==6:
                    p=Path(parts[5].removesuffix(' (deleted)'))
                    if p.suffix=='.npz' and p.parent in ALLOWED:open_npz.append({'pid':int(proc.name),'path':str(p)})
        except (OSError,ProcessLookupError):continue
    if blocked or open_npz:
        write(STAGE/'dependency_block.json',{'observed_unix':time.time(),'active_legacy_processes':blocked,'open_candidate_files':open_npz})
        raise RuntimeError('Current process dependencies require preserving the candidate NPZ files')
    return {'observed_unix':time.time(),'O1_processes':o1_processes,'O1_manifest':str(manifest),
            'O1_official_motion_paths':[c['official_motion_path'] for c in data['clips']],
            'O1_source_paths':[c['source'] for c in data['clips']],
            'P9_reference_store':full_manifest['reference_store'],'open_candidate_files':open_npz},dependency_files

def preflight():
    request=json.loads((STAGE/'request.json').read_text())
    if {str(Path(p)) for p in request['approved_directories']}!={str(p) for p in ALLOWED}:
        raise RuntimeError('Authorization scope differs from the three explicit directories')
    for directory in ALLOWED:
        if directory.resolve()!=directory or not directory.is_dir():raise RuntimeError('Candidate directory redirected or missing')
    activity,o1_files=dependency_check()
    protected_paths=set(request['protected_checkpoints'])
    protected_paths.update(str(p) for p in P4.iterdir() if p.is_file())
    protected_paths.update(str(p) for p in MEMMAP.iterdir() if p.is_file())
    protected_paths.update(str(p/'manifest.json') for p in ALLOWED)
    protected_paths.update(str(p) for p in o1_files)
    protected={p:identity(p) for p in sorted(protected_paths)}
    protected_inodes={(r['device'],r['inode']) for r in protected.values()}
    groups={};seen=set();archive_sizes={}
    for batch_id in request['archive_batches']:
        packed=json.loads((EXPORT/(batch_id+'.packed.json')).read_text())
        if packed['status']!='packed':raise RuntimeError('Export batch not packed: '+batch_id)
        archive_sizes[batch_id]=packed['server_bytes']
        for entry in packed['entries']:
            p=Path(entry['source_path'])
            if p.parent not in ALLOWED or p.suffix!='.npz':continue
            if str(p) in seen:raise RuntimeError('Duplicate source path')
            seen.add(str(p))
            if not unchanged(entry):raise RuntimeError('Changed or non-regular source: '+str(p))
            current=identity(p);key=(current['device'],current['inode'])
            if key in protected_inodes:raise RuntimeError('Candidate inode aliases a protected file')
            group=groups.setdefault(key,{'device':key[0],'inode':key[1],'size_bytes':current['size_bytes'],
                                         'mtime_ns':current['mtime_ns'],'nlink':current['nlink'],
                                         'allocated_bytes':current['allocated_bytes'],'paths':[]})
            group['paths'].append({'source_path':str(p),'archive_batch':batch_id})
    if len(seen)!=request['expected_paths'] or sum(g['size_bytes']*len(g['paths']) for g in groups.values())!=request['expected_logical_bytes']:
        raise RuntimeError('Frozen source list differs from the user-reviewed scope')
    for group in groups.values():
        if len(group['paths'])!=group['nlink']:
            raise RuntimeError('Hard-link dependencies changed for '+group['paths'][0]['source_path'])
    with (STAGE/'frozen_inode_groups.jsonl').open('w') as out:
        for group in sorted(groups.values(),key=lambda x:x['paths'][0]['source_path']):
            out.write(json.dumps(group,separators=(',',':'))+'\n')
    write(STAGE/'protected_before.json',protected)
    result={'status':'preflight_passed','created_unix':time.time(),'selected_paths':len(seen),
            'unique_inodes':len(groups),'logical_path_bytes':sum(g['size_bytes']*len(g['paths']) for g in groups.values()),
            'allocated_bytes_at_last_link':sum(g['allocated_bytes'] for g in groups.values()),
            'protected_files':len(protected),'protected_checkpoint_count':len(request['protected_checkpoints']),
            'activity':activity,'archive_sizes':archive_sizes}
    write(STAGE/'preflight.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['activity','archive_sizes']}),flush=True)

def check_protected(protected):
    changed=[p for p,record in protected.items() if not unchanged(record)]
    if changed:
        write(STAGE/'protected_change.json',{'paths':changed,'observed_unix':time.time()})
        raise RuntimeError('Protected files changed; stop this cleanup only')

def delete():
    with (STAGE/'cleanup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pre=json.loads((STAGE/'preflight.json').read_text())
        confirmation=json.loads((STAGE/'H_archive_confirmation.json').read_text())
        if confirmation['status']!='all_H_archives_fully_read':raise RuntimeError('H archive clearance is missing')
        verified={a['id']:a for a in confirmation['archives']}
        if set(verified)!=set(pre['archive_sizes']):raise RuntimeError('H archive set differs from the frozen source list')
        for batch_id,size in pre['archive_sizes'].items():
            if verified[batch_id]['bytes']!=size or verified[batch_id]['local_read_status']!='complete' or verified[batch_id]['read_exit_code']!=0:
                raise RuntimeError('H archive did not pass the required full read')
        if (STAGE/'deletion_journal.jsonl').exists():raise RuntimeError('Existing deletion journal: reconcile it instead of repeating cleanup')
        protected=json.loads((STAGE/'protected_before.json').read_text())
        activity_before,_=dependency_check();check_protected(protected)
        disk_before=dict(zip(('total','used','free'),shutil.disk_usage(BASE)))
        started=time.time();paths_deleted=0;logical_deleted=0;allocated_released=0;groups_done=0
        skipped=[]
        with (STAGE/'deletion_journal.jsonl').open('x') as journal, (STAGE/'frozen_inode_groups.jsonl').open() as source:
            for line in source:
                group=json.loads(line)
                if groups_done%2000==0:
                    activity,_=dependency_check();check_protected(protected)
                records=[{**group,**p} for p in group['paths']]
                if not all(unchanged(r) and Path(r['source_path']).stat().st_nlink==group['nlink'] for r in records):
                    skipped.append({'paths':[r['source_path'] for r in records],'reason':'identity, size, mtime or hard-link count changed'})
                    groups_done+=1;continue
                removed=[]
                for index,record in enumerate(records):
                    p=Path(record['source_path'])
                    if p.parent not in ALLOWED or p.suffix!='.npz' or not unchanged(record) or p.stat().st_nlink!=group['nlink']-index:
                        skipped.append({'paths':[r['source_path'] for r in records[index:]],'reason':'file changed during this inode group'})
                        break
                    p.unlink()
                    removed.append(record['source_path'])
                    paths_deleted+=1;logical_deleted+=group['size_bytes']
                complete=len(removed)==len(records)
                if complete:allocated_released+=group['allocated_bytes']
                journal.write(json.dumps({'device':group['device'],'inode':group['inode'],'deleted_paths':removed,
                                          'logical_bytes':group['size_bytes']*len(removed),
                                          'allocated_bytes_at_final_unlink':group['allocated_bytes'] if complete else 0,
                                          'deleted_unix':time.time()},separators=(',',':'))+'\n')
                journal.flush();os.fsync(journal.fileno())
                groups_done+=1
                if groups_done%2000==0:
                    progress={'status':'deleting','groups_done':groups_done,'paths_deleted':paths_deleted,'logical_deleted_bytes':logical_deleted,
                              'allocated_bytes_at_final_unlink':allocated_released,'skipped_groups':len(skipped),'updated_unix':time.time()}
                    write(STAGE/'progress.json',progress)
                    print(json.dumps(progress),flush=True)
        for directory in ALLOWED:
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
            os.fsync(fd);os.close(fd)
        remaining=[]
        with (STAGE/'frozen_inode_groups.jsonl').open() as source:
            for line in source:
                for p in json.loads(line)['paths']:
                    if os.path.lexists(p['source_path']):remaining.append(p['source_path'])
        activity_after,_=dependency_check();check_protected(protected)
        disk_after=dict(zip(('total','used','free'),shutil.disk_usage(BASE)))
        result={'status':'completed' if not remaining and not skipped else 'completed_with_remaining',
                'started_unix':started,'finished_unix':time.time(),'selected_paths':pre['selected_paths'],
                'deleted_paths':paths_deleted,'logical_deleted_bytes':logical_deleted,
                'unique_inode_groups_processed':groups_done,'allocated_file_bytes_at_final_unlink':allocated_released,
                'disk_before':disk_before,'disk_after':disk_after,'filesystem_free_delta_bytes':disk_after['free']-disk_before['free'],
                'remaining_selected_paths':remaining,'skipped':skipped,'protected_files_unchanged':len(protected),
                'protected_checkpoints_unchanged':pre['protected_checkpoint_count'],
                'activity_before':activity_before,'activity_after':activity_after,'H_archive_files_modified':False,
                'directories_deleted':0,'manifests_deleted':0,'memmap_arrays_deleted':0}
        write(STAGE/'result.json',result);write(STAGE/'progress.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ['activity_before','activity_after','remaining_selected_paths','skipped']}),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='preflight':preflight()
    elif sys.argv[1]=='delete':delete()
