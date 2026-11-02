"""Finish only the retained P2 publication files after the completed training pair."""
from pathlib import Path
import fcntl,json,os,re,shutil,time
from publish_checkpoint import ROOT,REPO,release_by_tag,upload_files,push_results
TAG='20261101-goal-feedback-s0'
RELEASE='sm-'+TAG+'-final'
RESULT=ROOT/'results'/TAG
STAGE=ROOT/'outputs/campaigns'/TAG
SP=RESULT/'summary.json'


def write(s):
    SP.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')


def update_index(s):
    def update(index):
        index['campaigns'][TAG].update(status=s['status'],summary=str(SP.relative_to(ROOT)),release_url=s['release_url'])
        index['next_stage']['status']=s['status']
    return update


def allowed(p):
    r=str(p.relative_to(ROOT))
    roots=[f'outputs/runs/{TAG}-{mode}/' for mode in ('robot_root','reference_heading')]
    roots += [f'outputs/campaigns/{TAG}/',f'outputs/preparation/{TAG}/']
    return (any(r.startswith(x) for x in roots) or
        bool(re.fullmatch(r'outputs/publications/sm-'+TAG+r'-(robot_root|reference_heading)-i\d{7}/.+',r)) or
        bool(re.fullmatch(r'outputs/publications/'+TAG+r'-(robot_root|reference_heading)-i\d+\.log',r)) or
        bool(re.fullmatch(r'outputs/campaigns/'+TAG+r'-(robot_root|reference_heading)\.train\.log',r)))


def main():
    with (ROOT/'work/p2-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        s=json.loads(SP.read_text())
        archive=STAGE/'original_records.tar'
        parts=[]
        # Split the one failed 2.49 GB tar stream. No re-packing of prior artifacts.
        with archive.open('rb') as src:
            for number in range((archive.stat().st_size+1024**3-1)//1024**3):
                target=STAGE/f'original_records.tar.part{number+1:03d}'
                remaining=min(1024**3,archive.stat().st_size-number*1024**3)
                with target.open('wb') as out:
                    while remaining:
                        block=src.read(min(8*1024**2,remaining));out.write(block);remaining-=len(block)
                parts.append(target)
        paths=[ROOT/r['path'] for r in s['unpublished'] if r['path']!=str(archive.relative_to(ROOT))]+parts
        s['status']='publication_completion_running'
        s['publication_completion']={'started_unix':time.time(),'original_archive_bytes':archive.stat().st_size,
            'parts':[{'name':p.name,'bytes':p.stat().st_size} for p in parts],
            'scope':'Only prior incomplete assets and split original_records.tar; no training/evaluation rerun'}
        write(s)
        push_results('p2-completion-start',[Path('scripts/complete_goal_publication.py'),SP.relative_to(ROOT)],update_index(s))
        release=release_by_tag(RELEASE,431061734)
        uploaded,errors=upload_files(RELEASE,paths,release['id'])
        # One final asset listing also resolves uploads whose confirmation request timed out.
        remote={a['name']:a for a in release_by_tag(RELEASE,release['id'])['assets']}
        missing=[];confirmed=[]
        for p in paths:
            a=remote.get(p.name)
            if a and a['state']=='uploaded' and a['size']==p.stat().st_size:
                confirmed.append({'path':str(p.relative_to(ROOT)),'name':p.name,'bytes':p.stat().st_size,
                    'state':'uploaded','url':a['browser_download_url'],'network':'AutoDL official academic acceleration'})
            else:
                missing.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
                    'error':next((e['error'] for e in errors if e['path']==str(p.relative_to(ROOT))),'not fully uploaded')})
        saved={a['name']:a for a in s['assets']}
        old_urls={}
        for name,a in saved.items():
            r=remote.get(name)
            if r and r['state']=='uploaded' and r['size']==a['bytes']:
                old_urls[a['url']]=r['browser_download_url'];a['url']=r['browser_download_url']
        saved.update({a['name']:a for a in confirmed})
        s['assets']=list(saved.values());s['unpublished']=missing
        inventory=s['upload_inventory']
        for a in confirmed:inventory[a['path']]={'url':a['url'],'bytes':a['bytes']}
        all_parts=all(p.name in saved for p in parts)
        part_assets=[saved[p.name] for p in parts if p.name in saved]
        for record in inventory.values():
            if record.get('url') in old_urls:record['url']=old_urls[record['url']]
            pending=record.get('pending_asset')
            if pending=='original_records.tar' and all_parts:
                record.update(url=s['release_url'],archive_parts=[{'name':a['name'],'url':a['url'],'bytes':a['bytes']} for a in part_assets])
            elif pending in saved:
                record['url']=saved[pending]['url']
        if all_parts:
            inventory[str(archive.relative_to(ROOT))]={'url':s['release_url'],'bytes':archive.stat().st_size,
                'archive_parts':[{'name':a['name'],'url':a['url'],'bytes':a['bytes']} for a in part_assets]}
        s['publication_completion'].update(assets_confirmed=len(confirmed),remaining_files=len(missing),
            archive_parts=[{'name':a['name'],'url':a['url'],'bytes':a['bytes']} for a in part_assets])
        s['status']='uploaded' if not missing else 'upload_incomplete'
        write(s)
        s['publication_completion']['git_commit_before_cleanup']=push_results('p2-completion-uploaded',[SP.relative_to(ROOT)],update_index(s))
        deleted=[];released=0
        for relative,record in inventory.items():
            p=ROOT/relative
            if not allowed(p) or not p.is_file() or p.is_symlink() or not record.get('url'):continue
            if not p.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Cleanup target outside project')
            st=p.stat()
            if st.st_size!=record['bytes']:continue
            if st.st_nlink==1:released+=st.st_blocks*512
            p.unlink();deleted.append({'path':relative,'bytes':st.st_size})
        s['cleanup']['deleted'].extend(deleted);s['cleanup']['released_bytes']+=released
        s['publication_completion'].update(deleted_files=len(deleted),released_bytes=released,completed_unix=time.time())
        s['status']='completed' if not missing else 'completed_with_unpublished_files'
        write(s)
        protocol=ROOT/'configs/next_stage_correction_protocol.json'
        d=json.loads(protocol.read_text());d['status']=s['status'];protocol.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
        push_results('p2-completion-cleanup',[SP.relative_to(ROOT),protocol.relative_to(ROOT)],update_index(s))
        print('PUBLICATION_COMPLETION',json.dumps({'status':s['status'],'unpublished':missing,'additional_released_bytes':released,'total_released_bytes':s['cleanup']['released_bytes']}),flush=True)

if __name__=='__main__':main()
