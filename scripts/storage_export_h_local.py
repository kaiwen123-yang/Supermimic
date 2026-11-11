"""Local Windows controller for the explicitly authorized one-time H-drive export."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
import collections
import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import time

SESSION = '20261111_1144'
ARCHIVE = Path(r'H:\Supermimic')
META = ARCHIVE/'00_inventory'/SESSION
REPO = Path(__file__).resolve().parents[1]
REMOTE = '/root/autodl-tmp/robot-repro/supermimic/work/storage_export_20261111'
SCRIPT = REMOTE+'/storage_export_h_remote.py'
SSH = r'C:\Windows\System32\OpenSSH\ssh.exe'
SCP = r'C:\Windows\System32\OpenSSH\scp.exe'
TAR = r'C:\Windows\System32\tar.exe'
GIT = r'C:\Program Files\Git\cmd\git.exe'
OPTIONS = ['-o','BatchMode=yes','-o','Compression=no','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=10']
WORKERS = 4
LOCK = threading.Lock()
PAUSED = threading.Event()
STATES = {}
PLAN = None


def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(p)


def remote(*args,payload=None):
    cmd=['/root/miniconda3/bin/python',SCRIPT,*args]
    p=subprocess.run([SSH,*OPTIONS,'autodl-d57',*cmd],input=json.dumps(payload).encode() if payload is not None else None,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-2000:])
    return json.loads(p.stdout)


def prepare():
    d=json.loads((META/'inventory.json').read_bytes())
    projects={p['root']:p for p in d['projects']}
    groups=collections.defaultdict(list)
    for e in d['entries']:
        runs=projects[e['project']]['runs']
        if e['run']==Path(e['project']).name:
            for run,details in sorted(runs.items(),key=lambda x:-len(x[0])):
                if run in e['source_path']:
                    e['run']=run
                    e['campaign']=details['campaign']
                    break
            if e['campaign']==Path(e['project']).name and runs:
                e['campaign']=next(iter(runs.values()))['campaign']
        if '/outputs/parents/' in e['source_path'] and 'working_data' in e['source_path']:
            e['category']='02_processed_data/retired'
        if e['action']=='defer_active':
            continue
        groups[(e['category'],e['campaign'],e['run'],e['action'])].append(e)
    batches=[]
    priorities={'04_trajectories':0,'05_logs':0,'06_videos':0,'03_checkpoints/historical':1,
                '02_processed_data/retired':2,'01_source_datasets/BONES':2,'01_source_datasets/LAFAN1':2,
                '03_checkpoints/anchors_copy_only':3,'07_results_and_configs':4,'02_processed_data/active_copy_only':5}
    for key,entries in sorted(groups.items(),key=lambda item:(priorities[item[0][0]],item[0][1:])):
        current=[]
        size=0
        for e in sorted(entries,key=lambda e:(-e['size_bytes'],e['source_path'])):
            direct=e['source_path'].endswith(('.tar.gz','.tar.zst','.tar','.zip','.tgz'))
            if current and (size+e['size_bytes']>2*1024**3 or len(current)>=5000 or direct):
                batches.append((key,current,False));current=[];size=0
            if direct:
                batches.append((key,[e],True))
            else:
                current.append(e);size+=e['size_bytes']
        if current:
            batches.append((key,current,False))
    index=[]
    for number,(key,entries,direct) in enumerate(batches,1):
        batch_id=f'b{number:04d}'
        category,campaign,run,action=key
        compress=category=='05_logs' or (category=='02_processed_data/active_copy_only' and all(e['source_path'].endswith('.npy') for e in entries))
        suffix=('__'+Path(entries[0]['source_path']).name) if direct else ('.tar.zst' if compress else '.tar')
        archive_name=f'smh_{SESSION}_{batch_id}{suffix}'
        relative=str(Path(category)/campaign/run/archive_name)
        b={'id':batch_id,'session':SESSION,'category':category,'campaign':campaign,'run':run,'action':action,
           'archive_name':archive_name,'local_relative_path':relative,'direct_archive':direct,
           'compression':'zstd' if compress else 'none','source_bytes':sum(e['size_bytes'] for e in entries),
           'file_count':len(entries),'entries':entries}
        for e in entries:
            e['archive_name']=archive_name
        write(META/'batches'/(batch_id+'.json'),b)
        index.append({k:v for k,v in b.items() if k!='entries'})
    with (META/'file_manifest.jsonl').open('w',encoding='utf-8') as out:
        for e in d['entries']:
            out.write(json.dumps(e,ensure_ascii=False,separators=(',',':'))+'\n')
    protected=[{'source_path':e['source_path'],'reason':e['keep_reason'],'size_bytes':e['size_bytes']} for e in d['entries']
               if e['category']=='03_checkpoints/anchors_copy_only']
    write(META/'protection.json',{'checkpoint_files':protected,'links':d['links'],'projects':d['projects'],
          'reserved_p12_root':'/root/autodl-tmp/robot-repro/supermimic-p12-world-window',
          'excluded':'source, Git/stash, environments, robot assets, runtime caches, work/locks and other projects',
          'fixed_inputs':'all tracked results and P10 fixed tails / P11 residual parent evidence stay on server'})
    plan={'session':SESSION,'inventory_unix':d['created_unix'],'observed':d['observed'],'workers':WORKERS,
          'bandwidth_limit':None,'pack_threads_per_compressed_batch':2,'reserve_server_bytes':30*1024**3,
          'file_count':len(d['entries']),'source_bytes':sum(e['size_bytes'] for e in d['entries']),
          'planned_move_bytes':sum(e['size_bytes'] for e in d['entries'] if e['action']=='move_after_confirm'),
          'planned_keep_bytes':sum(e['size_bytes'] for e in d['entries'] if e['action']=='copy_only_keep_server'),
          'deferred_files':[e for e in d['entries'] if e['action']=='defer_active'],'batches':index}
    write(META/'plan.json',plan)
    print(json.dumps({k:v for k,v in plan.items() if k not in ('batches','observed','deferred_files')}))
    print('batches',len(index),flush=True)


def summary():
    done=[x for x in STATES.values() if x.get('status')=='complete']
    return {'session':SESSION,'updated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'status':'paused_training_slowdown' if PAUSED.is_set() else 'running',
            'local_root':str(ARCHIVE),'tmux_local':'sm-export-h-20261111','tmux_server':'sm-export-h-20261111',
            'workers':WORKERS,'bandwidth_limit':None,'planned_files':PLAN['file_count'],'planned_source_bytes':PLAN['source_bytes'],
            'planned_move_bytes':PLAN['planned_move_bytes'],'planned_keep_bytes':PLAN['planned_keep_bytes'],
            'total_batches':len(PLAN['batches']),'completed_batches':len(done),
            'verified_archive_bytes':sum(x.get('local_bytes',0) for x in done),
            'exported_source_bytes':sum(x.get('exported_source_bytes',0) for x in done),
            'server_deleted_bytes':sum(x.get('deleted_bytes',0) for x in done),
            'exported_kept_source_bytes':sum(x.get('kept_bytes',0) for x in done),
            'server_last_observed_free_bytes':max((x for x in done),key=lambda x:x.get('completed_unix',0),default={}).get('server_free_bytes'),
            'deferred_scope':PLAN['deferred_files'],
            'p12_scope':'reserved in its entirety; future newly created files are outside this frozen inventory',
            'batches':sorted(STATES.values(),key=lambda x:x['id'])}


def update(batch_id,**values):
    with LOCK:
        STATES.setdefault(batch_id,{'id':batch_id}).update(values)
        STATES[batch_id]['updated_unix']=time.time()
        write(META/'status'/(batch_id+'.json'),STATES[batch_id])
        write(META/'summary.json',summary())


def worker(slot,todo):
    while not PAUSED.is_set():
        try:
            stub=todo.get_nowait()
        except queue.Empty:
            return
        batch_id=stub['id']
        b=json.loads((META/'batches'/(batch_id+'.json')).read_text(encoding='utf-8'))
        try:
            update(batch_id,status='packing',category=b['category'],campaign=b['campaign'],run=b['run'],source_bytes=b['source_bytes'])
            remote('submit',str(slot),payload=b)
            while True:
                packed=remote('poll',SESSION,batch_id)
                if packed['status']!='packing':
                    break
                time.sleep(3)
            write(META/'packed'/(batch_id+'.json'),packed)
            if packed['status']=='paused':
                PAUSED.set()
            if packed['status']!='packed':
                update(batch_id,status=packed['status'],detail=packed)
                continue
            incoming=ARCHIVE/'98_incoming'/(b['archive_name']+'.partial')
            final=ARCHIVE/b['local_relative_path']
            if incoming.exists() or final.exists():
                raise RuntimeError('existing local name retained; no overwrite or mixing partial archives')
            update(batch_id,status='downloading',server_bytes=packed['server_bytes'],incoming_path=str(incoming))
            start=time.time()
            with (META/(batch_id+'.transfer.log')).open('wb') as log:
                subprocess.run([SCP,'-q',*OPTIONS,'autodl-d57:'+packed['server_archive_path'],str(incoming)],stdout=log,stderr=log,check=True)
            local_bytes=incoming.stat().st_size
            if local_bytes!=packed['server_bytes']:
                raise RuntimeError('download byte count differs; source retained')
            seconds=time.time()-start
            update(batch_id,status='reading_local_archive',local_bytes=local_bytes,transfer_seconds=seconds,
                   transfer_MiB_s=local_bytes/seconds/1024**2)
            with (META/(batch_id+'.read.log')).open('wb') as log:
                subprocess.run([TAR,'-xOf',str(incoming)],stdout=subprocess.DEVNULL,stderr=log,check=True)
            final.parent.mkdir(parents=True,exist_ok=True)
            incoming.rename(final)
            ack={'local_archive_path':str(final),'local_bytes':local_bytes,'local_read_status':'complete',
                 'read_tool':'Windows bsdtar -xOf; entire decompressed stream consumed, exit 0',
                 'confirmed_unix':time.time()}
            write(META/'confirmations'/(batch_id+'.json'),ack)
            update(batch_id,status='local_verified_deleting',local_archive_path=str(final),local_read_status='complete')
            receipt=remote('finalize',SESSION,batch_id,payload=ack)
            write(META/'receipts'/(batch_id+'.json'),receipt)
            update(batch_id,status='complete',exported_source_bytes=sum(e['size_bytes'] for e in packed['entries']),
                   deleted_bytes=receipt['deleted_bytes'],kept_bytes=receipt['kept_bytes'],
                   deleted_files=len(receipt['deleted']),kept_files=len(receipt['kept']),skipped=packed['skipped'],
                   server_free_bytes=receipt['disk_after']['free'],server_temp_removed=receipt['server_temp_removed'],
                   completed_unix=receipt['completed_unix'])
        except Exception as exc:
            update(batch_id,status='incomplete',error=repr(exc))
            print(json.dumps({'batch':batch_id,'error':repr(exc),'source':'retained unless a deletion receipt records otherwise'}),flush=True)
        else:
            print(json.dumps({'batch':batch_id,'complete':True,'archive_bytes':local_bytes,'deleted_bytes':receipt['deleted_bytes'],
                              'MiB_s':round(local_bytes/seconds/1024**2,2)}),flush=True)
        finally:
            todo.task_done()


def publish(label):
    s=json.loads((META/'summary.json').read_text(encoding='utf-8'))
    dest=REPO/'results/storage_export/20261111'
    dest.mkdir(parents=True,exist_ok=True)
    write(dest/'status.json',s)
    lines=['# Supermimic H-drive export, 2026-11-11','',
           f"Status: {s['status']}. Snapshot: {s['updated_at']}.",'',
           'This is the user-authorized one-time migration, not the normal experiment publication workflow.',
           'Local destination: `H:\\Supermimic`. Full frozen file manifests, confirmations and exact deletion receipts remain in `00_inventory\\20261111_1144`.',
           'Four concurrent transfer sequences, no bandwidth cap; up to two zstd threads per compressed batch. Most NPZ/checkpoint batches use uncompressed tar. Existing archives are transferred directly.',
           'The live initial process check found no Supermimic computation/publication and no P12 worktree. P12 remains reserved, and every batch rechecks live processes/config paths before source deletion.',
           'All parent/final/milestone checkpoints (including P6 B33000, P11 endpoints, P10 control27000 and P9 LAFAN60000), processed backing data, fixed P10/P11 evidence, source, environments, assets and Git/stash remain on D57.',
           '',f"Completed batches: {s['completed_batches']}/{s['total_batches']}.",
           f"Fully read local archive bytes: {s['verified_archive_bytes']}.",
           f"Exported original file bytes: {s['exported_source_bytes']}.",
           f"Actual unlinked source bytes: {s['server_deleted_bytes']} (logical file sizes; disk free is reported separately).",
           f"Exported and kept source bytes: {s['exported_kept_source_bytes']}.",
           f"Last observed server free bytes: {s['server_last_observed_free_bytes']}.",'',
           'Every deletion follows successful download, identical archive byte counts, full local decompressed read and a fresh file-identity/dependency check. No hashes, simulations, restore tests, package installation, GPU use, directory deletion or Release upload.',
           'All H-drive archives remain until the user decides to remove them. Failed/changed/active files remain on the server; details are in status.json and the local receipts.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    def git(*args):
        subprocess.run([GIT,'-C',str(REPO),*args],stdout=sys.stdout,stderr=sys.stderr,check=True)
    git('add','--','scripts/storage_export_h_local.py','scripts/storage_export_h_remote.py','results/storage_export/20261111')
    changed=subprocess.run([GIT,'-C',str(REPO),'diff','--cached','--quiet']).returncode
    if changed:
        git('commit','-m',label)
        git('fetch','origin','main')
        git('rebase','origin/main')
        git('-c','http.postBuffer=67108864','push','origin','HEAD:main')
    commit=subprocess.check_output([GIT,'-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    write(META/'publication.json',{'commit':commit,'label':label,'published_unix':time.time()})


def run():
    global PLAN
    # Open the log in Windows itself; WSL's inherited stdout bridge can expire.
    controller_log=(META/'controller.log').open('a',encoding='utf-8',buffering=1)
    sys.stdout=controller_log
    sys.stderr=controller_log
    PLAN=json.loads((META/'plan.json').read_text(encoding='utf-8'))
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x8000)
    for p in (META/'status').glob('*.json'):
        s=json.loads(p.read_text(encoding='utf-8'));STATES[s['id']]=s
    todo=queue.Queue()
    for b in PLAN['batches']:
        if b['id'] not in STATES:
            todo.put(b)
    with LOCK:
        write(META/'summary.json',summary())
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures=[pool.submit(worker,i,todo) for i in range(1,WORKERS+1)]
        for f in futures:
            f.result()
    with LOCK:
        s=summary()
        s['status']='paused_training_slowdown' if PAUSED.is_set() else 'completed' if s['completed_batches']==s['total_batches'] else 'completed_with_remaining'
        write(META/'summary.json',s)
    remote('finish',SESSION,payload={'status':s['status'],'finished_unix':time.time()})
    publish('Record completed H-drive export and exact deletion totals')
    print(json.dumps({k:v for k,v in s.items() if k!='batches'}),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='prepare':
        prepare()
    elif sys.argv[1]=='run':
        run()
    elif sys.argv[1]=='publish':
        publish('Start authorized H-drive export with verified first batches')
