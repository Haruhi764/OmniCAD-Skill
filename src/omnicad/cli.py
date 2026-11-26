"""Command line interface; all operations are local and explicit."""
from argparse import ArgumentParser
import json
from pathlib import Path
import subprocess
import sys
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

import ezdxf

from . import acceptance, capabilities, exchange, supervisor, dxf, intake, intent, mechanical, oqa, pdfquality, records
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
    q.add_argument("--verify-native",action="store_true",help="Edit and restore representative native objects and independently replot")
    def native_options(q):
        q.add_argument("--backend", choices=capabilities.BACKENDS, default="auto")
        q.add_argument("--product", choices=("auto","autocad","lt"), default="auto")
        q.add_argument("--experimental-lt", action="store_true", help="Opt in to the manual LT exchange workflow")
        q.add_argument("--year", type=int)
        q.add_argument("--native-state", type=Path)
        q.add_argument("--native-timeout", type=int, default=180)
        q.add_argument("--native-budget", type=int)
    native_options(q)
    q=s.add_parser("read-dwg",help="Export a trusted local DWG copy via AutoCAD")
    q.add_argument("drawing",type=Path)
    q.add_argument("new_directory",type=Path)
    native_options(q)
    q=s.add_parser("capabilities",help="Detect installed products and choose a supported backend")
    q.add_argument("--product", choices=("auto","autocad","lt"), default="auto")
    q.add_argument("--year", type=int)
    q.add_argument("--backend", choices=capabilities.BACKENDS, default="auto")
    q.add_argument("--probe-file",type=Path)
    q=s.add_parser("verify-exchange",help="Check returned DXF/DWG/PDF without claiming native acceptance")
    q.add_argument("folder",type=Path)
    q=s.add_parser("native-reset",help="Archive the shared circuit after manual host review")
    q.add_argument("--confirm-host-reviewed",action="store_true")
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
    q=s.add_parser("mechanical",help="Compile an explicit shaft or flange recipe into a reviewed job")
    q.add_argument("recipe",type=Path)
    q.add_argument("output_job",type=Path)
    q=s.add_parser("oqa",help="Run discipline-aware engineering QA")
    q.add_argument("drawing",type=Path,help="DXF or AutoCAD readback")
    q.add_argument("--mode",choices=oqa.MODES,default="light")
    q.add_argument("--domain",choices=oqa.DOMAINS,default="general")
    for flag in ("job","contract","pdf","publication","metrics","report"):
        q.add_argument("--"+flag,type=Path)
    q.add_argument("--expect-text",action="append",default=[])
    q=s.add_parser("accept",help="Strict typed hard gates and evidence-bound soft score")
    q.add_argument("drawing",type=Path)
    q.add_argument("--domain",choices=acceptance.CRITICAL_FIELDS,required=True)
    q.add_argument("--contract",type=Path,required=True)
    q.add_argument("--target",choices=("dxf","dwg-pdf"),default="dwg-pdf")
    for flag in ("job","pdf","publication","review","report"):
        q.add_argument("--"+flag,type=Path)
    q=s.add_parser("intent",help="Inventory intent and unresolved scope before editing")
    q.add_argument("request",type=Path,help="UTF-8 request text")
    q.add_argument("--reference",action="append",default=[])
    q.add_argument("--target")
    q.add_argument("--region")
    for flag in ("preserve","constraint","swap"):
        q.add_argument("--"+flag,action="append",default=[])
    q.add_argument("--report",type=Path)
    q=s.add_parser("diff",help="Compare two DXFs from the same drawing lineage")
    q.add_argument("before",type=Path)
    q.add_argument("after",type=Path)
    q.add_argument("--allowlist",type=Path,help="JSON list of reviewed object IDs")
    q.add_argument("--report",type=Path)
    q=s.add_parser("repair-pdf",help="Check and repair the supported AutoCAD PageMode defect to a new file")
    q.add_argument("source",type=Path)
    q.add_argument("output",type=Path)
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
    if command=="capabilities":
        hosts=capabilities.installed_windows()
        host,backend=capabilities.choose(hosts,a.backend,a.product,a.year)
        probe=capabilities.probe_session_file(a.probe_file).report() if a.probe_file else None
        return {"installed":[h.report() for h in hosts],"selected":host.report(),
                "backend":backend,"session_probe":probe,"experimental_opt_in_required":backend=="exchange"},0
    if command=="verify-exchange":
        result=exchange.verify(a.folder)
        return result,2  # Native verification is intentionally pending.
    if command=="native-reset":
        supervisor.reset_circuit(a.confirm_host_reviewed)
        return {"reviewed_circuit_archived":True},0
    if command=="accept":
        result=acceptance.evaluate(a.drawing,a.domain,json_input(a.contract),
            load(a.job) if a.job else None,a.pdf,json_input(a.publication) if a.publication else None,
            json_input(a.review) if a.review else None,a.target)
        if a.report:
            records.write_json(a.report,result)
        return result,0 if result["verdict"]=="passed" else 2
    if command=="mechanical":
        job=mechanical.compile_recipe(json_input(a.recipe))
        records.write_json(a.output_job,job)
        return {"job":str(a.output_job),"entities":len(job["entities"])},0
    if command=="oqa":
        result=oqa.inspect(a.drawing,a.mode,a.domain,load(a.job) if a.job else None,
                           json_input(a.contract) if a.contract else None,a.pdf,
                           json_input(a.publication) if a.publication else None,a.expect_text,
                           json_input(a.metrics) if a.metrics else None)
        if a.report:
            records.write_json(a.report,result)
        return result,2 if result["coverage"].get("failed") else 0
    if command=="intent":
        result=intent.analyze(a.request.read_text(encoding="utf-8-sig"),a.reference,a.target,a.region,
                              a.preserve,a.constraint,a.swap)
        if a.report:
            records.write_json(a.report,result)
        return result,2 if result["missing"] else 0
    if command=="diff":
        allowed=json_input(a.allowlist) if a.allowlist else None
        if allowed is not None and (not isinstance(allowed,list) or not all(isinstance(v,str) for v in allowed)):
            raise ValueError("The allowlist must be a JSON list of entity identities")
        result=intent.compare_drawings(ezdxf.readfile(a.before),ezdxf.readfile(a.after),allowed)
        result["sha256"]={"before":records.digest(a.before),"after":records.digest(a.after)}
        if a.report:
            records.write_json(a.report,result)
        return result,2 if result["outside_allowlist"] else 0
    if command=="repair-pdf":
        if a.source.resolve()==a.output.resolve() or a.output.exists():
            raise ValueError("Use a new PDF output path")
        result=pdfquality.repair_plot(a.source,a.output)
        if result["state"]=="unchanged":
            records.copy_new(a.source,a.output)
        return result|{"output":str(a.output)},0
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
        host,backend=capabilities.publication_route(capabilities.installed_windows(),
            a.backend,a.product,a.year,a.experimental_lt)
        if backend!="com":
            return {"status":"manual_exchange_required","instruction":
                    "Open a DWG copy in CAD and Save As a distinct DXF; then run OQA."},2
        output,execution=supervisor.execute({"operation":"readback","source":str(a.drawing),
            "destination":str(a.new_directory),"year":host.year},a.native_state,a.native_timeout,a.native_budget)
        return output|{"execution":execution},0
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
        host,backend=capabilities.publication_route(capabilities.installed_windows(),
            a.backend,a.product,a.year,a.experimental_lt)
        if backend=="exchange":
            return exchange.prepare(job,a.drawing,a.new_directory,host),2
        if "sheet" in job:
            try:
                import pypdf  # required for independent PDF validation
            except ImportError as e:
                raise ValueError("PDF publication verification requires the [intake] extra") from e
        output,execution=supervisor.execute({"operation":"publish","source":str(a.drawing),
            "destination":str(a.new_directory),"year":host.year,"sheet":job.get("sheet"),
            "job_sha256":records.digest(a.job),"verify_native":a.verify_native},
            a.native_state,a.native_timeout,a.native_budget)
        result=report(job,Path(output["readback"]),Path(output["pdf"]) if output["pdf"] else None,dwg=Path(output["dwg"]))
        result["autocad"]=output
        result["execution"]=execution
        report_path=a.new_directory/"report.json"
        if not report_path.exists():
            records.write_json(report_path,result)
        elif not execution["reused"]:
            raise ValueError("Unexpected existing publication report")
        else:
            prior=json_input(report_path)
            if any(prior.get(k)!=result[k] for k in ("qa","trace","paper","autocad")):
                raise ValueError("Existing publication report does not match the verified checkpoint")
        return result,0 if result["trace"]["release_ready_by_manifest"] else 2
    raise ValueError(command)


def main(argv=None):
    a=parser().parse_args(argv)
    try:
        result,status=run(a)
    except (ValueError,KeyError,TypeError,RuntimeError,OSError,ImportError,ezdxf.DXFError,subprocess.SubprocessError,BadZipFile,ParseError) as e:
        print(f"omnicad: {e}",file=sys.stderr)
        return 1
    # ASCII survives legacy Windows consoles. Saved UTF-8 reports retain all original text.
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return status
