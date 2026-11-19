"""Run the explicitly authorized AutoCAD fixture end to end in a new local directory."""
import argparse
import json
from pathlib import Path

from omnicad.cli import main as cli


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_directory",type=Path)
    options=parser.parse_args()
    folder=options.new_directory.resolve()
    folder.mkdir()
    job=Path(__file__).resolve().parents[1]/"examples"/"bracket.json"
    seed=folder/"seed.dxf"
    if cli(["build",str(job),str(seed)])!=0:
        return 1
    publication=folder/"publication"
    status=cli(["publish",str(job),str(seed),str(publication)])
    # The omission of an independent visual attestation is an expected QA hold.
    if status!=2:
        return 1
    report=json.loads((publication/"report.json").read_text(encoding="utf-8"))
    ready=report["autocad"]["editable_reopened"] and report["qa"]["entity_types"]["DIMENSION"]==1 and (
        report["trace"]["checks_clear"] and report["paper"]["paper_and_crop_ok"]
        and report["trace"]["blocking_requirements"]==["Q02"])
    return 0 if ready else 1


if __name__=="__main__":
    raise SystemExit(main())
