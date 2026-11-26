"""Flag internal working notes in CAD deliverables for explicit review."""

import re
from unicodedata import normalize


MARKERS = re.compile(
    r"(?:待(?:确认|定位|核实|核|布置|统一|复核|补充|定)|资料不足|设计(?:存在)?冲突|"
    r"AI检查记录|(?:内部|临时)(?:检查|审图|工作|说明|备注)|按老师意见|"
    r"FORINTERNALUSE|INTERNALREVIEWONLY|(?:^|\W)TBD(?:$|\W)|"
    r"(?<![A-Za-z])(?:Codex|ChatGPT|OpenAI|AI\s*Generated)(?![A-Za-z])|"
    r"[A-Z]:[\\/][^\r\n]*?\.(?:py|lsp|scr)(?=$|\s))",
    re.IGNORECASE,
)

DEBUG_NAME = re.compile(r"^(?:DEBUG(?:$|[_-])|AUTOMATION[_-]?TEST|TEMP[_-]?TEST|TEST[_-]OBJECTS)",re.I)


def drawing_text(entity):
    kind = entity.dxftype()
    if kind == "MTEXT":
        return entity.plain_text()
    if kind in {"MULTILEADER", "MLEADER"}:
        return entity.get_mtext_content()
    if kind in {"TEXT", "ATTRIB", "ATTDEF", "DIMENSION"}:
        return entity.dxf.get("text", "")
    return ""


def internal_notes(doc):
    """Return candidate handles in layouts, attributes and reachable blocks.

    A match calls for review. Never erase an entity based on a keyword alone.
    Unreferenced block definitions and CAD xrefs are outside this scan.
    """
    pending = [(layout.name, iter(layout)) for layout in doc.layouts]
    visited_blocks = set()
    findings = []
    for location, names in (("layer_name",[x.dxf.name for x in doc.layers]),
                            ("block_name",[x.name for x in doc.blocks]),
                            ("layout_name",[x.name for x in doc.layouts])):
        for name in names:
            marker = DEBUG_NAME.search(name) or MARKERS.search(name)
            if marker:
                findings.append({"location":location,"handle":"","layer":"",
                                 "marker":marker.group(),"text":name})
    while pending:
        location, entities = pending.pop()
        for entity in entities:
            text = drawing_text(entity)
            normalized = normalize("NFKC", text)
            compact = re.sub(r"\s+", "", normalized)
            match = MARKERS.search(compact) or MARKERS.search(normalized)
            if match:
                findings.append({"location": location, "handle": entity.dxf.handle,
                                 "layer": entity.dxf.layer, "marker": match.group().strip(), "text": text})
            if entity.dxftype() != "INSERT":
                continue
            pending.append((location, iter(entity.attribs)))
            name = entity.dxf.name
            key = name.casefold()
            block = doc.blocks.get(name)
            if block is not None and key not in visited_blocks:
                visited_blocks.add(key)
                pending.append((f"block:{name}", iter(block)))
    return sorted(findings, key=lambda item: (item["location"], item["handle"]))


def pdf_metadata_notes(reader):
    """Review user-facing metadata only. Preserve genuine producer/provenance."""
    meta=reader.metadata or {}
    findings=[]
    for key in ("/Title","/Author","/Subject","/Keywords"):
        value=str(meta.get(key,""))
        if MARKERS.search(normalize("NFKC",value)):
            findings.append({"field":key,"value":value})
    return findings
