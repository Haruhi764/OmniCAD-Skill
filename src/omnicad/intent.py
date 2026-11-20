"""Conservative scope routing for a reviewed drawing job."""
from pathlib import Path
import re

from ezdxf.lldxf.tagwriter import TagCollector

from .dxf import indexed


def analyze(request, reference=(), target=None, region=None, preserve=(), constraints=(), swap_pair=()):
    if not request.strip():
        raise ValueError("A request is required")
    change = bool(re.search(r"修改|简化|调整|调换|互换|保持不变|原.{0,4}DWG|revise|simplif|swap|only edit|unchanged",
                            request, re.I))
    redraw = bool(re.search(r"照.{0,7}(图|画)|重绘|仿照|redraw|trace", request, re.I))
    bounded = bool(re.search(r"只.{0,4}(改|调)|仅.{0,4}(改|调)|这里|其余|不变|only|unchanged", request, re.I))
    swap = bool(re.search(r"调换|互换|\bswap\b", request, re.I))
    route = "revise" if change or target or bounded else ("redraw" if redraw else "review")
    missing = []
    if route == "revise" and not target:
        missing.append("Exact editable drawing to revise")
    if (bounded or re.search(r"简化|simplif",request,re.I)) and not region:
        missing.append("Reviewed region or entity IDs")
    if route == "redraw" and not reference:
        missing.append("Reviewed reference drawing")
    if swap and (len(swap_pair)!=2 or len(set(swap_pair))!=2 or not all(v.strip() for v in swap_pair)):
        missing.append("Two distinct features or rooms and the intended exchange")
    if target and any(Path(r).resolve()==Path(target).resolve() for r in reference):
        missing.append("Separate reference and target roles, or explicitly use the target as the baseline")
    if route == "revise" and target and Path(target).suffix.casefold() not in {".dxf",".dwg"}:
        missing.append("Editable DWG or DXF target")
    clauses=[part.strip() for part in re.split(r"[。；;\n]",request) if part.strip()]
    return {"source_request":request,"retention_candidates":[c for c in clauses if re.search(r"保留|不变|preserve|unchanged",c,re.I)],
            "constraint_candidates":[c for c in clauses if re.search(r"不得|禁止|不能|must not",c,re.I)],"route":route,"reference":list(reference),"target":target,"allowed_region":region,
            "preserve":list(preserve),"constraints":list(constraints),"swap_pair":list(swap_pair),
            "missing":missing,"requires_review":True,"requires_diff":route=="revise"}


def _geometry(e):
    tags=TagCollector.dxftags(e)
    return tuple((t.code,str(t.value)) for t in tags if t.code not in {5,105,330})


def snapshot(doc):
    result={}
    for layout in doc.layouts:
        space=layout.name
        if space != "Model":
            result[f"layout:{space}"]=_geometry(layout.dxf_layout)
        ids={e.dxf.handle:k for k,e in indexed(layout).items()}
        for e in layout:
            result[f"{space}:{ids.get(e.dxf.handle,'@'+e.dxf.handle)}"]=_geometry(e)
    for block in doc.blocks:
        if block.name.lower().startswith(("*model_space","*paper_space")) or re.fullmatch(r"\*d\d+",block.name,re.I):
            continue
        result[f"block:{block.name}"]=tuple(_geometry(entity) for entity in block)
    for field in ("layers","styles","linetypes","dimstyles"):
        for row in getattr(doc,field):
            result[f"{field}:{row.dxf.name}"]=_geometry(row)
    result["header:units"] = doc.units
    return result


def compare_drawings(before, after, allowed=None):
    """DXF semantic guard for the same drawing lineage; external edits may rekey handles."""
    a,b=snapshot(before),snapshot(after)
    added,removed=sorted(b.keys()-a.keys()),sorted(a.keys()-b.keys())
    changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k])
    outside=sorted(set(added+removed+changed)-set(allowed or [])) if allowed is not None else None
    return {"added":added,"removed":removed,"changed":changed,"outside_allowlist":outside,
            "scope_verified":outside==[]}
