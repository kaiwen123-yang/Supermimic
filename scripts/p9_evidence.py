"""Export exactly the two prescribed already-recorded successful physical windows."""
from pathlib import Path
from p9_results import ROOT, PROTOCOL, read, write
from p7_evidence import export_physical_window


def export():
    p = read(PROTOCOL)
    output = ROOT / "results" / p["campaign"] / "evidence"
    rows = []
    for target in p["evidence"]["existing_success_windows"]:
        run = ROOT.parent / "supermimic-p8-stability-scale/outputs/runs" / target["run"]
        first,last = target["reference_frames"]
        rows.append(export_physical_window(run,target["iteration"],target["motion"],first,last,output))
    failures = "results/20261106-p8-stability-scale-s0/jobs/lafan_h32/final_failure_windows"
    manifest = {"status":"prepared", "windows":rows, "matching_failure_windows_reused":failures,
        "source":"existing formal evaluation trajectories; no new inference or physics",
        "pairing":"Same reference event, different checkpoint policies. H16 success in dance does not imply overall H16 superiority."}
    write(output/"manifest.json",manifest)
    return manifest


if __name__ == "__main__":
    export()
