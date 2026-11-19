"""Local, read-only intake. It inventories evidence rather than guessing geometry."""
from pathlib import Path
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET

from .records import digest,write_json

CACHE_VERSION=1
MAX_XML=20<<20


def pdf_info(path, include_text=True):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ValueError("PDF intake requires the [intake] extra") from e
    document=PdfReader(path)
    if document.is_encrypted:
        raise ValueError("Encrypted PDF requires an authorized decrypted local copy")
    pages=[]
    for p in document.pages:
        unit=float(p.user_unit)
        w,h=float(p.mediabox.width)*unit,float(p.mediabox.height)*unit
        cw,ch=float(p.cropbox.width)*unit,float(p.cropbox.height)*unit
        if p.rotation%180:
            w,h=h,w
            cw,ch=ch,cw
        item={"size_mm":[round(x*25.4/72,4) for x in (w,h)],
              "crop_mm":[round(x*25.4/72,4) for x in (cw,ch)]}
        if include_text:
            item["text"]=(p.extract_text() or "")[:16000]
        pages.append(item)
    return {"pages":pages}


def inspect_source(path, format_hint):
    if format_hint==".pdf":
        return pdf_info(path)|{"limits":"Text and paper size only. Confirm dimensions and leaders against a render."}
    if format_hint==".docx":
        ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with ZipFile(path) as z:
            part=z.getinfo("word/document.xml")
            if part.file_size>MAX_XML:
                raise ValueError("Word document XML exceeds intake limit")
            tree=ET.fromstring(z.read(part))
        data=["".join(n.text or "" for n in p.iter(ns+"t")) for p in tree.iter(ns+"p")]
        return {"paragraphs":[s for s in data if s.strip()],
                "limits":"Body text and table cells only; images, footnotes, revision history and comments require review."}
    if format_hint==".dxf":
        import ezdxf
        from collections import Counter
        d=ezdxf.readfile(path)
        return {"units":d.units,"layouts":d.layout_names(),"layers":[x.dxf.name for x in d.layers],
                "entities":dict(Counter(e.dxftype() for e in d.modelspace()))}
    if format_hint==".dwg":
        with path.open("rb") as f:
            code=f.read(6).decode("ascii",errors="replace")
        if not code.startswith("AC10"):
            raise ValueError("Invalid DWG header")
        return {"version_header":code,"limits":"Header only. Use authorized AutoCAD readback for entity QA."}
    if format_hint in {".jpg",".jpeg",".png",".tif",".tiff",".webp"}:
        try:
            from PIL import Image
        except ImportError as e:
            raise ValueError("Image intake requires the [intake] extra") from e
        with Image.open(path) as im:
            return {"width_px":im.width,"height_px":im.height,"format":im.format,
                    "limits":"Metadata only. No OCR, measurement calibration or automatic tracing."}
    if format_hint in {".txt",".md"}:
        if path.stat().st_size>2<<20:
            raise ValueError("Text source exceeds 2 MiB limit")
        return {"text":path.read_text(encoding="utf-8-sig")}
    raise ValueError(f"Unsupported input format {format_hint}")


def inspect(path: Path, cache_dir: Path):
    suffix=path.suffix.lower()
    sha=digest(path)
    cache_dir.mkdir(parents=True,exist_ok=True)
    cached=cache_dir/f"v{CACHE_VERSION}-{sha}-{suffix[1:].isalnum() and suffix[1:] or 'unknown'}.json"
    if cached.exists():
        return {"cache_hit":True,"path":str(cached),"data":json.loads(cached.read_text(encoding="utf-8"))}
    data={"format":suffix,"sha256":sha,"result":inspect_source(path,suffix)}
    if digest(path)!=sha:
        raise ValueError("Input changed during intake")
    write_json(cached,data)
    return {"cache_hit":False,"path":str(cached),"data":data}
