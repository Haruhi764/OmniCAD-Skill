"""Discipline-aware checks with separate automated, native and review evidence."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import ezdxf

from . import dxf, records
from .formal import drawing_text, internal_notes, pdf_metadata_notes
from .paper import check_pdf, preview
from .pdfquality import strict_reader


DOMAINS = {
    "general": (),
    "architecture": ("walls", "openings", "axes", "dimensions"),
    "civil": ("geometry", "elevations", "axes", "sections", "components"),
    "mechanical": ("profile", "dimensions", "annotations", "sections"),
    "food-process": ("equipment", "flow", "labels", "sequence"),
    "workshop-layout": ("walls", "openings", "axes", "dimensions", "equipment", "routes", "schedule"),
}
MODES = {"light": 0, "standard": 1, "full": 2}
OPAQUE = {"IMAGE", "PDFUNDERLAY", "ACAD_PROXY_ENTITY", "DWFUNDERLAY", "DGNUNDERLAY"}


def _row(name, level, state, evidence):
    return {"check": name, "evidence_level": level, "state": state, "evidence": evidence}


def _role_values(matches, spec):
    field=spec.get("field")
    expected=spec.get("values")
    if field is None and expected is None:
        return {}
    if field not in {"length","radius","measurement","text","closed","endpoints"} or not isinstance(expected,list):
        raise ValueError("Role values require a field and a list of reviewed expected values")
    supported={"length":{"LINE"},"radius":{"CIRCLE","ARC"},"measurement":{"DIMENSION"},
               "text":{"TEXT","MTEXT","ATTRIB"}, "closed":{"LWPOLYLINE","POLYLINE"},
               "endpoints":{"LINE"}}
    if spec["type"].upper() not in supported[field]:
        raise ValueError(f"{field} is unavailable on {spec['type']}")
    if field=="text":
        actual=sorted(drawing_text(e) for e in matches)
        expected=sorted(expected)
        return {"field":field,"expected_values":expected,"actual_values":actual,"values_ok":actual==expected}
    if field=="closed":
        if any(type(x) is not bool for x in expected):
            raise ValueError("Expected closure values must be boolean")
        actual=sorted(bool(e.closed if e.dxftype()=="LWPOLYLINE" else e.is_closed) for e in matches)
        return {"field":field,"expected_values":sorted(expected),"actual_values":actual,
                "values_ok":actual==sorted(expected)}
    from math import dist, isfinite

    tol=spec.get("tolerance",.01)
    if field=="endpoints":
        # Keep start/end order; allow only explicit 2D/3D coordinates.
        def pair(value):
            if (not isinstance(value,(list,tuple)) or len(value)!=2 or
                any(not isinstance(p,(list,tuple)) or len(p) not in (2,3) or
                    any(type(x) not in (int,float) or not isfinite(x) for x in p) for p in value)):
                raise ValueError("Endpoint values require two finite XY or XYZ points")
            return tuple(tuple(p)+(0,)*(3-len(p)) for p in value)
        if type(tol) not in (int,float) or not isfinite(tol) or tol<=0:
            raise ValueError("Endpoint tolerance must be positive and finite")
        actual=[(tuple(e.dxf.start),tuple(e.dxf.end)) for e in matches]
        wanted=[pair(v) for v in expected]
        # Bipartite matching avoids order-dependent pairing at nearby positions.
        candidates=[[j for j,(c,d) in enumerate(actual) if dist(a,c)<=tol and dist(b,d)<=tol]
                    for a,b in wanted]
        assigned={}
        def assign(i,seen):
            for j in candidates[i]:
                if j in seen:
                    continue
                seen.add(j)
                if j not in assigned or assign(assigned[j],seen):
                    assigned[j]=i
                    return True
            return False
        ok=len(actual)==len(wanted) and all(assign(i,set()) for i in range(len(wanted)))
        return {"field":field,"expected_values":wanted,"actual_values":actual,"values_ok":ok}
    if (type(tol) not in (int,float) or not isfinite(tol) or tol<=0 or
        any(type(value) not in (int,float) or not isfinite(value) for value in expected)):
        raise ValueError("Expected role measures and tolerance must be finite")
    if field=="length":
        actual=sorted(dist(e.dxf.start,e.dxf.end) for e in matches)
    elif field=="radius":
        actual=sorted(e.dxf.radius for e in matches)
    else:
        actual=sorted(e.get_measurement() for e in matches)
    expected=sorted(expected)
    ok=len(actual)==len(expected) and all(abs(x-y)<=tol for x,y in zip(actual,expected))
    return {"field":field,"expected_values":expected,"actual_values":actual,"values_ok":ok}


def _known_parts(doc, contract, domain):
    if not isinstance(contract, dict) or set(contract)-set(DOMAINS[domain]):
        raise ValueError("Contract must map known domain roles to checks")
    model = doc.modelspace()
    rows = []
    for role in DOMAINS[domain]:
        specs = contract.get(role, [])
        if not specs:
            rows.append(_row(role, "manual", "unverified", "No reviewed role expectations were supplied"))
            continue
        failures = []
        evidence = []
        for spec in specs:
            if not isinstance(spec.get("layer"), str) or not isinstance(spec.get("type"), str):
                raise ValueError("Each role expectation needs an explicit layer and entity type")
            count=spec["count"]
            if type(count) is not int or count<0:
                raise ValueError("Expected count must be a nonnegative integer")
            matches=[e for e in model if e.dxftype()==spec["type"].upper()
                     and e.dxf.layer.casefold()==spec["layer"].casefold()]
            result={"layer":spec["layer"],"type":spec["type"],"expected":count,"measured":len(matches)}
            result.update(_role_values(matches,spec))
            evidence.append(result)
            if count!=len(matches) or not result.get("values_ok",True):
                failures.append(result)
        rows.append(_row(role, "automated", "failed" if failures else "passed", evidence))
    return rows


def _dimension_duplicates(doc):
    duplicates=[]
    for layout in doc.layouts:
        seen={}
        for e in layout.query("DIMENSION"):
            key=tuple(tuple(v) for v in (e.dxf.defpoint, e.dxf.defpoint2, e.dxf.defpoint3)
                      if v is not None)
            if len(key)==3:
                key=(key[0],*sorted(key[1:]),e.dxf.dimtype % 32,e.dxf.angle)
                if key in seen:
                    duplicates.append([layout.name,seen[key],e.dxf.handle])
                seen[key]=e.dxf.handle
    return duplicates


def verify_print(first, second, dpi=100):
    from PIL import Image, ImageChops
    from pypdf import PdfReader

    pages=[len(PdfReader(p,strict=False).pages) for p in (first,second)]
    if pages[0]!=pages[1] or not pages[0]:
        return False
    with TemporaryDirectory(prefix=".print-check-",dir=first.parent) as out:
        for page in range(1,pages[0]+1):
            pngs=[Path(out)/f"{name}-{page}.png" for name in ("a","b")]
            for pdf,png in zip((first, second),pngs):
                preview(pdf,png,dpi=dpi,page=page)
            with Image.open(pngs[0]) as a, Image.open(pngs[1]) as b:
                if a.size!=b.size or ImageChops.difference(a.convert("RGB"),b.convert("RGB")).getbbox() is not None:
                    return False
    return True


def validate_publication(publication, drawing, pdf=None):
    autocad=publication["autocad"]
    paths={label:Path(autocad[key]) for label,key in (("dxf","readback"),("dwg","dwg"),("pdf","pdf"))
           if autocad.get(key)}
    if not {"dwg","dxf"} <= paths.keys() or paths["dxf"].resolve()!=drawing.resolve():
        raise ValueError("Publication does not identify this native DXF readback")
    if pdf is not None and ("pdf" not in paths or paths["pdf"].resolve()!=pdf.resolve()):
        raise ValueError("Publication does not identify this PDF")
    if {k: records.digest(p) for k,p in paths.items()}!=publication["trace"]["artifacts_sha256"]:
        raise ValueError("Publication artifact fingerprint changed")
    return autocad, paths


def _pdf_checks(pdf, job, expected_text, full):
    from pypdf.errors import PdfReadError

    rows=[]
    try:
        reader=strict_reader(pdf.read_bytes())
        rows.append(_row("pdf_structure","automated","passed",{"pages":len(reader.pages)}))
        notes=pdf_metadata_notes(reader)
        rows.append(_row("pdf_user_metadata","automated","failed" if notes else "passed",notes))
    except (PdfReadError,ValueError) as e:
        return [_row("pdf_structure","automated","failed",str(e))]
    if job and "sheet" in job:
        paper=check_pdf(pdf,job)
        rows.append(_row("pdf_paper_and_crop","automated","passed" if paper["paper_and_crop_ok"] else "failed",paper))
    if expected_text:
        actual=" ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
        missing=[s for s in expected_text if " ".join(s.split()) not in actual]
        rows.append(_row("pdf_expected_text","automated","failed" if missing else "passed",{"missing":missing}))
    if full:
        import shutil
        from subprocess import SubprocessError

        if not shutil.which("pdftoppm"):
            rows.append(_row("pdf_render","automated","unverified","Poppler is unavailable"))
        else:
            try:
                with TemporaryDirectory(prefix=".render-check-",dir=pdf.parent) as out:
                    for page in range(1,len(reader.pages)+1):
                        preview(pdf,Path(out)/f"preview-{page}.png",page=page)
            except (OSError,SubprocessError) as exc:
                rows.append(_row("pdf_render","automated","failed",str(exc)))
            else:
                rows.append(_row("pdf_render","automated","passed",f"Poppler rendered {len(reader.pages)} pages"))
        rows.append(_row("pdf_visual_layout","manual","unverified","Inspect glyphs, hierarchy and collisions at output scale"))
    return rows


def inspect(drawing, mode="light", domain="general", job=None, contract=None, pdf=None,
            publication=None, expected_text=(), resource_metrics=None):
    t=perf_counter()
    doc=ezdxf.readfile(drawing)
    model=doc.modelspace()
    checks=doc.audit()
    rows=[_row("dxf_integrity","automated","failed" if checks.errors or checks.fixes else "passed",
               {"errors":len(checks.errors),"fixes":len(checks.fixes),"model_units":doc.units})]
    type_counts=Counter(e.dxftype() for e in model)
    opaque=sorted(set(type_counts)&OPAQUE)
    rows.append(_row("model_entities","automated","failed" if not model or opaque else "passed",
                     {"types":dict(type_counts),"opaque_types":opaque}))
    notes=internal_notes(doc)
    rows.append(_row("formal_text","automated","failed" if notes else "passed",notes))
    depth=MODES[mode]
    if depth:
        if job:
            result=dxf.audit(doc,job)
            rows.append(_row("manifest_geometry","automated","passed" if records.clean(result) else "failed",result))
            scope=records.trace(job,result,{"dxf":records.digest(drawing)})
            rows.extend(_row("requirement:"+r["id"],"manual","unverified",r["statement"])
                        for r in scope["requirements"] if r["scope"] in {"required","undecided"} and
                        r["state"] in {"undecided","review_needed"})
        rows.extend(_known_parts(doc,contract or {},domain))
        symbols=[]
        for layout in doc.layouts:
            for e in layout:
                if e.dxftype() in {"TEXT","MTEXT","ATTRIB"}:
                    content=drawing_text(e)
                    if not content.strip() or "\ufffd" in content or e.dxf.style not in doc.styles:
                        symbols.append([layout.name,e.dxf.handle])
        rows.append(_row("text_encoding_and_styles","automated","failed" if symbols else "passed",symbols))
        repeats=_dimension_duplicates(doc)
        rows.append(_row("duplicate_dimensions","automated","failed" if repeats else "passed",repeats))
    if publication:
        native,paths=validate_publication(publication,drawing,pdf)
        pdf=paths.get("pdf")
        rows.append(_row("dwg_reopen","AutoCAD","passed" if native.get("editable_reopened") else "failed",
                         {"sha256":records.digest(paths["dwg"]),"model_entities":native.get("model_entities")}))
        edits=native.get("edit_samples",{})
        rows.append(_row("dwg_edit_samples","AutoCAD","passed" if edits else "unverified",
                         edits or "No actual edit-and-restore samples"))
        ref=native.get("replot")
        if depth==2 and pdf and ref:
            reference=Path(ref)
            if records.digest(reference)!=native["replot_sha256"]:
                raise ValueError("Independent plot fingerprint changed")
            same=verify_print(pdf,reference)
            rows.append(_row("dwg_pdf_consistency","AutoCAD","passed" if same else "failed",
                             {"basis":"second plot after reopening the same DWG","dpi":100}))
    if pdf:
        rows.extend(_pdf_checks(pdf,job,expected_text,depth==2))
    if depth==2:
        completed={r["check"] for r in rows}
        for name in ("dwg_reopen","dwg_edit_samples","dwg_pdf_consistency"):
            if name not in completed:
                rows.append(_row(name,"AutoCAD","unverified","Matching native evidence was not supplied"))
        if not pdf and job and "pdf" in job.get("required_formats",[]):
            rows.append(_row("pdf_structure","automated","unverified","Requested PDF was not supplied"))
    states=Counter(r["state"] for r in rows)
    return {"mode":mode,"domain":domain,"rows":rows,"coverage":dict(states),
            "verified_fraction":{"passed":states["passed"],"checks":len(rows)},
            "timing_seconds":round(perf_counter()-t,4),"model_calls":0,
            "tokens":None,"supplied_resource_metrics":resource_metrics}
