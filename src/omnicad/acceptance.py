"""Strict typed acceptance gates layered above the backward-compatible OQA report."""
import math
import re

import ezdxf

from . import oqa, records

CRITICAL_FIELDS = {
    "architecture": {"walls": {"endpoints","closed"}, "axes": {"endpoints","length"}, "dimensions": {"measurement"}},
    "civil": {"geometry": {"endpoints","closed","length","radius"}, "axes": {"endpoints","length"},
              "elevations": {"text"}},
    "mechanical": {"profile": {"length","radius","endpoints","closed"}, "dimensions": {"measurement"}},
    "food-process": {"flow": {"endpoints"}, "sequence": {"text"}, "labels": {"text"}},
    "workshop-layout": {"walls": {"endpoints","closed"}, "axes": {"endpoints","length"},
                        "dimensions": {"measurement"}, "routes": {"endpoints"}, "schedule": {"text"}},
}
NUMERIC = {"endpoints","length","radius","measurement"}


def _check_dimensions(doc, tolerance):
    bad, manual = [], []
    for layout in doc.layouts:
        for entity in layout.query("DIMENSION"):
            override = entity.dxf.text.strip()
            if override in ("","<>"):
                continue
            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", override):
                measurement=entity.get_measurement()
                if tolerance is None or not isinstance(measurement,(float,int)):
                    manual.append(entity.dxf.handle)
                elif abs(float(override)-measurement)>tolerance:
                    bad.append({"handle":entity.dxf.handle,"override":override,"measured":measurement})
            else:
                manual.append(entity.dxf.handle)
    return oqa._row("dimension_display", "automated+manual",
                    "failed" if bad else "unverified" if manual else "passed",
                    {"conflicts":bad,"manual_overrides":manual})


def evaluate(drawing, domain, contract, job=None, pdf=None, publication=None,
             review=None, target="dwg-pdf"):
    if domain not in CRITICAL_FIELDS or target not in {"dxf","dwg-pdf"}:
        raise ValueError("Select a typed profile and target")
    if not isinstance(contract,dict) or not isinstance(contract.get("roles"),dict):
        raise ValueError("Acceptance contract requires a roles object")
    units=contract.get("model_units")
    if type(units) is not int or units<=0:
        raise ValueError("Specify expected DXF INSUNITS code")
    roles=contract["roles"]
    for specs in roles.values():
        for spec in specs:
            if spec.get("field") in NUMERIC:
                tolerance=spec.get("tolerance")
                if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<=0:
                    raise ValueError("Each numeric expectation needs its own explicit digital tolerance")
    tolerance=contract.get("dimension_display_tolerance")
    if tolerance is not None and (type(tolerance) not in (int,float) or not math.isfinite(tolerance) or tolerance<=0):
        raise ValueError("Invalid dimension display verification tolerance")
    base=oqa.inspect(drawing,"full" if target=="dwg-pdf" else "standard",domain,job,roles,pdf,publication)
    rows=base["rows"]
    doc=ezdxf.readfile(drawing)
    rows.append(oqa._row("expected_units","automated","passed" if doc.units==units else "failed",
                         {"expected":units,"actual":doc.units}))
    rows.append(_check_dimensions(doc,tolerance))
    # Counts by themselves are not geometry verification.
    missing=[]
    for role,fields in CRITICAL_FIELDS[domain].items():
        if not any(s.get("field") in fields and s.get("values") and s.get("count",0)>0
                   for s in roles.get(role, [])):
            missing.append(role)
    rows.append(oqa._row("critical_expectations","automated","unverified" if missing else "passed",
                         {"missing_role_values":missing}))
    if job is None:
        rows.append(oqa._row("reviewed_manifest","manual","unverified",
                             "Role samples do not prove full drawing completeness; supply reviewed manifest"))
    elif target=="dwg-pdf" and not job.get("sheet"):
        rows.append(oqa._row("sheet_expectations","manual","unverified","No reviewed sheet and scale"))
    hashes={"dxf":records.digest(drawing)}
    if pdf:
        hashes["pdf"]=records.digest(pdf)
    if publication:
        _,paths=oqa.validate_publication(publication,drawing,pdf)
        hashes.update({k:records.digest(v) for k,v in paths.items()})
    review=review or {}
    bound=review.get("sha256")==hashes
    # Reviews can resolve visual/semantic items, never a failed numeric check,
    # missing contract, missing native evidence or missing files.
    for row in rows:
        name=row["check"]
        if row["state"]=="unverified" and (name.startswith("requirement:") or
                                           name in {"dimension_display","pdf_visual_layout"}):
            decision=review.get("checks",{}).get(name,{}) if bound else {}
            if decision.get("state") in {"passed","failed"} and str(decision.get("note","")).strip():
                row.update(state=decision["state"],evidence_level="manual",
                           evidence={"original":row["evidence"],"review":decision})
    for name in ("engineering_completeness","visual_labels","layout_and_scale"):
        decision=review.get("checks",{}).get(name,{}) if bound else {}
        state=decision.get("state")
        explicit=state in {"passed","failed"} and bool(str(decision.get("note","")).strip())
        rows.append(oqa._row(name,"manual",state if explicit else "unverified",
                             decision if explicit else "Hash-bound independent review required"))
    # Soft checks never compensate for a failing hard gate.
    soft={"visual_labels","layout_and_scale","pdf_visual_layout","duplicate_dimensions"}
    hard=[r for r in rows if r["check"] not in soft]
    failures=[r["check"] for r in hard if r["state"]=="failed"]
    pending=[r["check"] for r in hard if r["state"]!="passed" and r["state"]!="failed"]
    if target=="dwg-pdf":
        for name in ("dwg_reopen","dwg_edit_samples","dwg_pdf_consistency","pdf_structure","pdf_paper_and_crop","pdf_render"):
            if not any(r["check"]==name and r["state"]=="passed" for r in rows) and name not in failures:
                pending.append(name)
    quality=[r for r in rows if r["check"] in soft]
    points=sum(r["state"]=="passed" for r in quality)
    verdict="failed" if failures or any(r["state"]=="failed" for r in quality) else (
        "pending" if pending or any(r["state"]!="passed" for r in quality) else "passed")
    return {"domain":domain,"target":target,"verdict":verdict,"hard_failures":sorted(set(failures)),
            "hard_pending":sorted(set(pending)), "soft_score":{"earned":points,"available":len(quality),
            "unverified":sum(r["state"]=="unverified" for r in quality)},
            "sha256":hashes,"rows":rows,"tolerance_scope":"digital comparison only, not manufacturing/installation tolerance"}
