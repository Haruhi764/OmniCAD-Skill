"""Command line interface; all operations are local and explicit."""
from argparse import ArgumentParser
import json
from pathlib import Path
import subprocess
import sys
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

import ezdxf

from . import dxf, intake, records
from .backend import AutoCAD
from .formal import internal_notes
from .manifest import load
from .paper import check_pdf, preview


def parser():
    p=ArgumentParser(prog="omnicad")
    s=p.add_subparsers(dest="command",required=True)
    q=s.add_parser("intake",help="Inventory an input with a local content-addressed cache")
    q.add_argument("source",type=Path)
    q.add_argument("--cache",type=Path,required=True)
    q.add_argument("--full",action="store_true",help="Emit extracted data explicitly")
    q=s.add_parser("build",help="Create a new native-entity DXF from an explicit manifest")
    q.add_argument("job",type=Path)
    q.add_argument("output",type=Path)
    q=s.add_parser("audit",help="Compare a DXF with its manifest and report requirement coverage")
    q.add_argument("job",type=Path)
    q.add_argument("drawing",type=Path)
    q.add_argument("--pdf",type=Path)
    q.add_argument("--publication",type=Path,help="Use a matching report.json emitted by publish")
    q.add_argument("--review",type=Path)
    q.add_argument("--report",type=Path)
    q=s.add_parser("formal-check",help="Flag internal notes in a legacy or native readback DXF")
    q.add_argument("drawing",type=Path)
    q.add_argument("--report",type=Path)
    q=s.add_parser("publish",help="Use installed AutoCAD to save DWG, reopen, plot and verify")
    q.add_argument("job",type=Path)
    q.add_argument("drawing",type=Path)
    q.add_argument("new_directory",type=Path)
    q=s.add_parser("read-dwg",help="Export a trusted local DWG copy via AutoCAD")
    q.add_argument("drawing",type=Path)
    q.add_argument("new_directory",type=Path)
    q=s.add_parser("preview",help="Produce a full or cropped Poppler raster for visual QA")
    q.add_argument("pdf",type=Path)
    q.add_argument("png",type=Path)
    q.add_argument("--region",type=int,nargs=4,metavar=("X","Y","W","H"))
    q.add_argument("--dpi",type=int,default=120)
    q.add_argument("--page",type=int,default=1)
    q=s.add_parser("revise",help="Write a targeted reversible DXF revision in a new directory")
    q.add_argument("job",type=Path)
    q.add_argument("drawing",type=Path)
    q.add_argument("changes",type=Path)
    q.add_argument("new_directory",type=Path)
    q=s.add_parser("restore",help="Restore a verified backup to a new output path")
    q.add_argument("backup",type=Path)
    q.add_argument("sha256")
    q.add_argument("output",type=Path)
    q=s.add_parser("lesson",help="Append an evidence-backed local closeout record")
    q.add_argument("log",type=Path)
    for key in ("category","issue","cause","resolution","evidence"):
        q.add_argument("--"+key,required=True)
    return p


def json_input(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def report(job,drawing,pdf=None,review=None,dwg=None):
    a=dxf.audit(ezdxf.readfile(drawing),job)
    paths={k:records.digest(p) for k,p in {"dxf":drawing,"pdf":pdf,"dwg":dwg}.items() if p}
    state=records.trace(job,a,paths,json_input(review) if review else None)
    paper=check_pdf(pdf,job) if pdf else None
    if paper and not paper["paper_and_crop_ok"]:
        state["release_ready_by_manifest"]=False
    return {"qa":a,"trace":state,"paper":paper}


def run(a):
    command=a.command
    if command=="intake":
        content=intake.inspect(a.source,a.cache)
        return (content if a.full else {"cache_hit":content["cache_hit"],"cache_file":content["path"],
                                        "sha256":content["data"]["sha256"]}),0
    if command=="preview":
        preview(a.pdf,a.png,a.region,a.dpi,a.page)
        return {"preview":str(a.png)},0
    if command=="restore":
        records.restore(a.backup,a.sha256,a.output)
        return {"restored":str(a.output)},0
    if command=="lesson":
        records.lesson(a.log,a.category,a.issue,a.cause,a.resolution,a.evidence)
        return {"lesson_log":str(a.log)},0
    if command=="read-dwg":
        if a.drawing.suffix.lower()!=".dwg":
            raise ValueError("read-dwg expects a trusted local DWG")
        return {"readback":str(AutoCAD().readback(a.drawing,a.new_directory))},0
    if command=="formal-check":
        if a.drawing.suffix.lower()!=".dxf":
            raise ValueError("formal-check expects DXF; use read-dwg for trusted DWG inputs")
        fingerprint=records.digest(a.drawing)
        findings=internal_notes(ezdxf.readfile(a.drawing))
        if fingerprint!=records.digest(a.drawing):
            raise ValueError("DXF changed during formal check")
        result={"sha256":fingerprint,"internal_notes":findings}
        if a.report:
            records.write_json(a.report,result)
        return result,2 if findings else 0
    job=load(a.job)
    if command=="build":
        if a.output.suffix.lower()!=".dxf":
            raise ValueError("build writes DXF only")
        doc=dxf.build(job)
        qa=dxf.audit(doc,job)
        if not records.clean(qa):
            return {"qa":qa,"saved":False},2
        dxf.save_new(doc,a.output)
        return {"output":str(a.output),"sha256":records.digest(a.output),"qa":qa},0
    if a.drawing.suffix.lower()!=".dxf":
        raise ValueError("Expected DXF; use read-dwg for trusted DWG inputs")
    if command=="audit":
        dwg=None
        pdf=a.pdf
        if a.publication:
            publication=json_input(a.publication)
            linked=publication["autocad"]
            if not linked["editable_reopened"] or a.drawing.resolve()!=Path(linked["readback"]).resolve():
                raise ValueError("Publication is not for this exact native readback")
            dwg=Path(linked["dwg"])
            expected_pdf=Path(linked["pdf"]) if linked["pdf"] else None
            if pdf and (not expected_pdf or pdf.resolve()!=expected_pdf.resolve()):
                raise ValueError("PDF is not the one in the AutoCAD publication report")
            pdf=expected_pdf
            copies={"dxf":a.drawing,"dwg":dwg,"pdf":pdf}
            if {k:records.digest(p) for k,p in copies.items() if p}!=publication["trace"]["artifacts_sha256"]:
                raise ValueError("Publication artifact fingerprint changed")
        result=report(job,a.drawing,pdf,a.review,dwg=dwg)
        if a.report:
            records.write_json(a.report,result)
        return result,0 if result["trace"]["release_ready_by_manifest"] else 2
    if command=="revise":
        records.revise(job,ezdxf.readfile(a.drawing),a.drawing,json_input(a.changes),a.new_directory)
        return {"revision":str(a.new_directory)},0
    if command=="publish":
        preflight=dxf.audit(ezdxf.readfile(a.drawing),job)
        if not records.clean(preflight):
            return {"qa":preflight,"saved":False},2
        if "sheet" in job:
            try:
                import pypdf  # required for independent PDF validation
            except ImportError as e:
                raise ValueError("PDF publication verification requires the [intake] extra") from e
        output=AutoCAD().publish(a.drawing,a.new_directory,job.get("sheet"))
        result=report(job,Path(output["readback"]),Path(output["pdf"]) if output["pdf"] else None,dwg=Path(output["dwg"]))
        result["autocad"]=output
        records.write_json(a.new_directory/"report.json",result)
        return result,0 if result["trace"]["release_ready_by_manifest"] else 2
    raise ValueError(command)


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        result,status=run(a)
    except (ValueError,KeyError,TypeError,RuntimeError,OSError,ezdxf.DXFError,subprocess.SubprocessError,BadZipFile,ParseError) as e:
        print(f"omnicad: {e}",file=sys.stderr)
        return 1
    # ASCII survives legacy Windows consoles. Saved UTF-8 reports retain all original text.
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return status
