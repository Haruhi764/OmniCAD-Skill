"""Backend boundary and the opt-in AutoCAD Windows adapter."""
import re
import sys
import time
from pathlib import Path
from typing import Protocol

from .dxf import LAYOUT
from .records import copy_new, digest
from .capabilities import session_identity
from .supervisor import classify


class CadBackend(Protocol):
    def publish(self, seed: Path, destination: Path, sheet: dict | None) -> dict:
        """Return artifacts and independently verified capabilities."""


def ready_identity(app):
    """Wait briefly for read-only COM startup queries. Never replay a CAD write."""
    for attempt in range(12):
        try:
            host = session_identity(app)
            if host.product == "autocad":
                _ = app.Documents.Count
            return host
        except Exception as exc:
            if classify(exc) != "busy" or attempt == 11:
                raise
            time.sleep(.35)


def connect(expected_year=None):
    if sys.platform!="win32":
        raise ValueError("AutoCAD COM requires Windows")
    try:
        import pywintypes
        import win32com.client
    except ImportError as e:
        raise ValueError("AutoCAD COM requires the [autocad] extra") from e
    try:
        app = win32com.client.GetActiveObject("AutoCAD.Application")
    except pywintypes.com_error as e:
        if e.hresult!=-2147221021:  # MK_E_UNAVAILABLE, no registered running object
            raise
        app = win32com.client.Dispatch("AutoCAD.Application")
    host = ready_identity(app)
    if host.product != "autocad":
        raise RuntimeError("Live host identity is not confirmed full AutoCAD; use DXF exchange")
    if expected_year is not None and host.year != expected_year:
        raise RuntimeError("Live AutoCAD release does not match requested release")
    return app


def active(app, expected):
    """Resolve a verified full path even if AutoCAD keeps a different tab active."""
    expected_path = expected.resolve()

    def matches(candidate):
        if candidate is None or Path(candidate.FullName).resolve() != expected_path:
            return False
        # Dynamic dispatch can expose FullName on the Open wrapper itself.
        # Confirm a document-only read before retaining the proxy.
        _ = candidate.ModelSpace.Count
        return True

    last = None
    for _ in range(15):
        try:
            candidate = app.ActiveDocument
            if matches(candidate):
                return candidate
        except Exception as exc:
            if classify(exc) != "busy" and not isinstance(exc, AttributeError):
                raise
            last = exc
        try:
            documents = app.Documents
            for index in range(documents.Count):
                try:
                    candidate = documents.Item(index)
                    if matches(candidate):
                        return candidate
                except AttributeError as exc:
                    last = exc
        except Exception as exc:
            if classify(exc) != "busy" and not isinstance(exc, AttributeError):
                raise
            last = exc
        time.sleep(.4)
    raise RuntimeError(f"Could not bind exact AutoCAD document {expected.name}") from last


def open_exact(app,path):
    # Closing the last drawing can invalidate the collection briefly. Retry
    # resolving the method, not invoking an open that may already have succeeded.
    for i in range(12):
        try:
            method=app.Documents.Open
            break
        except Exception as exc:
            if not isinstance(exc, AttributeError) and classify(exc) != "busy":
                raise
            if i==11:
                raise RuntimeError("AutoCAD Documents.Open is unavailable") from exc
            time.sleep(.4)
    method(str(path.resolve()),False)
    return active(app,path)


def layout_to_pdf(c,pdf,sheet):
    lay=c.Layouts.Item(LAYOUT)
    c.ActiveLayout=lay
    c.MSpace=False
    lay.ConfigName="DWG To PDF.pc3"
    lay.RefreshPlotDeviceInfo()
    w,h=sheet["size_mm"]
    candidates=[]
    for name in lay.GetCanonicalMediaNames():
        media=re.search(r"\(([\d.]+)_x_([\d.]+)_MM\)",name)
        if not media or "full_bleed" not in name.lower():
            continue
        a,b=map(float,media.groups())
        if abs(a-w)<.1 and abs(b-h)<.1:
            candidates.append((0,name))
        elif abs(a-h)<.1 and abs(b-w)<.1:
            candidates.append((1,name))
    if not candidates:
        raise ValueError("No matching full-bleed ISO media on DWG To PDF.pc3")
    rotation,name=min(candidates)
    lay.CanonicalMediaName=name
    lay.PlotRotation=rotation
    lay.PaperUnits=1
    lay.UseStandardScale=True
    lay.StandardScale=16
    lay.PlotType=5
    lay.PlotWithLineweights=True
    lay.PlotWithPlotStyles=True
    lay.StyleSheet="monochrome.ctb"
    c.Regen(1)
    return name


def plot(c, target):
    original = c.GetVariable("BACKGROUNDPLOT")
    try:
        c.SetVariable("BACKGROUNDPLOT", 0)
        if not c.Plot.PlotToFile(str(target), "DWG To PDF.pc3") or target.stat().st_size == 0:
            raise RuntimeError("AutoCAD did not write a valid-sized PDF")
    finally:
        c.SetVariable("BACKGROUNDPLOT", original)


def edit_samples(c):
    from pythoncom import VT_ARRAY, VT_DISPATCH, VT_R8
    from win32com.client import VARIANT

    point = lambda x: VARIANT(VT_ARRAY | VT_R8, (x, 0., 0.))
    accepted = {"AcDbLine", "AcDbCircle", "AcDbArc", "AcDbPolyline", "AcDbText", "AcDbMText",
                "AcDbHatch", "AcDbRotatedDimension", "AcDbAlignedDimension", "AcDbFcf"}
    verified = {}
    pick = c.SelectionSets.Add("OmniCADVerification")
    try:
        model = c.ModelSpace
        for i in range(model.Count):
            e = model.Item(i)
            kind = e.ObjectName
            if kind not in accepted or kind in verified:
                continue
            pick.AddItems(VARIANT(VT_ARRAY | VT_DISPATCH, (e,)))
            if pick.Count != 1:
                raise RuntimeError(f"Could not select {kind}")
            if kind == "AcDbFcf":
                previous = e.TextString
                changed = previous + " "
                try:
                    e.TextString = changed
                    ok = e.TextString == changed
                finally:
                    e.TextString = previous
                ok = ok and e.TextString == previous
            else:
                previous = e.GetBoundingBox()[0][0]
                try:
                    e.Move(point(0), point(.5))
                    ok = abs(e.GetBoundingBox()[0][0]-previous-.5) < 1e-5
                finally:
                    e.Move(point(.5), point(0))
                ok = ok and abs(e.GetBoundingBox()[0][0]-previous) < 1e-5
            if not ok:
                raise RuntimeError(f"Native edit and restore failed: {kind}")
            verified[kind] = e.Handle
            pick.Clear()
    finally:
        pick.Delete()
    return verified


class AutoCAD:
    """AutoCAD is launched/attached only when this adapter is invoked explicitly."""

    def __init__(self, expected_year=None):
        self.expected_year = expected_year

    def publish(self,seed,destination,sheet,verify_native=False):
        destination=destination.resolve()
        destination.mkdir()
        work=destination/"working.dxf"
        copy_new(seed,work)
        app=connect(self.expected_year)
        app.Visible=True
        c=open_exact(app,work)
        dwg,pdf,export=(destination/name for name in ("drawing.dwg","sheet.pdf","readback.dxf"))
        media=None
        if sheet:
            media=layout_to_pdf(c,pdf,sheet)
        c.SaveAs(str(dwg),64)  # ac2018_dwg
        c=active(app,dwg)
        # Keep a known work document open while reopening the saved DWG. Some
        # versions do not expose Documents.Open with AutoCAD Start active.
        open_exact(app,work)
        c.Close(False)
        c=open_exact(app,dwg)
        count=c.ModelSpace.Count
        if c.ReadOnly:
            raise RuntimeError("New DWG reopened read-only")
        output = {"dwg":str(dwg),"pdf":str(pdf) if sheet else None,"readback":str(export),
                  "host":session_identity(app).report(),
                  "editable_reopened":True,"model_entities":count,"media":media}
        primary_error = None
        try:
            if sheet:
                from .pdfquality import repair_plot

                raw = destination/"raw-plot.pdf"
                plot(c,raw)
                output["pdf_structure_repair"] = repair_plot(raw,pdf)
                if not pdf.exists():
                    copy_new(raw,pdf)
            if verify_native:
                output["edit_samples"] = edit_samples(c)
                c.Close(False)
                c = open_exact(app,dwg)
                if sheet:
                    replot = destination/"independent.pdf"
                    plot(c,replot)
                    output["replot"] = str(replot)
                    output["replot_sha256"] = digest(replot)
            c.SaveAs(str(export),65)
            c = active(app,export)
        except Exception as exc:
            primary_error = exc
            raise
        finally:
            try:
                try:
                    c.Close(False)
                finally:
                    active(app,work).Close(False)
            except Exception:
                if primary_error is None:
                    raise
        return output

    def readback(self,source,destination):
        """Export a trusted local DWG copy; leave the original unchanged."""
        destination=destination.resolve()
        destination.mkdir()
        work,export=(destination/name for name in ("working.dwg","readback.dxf"))
        copy_new(source,work)
        app=connect(self.expected_year)
        app.Visible=True
        c=open_exact(app,work)
        c.SaveAs(str(export),65)
        active(app,export).Close(False)
        return export
