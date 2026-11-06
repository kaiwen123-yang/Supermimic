"""Publish actual BONES manifest/filter results under the existing P8 lock."""
import argparse
import fcntl
from pathlib import Path
from p8_results import ROOT, PROTOCOL, read, write, refresh, index_update
from publish_checkpoint import push_results


def main(stage):
    protocol = read(PROTOCOL)
    result = ROOT / "results" / protocol["campaign"]
    with Path(protocol["execution"]["publication_lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        summary_path = result / "jobs/bones40_transfer_h32/summary.json"
        summary = read(summary_path)
        summary.update(data_status=stage, data_manifest="results/"+protocol["campaign"]+"/bones_data/subset_manifest.json")
        if stage == "starting":
            summary["status"] = "starting"
        write(summary_path, summary)
        campaign = refresh()
        commit = push_results("p8-bones-data-"+stage, [result.relative_to(ROOT), Path("configs/bones_p8_preprocessing.json")],
            lambda index: index_update(index, campaign))
        print("P8_BONES_DATA_PUBLISHED", stage, commit, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("full", "starting"))
    main(parser.parse_args().stage)
