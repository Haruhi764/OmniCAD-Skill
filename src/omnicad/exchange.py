"""Editable DXF handoff and optional in-session LT 2024+ save script."""
from pathlib import Path
import json
from uuid import uuid4

import ezdxf

from .capabilities import Host
from .dxf import audit
from .records import clean, copy_new, digest, write_json
from .paper import check_pdf
from .pdfquality import strict_reader

def _script(marker):
    # Constant ASCII and a unique marker in the intended DXF folder. It never
    # changes SECURELOAD, TRUSTEDPATHS, startup configuration, or another DWG.
    return (
        '((lambda (/ prefix name program target oldfd *error*) '
        '(setq prefix (getvar "DWGPREFIX") name (strcase (getvar "DWGNAME")) '
        'program (strcase (getvar "PROGRAM")) target (strcat prefix "drawing.dwg")) '
        '(defun *error* (msg) (if oldfd (setvar "FILEDIA" oldfd)) (princ msg) (princ)) '
        f'(if (and (member program (list "ACAD" "ACADLT")) '
        '(member name (list "SEED.DXF" "SEED.DWG")) '
        f'(findfile (strcat prefix "{marker}")) (not (findfile target))) '
        '(progn (setq oldfd (getvar "FILEDIA")) (setvar "FILEDIA" 0) '
        '(command-s "_.SAVEAS" "_2018" target) '
        '(setvar "FILEDIA" oldfd) (setq oldfd nil) '
        '(if (findfile target) (princ "\\nDWG written; reopen and verify.") '
        '(princ "\\nSAVEAS did not produce drawing.dwg."))) '
        '(princ "\\nOpen the prepared seed in its own folder; target must be absent.")) (princ)))\n'
    )

def _probe_script(marker):
    return ('((lambda (/ prefix file) (setq prefix (getvar "DWGPREFIX")) '
            f'(if (and (findfile (strcat prefix "{marker}")) '
            '(member (strcase (getvar "DWGNAME")) (list "SEED.DXF" "SEED.DWG" "DRAWING.DWG")) '
            '(not (findfile (strcat prefix "session.txt")))) '
            '(progn (setq file (open (strcat prefix "session.txt") "w")) '
            '(if file (progn (write-line (strcat "PROGRAM=" (getvar "PROGRAM")) file) '
            '(write-line (strcat "ACADVER=" (getvar "ACADVER")) file) '
            '(write-line (if (getenv "WINDIR") "OS=WINDOWS" "OS=OTHER") file) (close file)))) '
            '(princ "\\nUse the prepared drawing folder; session.txt must be new.")) (princ)))\n')

def prepare(job, seed, destination, host: Host):
    seed, destination = Path(seed), Path(destination).resolve()
    if seed.suffix.lower() != ".dxf":
        raise ValueError("Exchange preparation needs an audited DXF, not raw DWG")
    report = audit(ezdxf.readfile(seed), job)
    if not clean(report):
        raise ValueError("DXF preflight failed")
    destination.mkdir()
    marker = "omnicad-" + uuid4().hex + ".guard"
    prepared = destination / "seed.dxf"
    copy_new(seed, prepared)
    write_json(destination / "job.json", job)
    (destination / marker).write_text("Local exchange scope\n", encoding="ascii")
    scripts = []
    if host.platform=="win32" and host.interfaces["autolisp"]:
        for name, value in {"inspect-session.scr": _probe_script(marker),
                            "save-as-dwg.scr": _script(marker)}.items():
            (destination / name).write_text(value, encoding="ascii")
            scripts.append(name)
    record = {"backend": "exchange", "status": "awaiting_native", "host": host.report(),
              "seed_sha256": digest(prepared), "job_sha256": digest(destination/"job.json"),
              "scripts": scripts, "required": ["drawing.dwg", "readback.dxf"] + (["sheet.pdf"] if job.get("sheet") else []),
              "native_verified": False}
    write_json(destination/"exchange.json", record)
    (destination/"README.md").write_text(
        "# Native exchange — candidate\n\n"
        "1. Open seed.dxf in a licensed installed CAD product. Preserve the original seed file. "
        "Check the drawing identity and units.\n"
        "2. On a supported Windows AutoLISP product, optionally run SCRIPT and select inspect-session.scr, "
        "then save-as-dwg.scr. Review normal security prompts; if refused, use the ordinary Save As interface. "
        "Otherwise save a new drawing.dwg manually. Use the AutoCAD 2018 DWG format for this exchange. "
        "If the script refuses the active drawing, use manual Save As only on the prepared copy.\n"
        "3. Close and reopen drawing.dwg. Check selection and perform a reversible edit on a separate "
        "work copy. Plot the intended existing layout to sheet.pdf when requested. "
        "Export the reopened DWG to a distinct readback.dxf using the DXF Save As command.\n"
        "4. Run omnicad verify-exchange <folder>. This checks the returned files and manifest. "
        "Record the actual version, reopen/edit and print review independently. "
        "A completed transfer is not a native acceptance result.\n",
        encoding="utf-8")
    return record

def verify(folder):
    folder = Path(folder).resolve()
    record = json.loads((folder/"exchange.json").read_text(encoding="utf-8"))
    jobfile, seed = folder/"job.json", folder/"seed.dxf"
    if digest(seed) != record["seed_sha256"] or digest(jobfile) != record["job_sha256"]:
        raise ValueError("Exchange seed or manifest changed")
    job = json.loads(jobfile.read_text(encoding="utf-8"))
    required = ["drawing.dwg", "readback.dxf"] + (["sheet.pdf"] if job.get("sheet") else [])
    missing = [name for name in required if not (folder/name).is_file() or not (folder/name).stat().st_size]
    if missing:
        return {"status": "awaiting_native", "missing": missing, "native_verified": False}
    with (folder/"drawing.dwg").open("rb") as dwg:
        if dwg.read(6) != b"AC1032":
            raise ValueError("Expected actual AutoCAD 2018 DWG file header")
    readback = audit(ezdxf.readfile(folder/"readback.dxf"), job)
    pdf = None
    if job.get("sheet"):
        path = folder/"sheet.pdf"
        strict_reader(path.read_bytes())
        pdf = check_pdf(path, job)
    success = clean(readback) and (pdf is None or pdf["paper_and_crop_ok"])
    return {"status": "awaiting_native_review" if success else "failed",
            "readback": readback, "paper": pdf, "file_sha256": {n: digest(folder/n) for n in required},
            "native_verified": False,
            "reason": "Returned artifacts need independently witnessed reopen, edit and drawing-to-print consistency"}
