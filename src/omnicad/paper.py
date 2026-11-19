"""PDF page/crop checks and bounded local raster previews."""
import shutil
import subprocess

from .intake import pdf_info


def check_pdf(path,sheet,tolerance_mm=.5):
    if "sheet" not in sheet:
        raise ValueError("PDF QA requires a sheet in the manifest")
    pages=pdf_info(path,include_text=False)["pages"]
    expected=sheet["sheet"]["size_mm"]
    matches=[len(pages)==1, all(abs(a-b)<=tolerance_mm for a,b in zip(pages[0]["size_mm"],expected)) if pages else False,
             all(abs(a-b)<=tolerance_mm for a,b in zip(pages[0]["crop_mm"],expected)) if pages else False]
    return {"pages":pages,"expected_mm":expected,"paper_and_crop_ok":all(matches),
            "visual_review_needed":True}


def preview(pdf,out,region=None,dpi=120,page=1):
    exe=shutil.which("pdftoppm")
    if not exe:
        raise ValueError("Preview requires local Poppler pdftoppm on PATH")
    if not 48<=dpi<=350 or page<1:
        raise ValueError("Preview DPI must be 48–350 and page a positive integer")
    if pdf.suffix.lower()!=".pdf" or out.suffix.lower()!=".png":
        raise ValueError("Expected a PDF input and a new PNG output")
    args=[exe,"-r",str(dpi),"-f",str(page),"-l",str(page),"-singlefile","-png"]
    if region:
        x,y,w,h=region
        if min(x,y)<0 or min(w,h)<1 or w*h>24_000_000:
            raise ValueError("Invalid or excessively large crop region")
        args+=["-x",str(x),"-y",str(y),"-W",str(w),"-H",str(h)]
    import tempfile
    from pathlib import Path
    from .records import copy_new
    if out.exists():
        raise FileExistsError(out)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        prefix=Path(tmp)/"render"
        subprocess.run([*args,str(pdf.resolve()),str(prefix.resolve())],check=True,timeout=45,
                       capture_output=True)
        copy_new(prefix.with_suffix(".png"),out)
