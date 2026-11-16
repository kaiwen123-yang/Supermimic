"""One CPU-only read of published examples and author/data provenance."""
import argparse
import csv
import json
import subprocess
from pathlib import Path
from common import CAMPAIGN, CODE_ROOT, PROTOCOL_PATH, now, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL_PATH.read_text())
    plan = protocol['fixed_quality_timeseries']
    selected = {m['source_clip_id'] for m in plan['members']}
    historical, inspected = {}, {}
    for name, relative in plan['historical_score_roots'].items():
        root = CODE_ROOT / relative
        index = json.loads((root / 'per_clip_index.json').read_text())
        rows = []
        for part in sorted({i // index['rows_per_part'] for i in selected}):
            path = root / index['parts'][part]
            with path.open() as stream:
                rows.extend(row for row in csv.DictReader(stream) if int(row['source_clip_id']) in selected)
        historical[name] = {'source': relative, 'rows': rows, 'read_scope': 'only the four selected CSV parts; four retained rows'}
        windows = root / 'failure_windows'
        inspected[name] = {'directory': str(windows),
            'saved_failure_window_index': json.loads((windows / 'index.json').read_text()) if (windows / 'index.json').exists() else None,
            'full_selected_quality_trajectories': 'Not supplied in these published result directories; no old checkpoint replay performed.'}
    manifest_path = args.workspace / 'data/bones130394_official_packed/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    clips = manifest.pop('clips')
    members = [c for c in clips if c['source_clip_id'] in selected]
    official = protocol['source']['official_commit']
    tree = json.loads(subprocess.check_output(['gh', 'api', f'repos/HybridRobotics/supermimic/git/trees/{official}?recursive=1'], text=True))
    releases = json.loads(subprocess.check_output(['gh', 'api', 'repos/HybridRobotics/supermimic/releases'], text=True))
    author = {'checked_at': now(), 'official_commit': official,
        'tree_paths': [r['path'] for r in tree['tree']], 'tree_truncated': tree.get('truncated', False),
        'releases': [{'tag': r['tag_name'], 'assets': [a['name'] for a in r['assets']]} for r in releases],
        'exact_author_129514_membership_list_recovered': False,
        'exact_paper_run_scheduler_bundle_recovered': False,
        'scope': 'Pinned official source tree and public releases, plus repository O5 review. No demo checkpoint substituted.',
        'selected_O6_clock': 'Public runner outer collection loop, explicitly selected; exact paper-run mapping remains unconfirmed.',
        'wm_semantics': 'Official horizon8 stores8 states and supervises7 transitions; unchanged.',
        'source_review': 'docs/O5_REVIEW_20261116.md sections8/10',
        'source_files': ['src/supermimic/runners/supermimic_runner.py',
                         'src/supermimic/learners/learner_utils.py', 'src/supermimic/learners/wm_learner.py']}
    write_json(args.workspace / 'results' / CAMPAIGN / 'existing_evidence_read.json', {
        'at': now(), 'mode': 'CPU read-only sources; no model, checkpoint, physical rollout or RNG calls',
        'historical_examples': historical, 'historical_trajectory_scope': inspected,
        'packed_manifest_path': str(manifest_path), 'packed_provenance': manifest,
        'observed_clip_count': len(clips), 'selected_packed_members': members,
        'author_evidence': author, 'data_modified': False,
        'membership_gap': 'Project130394 vs paper129514 remains unresolved without the author member list; no deletion or policy-based filtering.',
        'O6_examples_frozen': True})
    print('O6_EXISTING_EVIDENCE_READ_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
