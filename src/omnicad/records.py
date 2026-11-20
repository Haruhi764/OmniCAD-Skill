"""Artifact fingerprints, requirement evidence, change history and recovery."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil

from .manifest import nonempty, point, validate


def digest(path):
    h=sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda:source.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, payload):
    with Path(path).open("x",encoding="utf-8",newline="\n") as out:
        json.dump(payload,out,ensure_ascii=False,indent=2)
        out.write("\n")


def clean(audit):
    flags=("entity_errors","unexpected_ids","untagged_model_entities","layers_bad","sheet_errors",
           "duplicates","possible_text_overlaps","audit_errors","audit_fixes")
    return audit["units_mm"] and not any(audit[k] for k in flags) and not audit.get("internal_notes")


def trace(job,audit,artifacts,reviews=None):
    reviewed=reviews or {}
    rows=[]
    for req in job["requirements"]:
        key=req["id"]
        ids=req.get("entities",[])
        scope=req["scope"]
        bad=[i for i in ids if i in audit["entity_errors"]]
        review=reviewed.get(key,{})
        visual=bool(review.get("note","").strip() and review.get("sha256")==artifacts)
        if scope in {"excluded","undecided"}:
            state=scope
        elif bad:
            state="failed"
        elif req.get("visual",False) or not ids:
            state="verified" if visual else "review_needed"
        else:
            state="verified"
        rows.append({"id":key,"statement":req["statement"],"source":req["source"],"scope":scope,
                     "decision":req.get("decision"),"state":state,"entities":ids,"issues":bad,
                     "visual_evidence":review.get("note") if visual else None})
    blocking=[r["id"] for r in rows if r["scope"] in {"required","undecided"} and r["state"]!="verified"]
    missing=sorted(set(job.get("required_formats",["dxf"]))-artifacts.keys())
    valid=clean(audit) and not blocking and not missing
    return {"drawing_id":job["drawing_id"],"artifacts_sha256":artifacts,"requirements":rows,
            "blocking_requirements":blocking,"missing_formats":missing,"checks_clear":clean(audit),"release_ready_by_manifest":valid}


def revise(job,doc,drawing,changes,outdir):
    from .dxf import audit, indexed, save_new
    from .intent import snapshot
    from ezdxf.math import Matrix44

    if digest(drawing)!=changes["input_sha256"]:
        raise ValueError("Revision has a stale baseline fingerprint")
    indexed_entities=indexed(doc.modelspace())
    expected=deepcopy(job)
    specs={e["id"]:e for e in expected["entities"]}
    if not changes["operations"]:
        raise ValueError("Revision has no operations")
    before=snapshot(doc)
    chosen=set()
    if not clean(audit(doc,job)):
        raise ValueError("Baseline failed preflight; revisions require a matching OmniCAD drawing")
    for operation in changes["operations"]:
        key=operation["id"]
        why=nonempty(operation["reason"],f"{key}.reason")
        if key in chosen or key not in specs or key not in indexed_entities:
            raise ValueError(f"{key}: stale or duplicate revision target")
        chosen.add(key)
        s,e=specs[key],indexed_entities[key]
        kind=operation["op"]
        if kind=="move" and s["type"] in {"line","circle","arc","polyline","text"}:
            dx,dy=point(operation["delta"],"delta")
            # Dimension anchors are separate specifications; changes that would orphan
            # their geometry need a new manifest and a reviewed redraw of those dimensions.
            if any(x["type"]=="linear_dimension" for x in expected["entities"]) and s["type"]!="text":
                raise ValueError("Moving geometry in a dimensioned drawing requires explicit dimension remapping")
            e.transform(Matrix44.translate(dx,dy,0))
            for name in ("start","end","center","insert"):
                if name in s:
                    x,y=s[name]
                    s[name]=[x+dx,y+dy]
            if "points" in s:
                s["points"]=[[x+dx,y+dy] for x,y in s["points"]]
        elif kind=="set_text" and s["type"]=="text":
            s["text"]=e.dxf.text=nonempty(operation["value"],f"{key}.value")
        else:
            raise ValueError(f"{key}: unsupported operation for {s['type']}")
        s["source"]+=" | revision: "+why
    validate(expected)
    report=audit(doc,expected)
    if not clean(report):
        raise ValueError(f"Revision failed QA: {report}")
    after=snapshot(doc)
    allowed={"Model:"+key for key in chosen}
    changed={key for key in before.keys()|after.keys() if before.get(key)!=after.get(key)}
    if changed-allowed:
        raise ValueError(f"Revision changed entities outside scope: {sorted(changed-allowed)}")
    outdir.mkdir()  # must be new; no write to source directory contents
    backup=outdir/"baseline.dxf"
    copy_new(drawing,backup)
    assert digest(backup)==changes["input_sha256"], "Source changed during revision"
    save_new(doc,outdir/"revised.dxf")
    write_json(outdir/"job.json",expected)
    write_json(outdir/"revision.json",{"changes":changes,"baseline_sha256":digest(backup),
                                     "revised_sha256":digest(outdir/"revised.dxf"),"scope_diff":sorted(changed),"qa":report})


def copy_new(source, destination):
    with Path(source).open("rb") as src,Path(destination).open("xb") as dst:
        shutil.copyfileobj(src,dst)


def restore(backup, fingerprint, output):
    if digest(backup)!=fingerprint:
        raise ValueError("Backup fingerprint mismatch")
    copy_new(backup,output)


def lesson(path, category, issue, cause, resolution, evidence):
    fields={k:nonempty(v,k) for k,v in locals().copy().items() if k!="path"}
    with path.open("a",encoding="utf-8",newline="\n") as out:
        out.write(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),**fields},ensure_ascii=False)+"\n")
