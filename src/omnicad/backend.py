"""Backend boundary and the opt-in AutoCAD Windows adapter."""
import re
import sys
import time
from pathlib import Path
from typing import Protocol

from .dxf import LAYOUT
from .records import copy_new


class CadBackend(Protocol):
    def publish(self, seed: Path, destination: Path, sheet: dict | None) -> dict:
        """Return artifacts and independently verified capabilities."""


def connect():
    if sys.platform!="win32":
        raise ValueError("AutoCAD COM requires Windows")
    try:
        import pywintypes
        import win32com.client
    except ImportError as e:
        raise ValueError("AutoCAD COM requires the [autocad] extra") from e
    try:
        return win32com.client.GetActiveObject("AutoCAD.Application")
    except pywintypes.com_error as e:
        if e.hresult!=-2147221021:  # MK_E_UNAVAILABLE, no registered running object
            raise
        return win32com.client.Dispatch("AutoCAD.Application")


def active(app, expected):
    last=None
    for _ in range(15):
        try:
            c=app.ActiveDocument
            if Path(c.FullName).resolve()==expected.resolve():
                return c
        except Exception as exc:
            last=exc
        time.sleep(.4)
    raise RuntimeError(f"Could not bind exact AutoCAD document {expected.name}") from last


def open_exact(app,path):
    # Closing the last drawing can invalidate the collection briefly. Retry
    # resolving the method, not invoking an open that may already have succeeded.
    for i in range(12):
        try:
            method=app.Documents.Open
            break
        except AttributeError:
            if i==11:
                raise RuntimeError("AutoCAD Documents.Open is unavailable")
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


class AutoCAD:
    """AutoCAD is launched/attached only when this adapter is invoked explicitly."""

    def publish(self,seed,destination,sheet):
        destination=destination.resolve()
        destination.mkdir()
        work=destination/"working.dxf"
        copy_new(seed,work)
        app=connect()
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
        anchor=open_exact(app,work)
        c.Close(False)
        c=open_exact(app,dwg)
        count=c.ModelSpace.Count
        if c.ReadOnly:
            raise RuntimeError("New DWG reopened read-only")
        if sheet:
            original=c.GetVariable("BACKGROUNDPLOT")
            try:
                c.SetVariable("BACKGROUNDPLOT",0)
                if not c.Plot.PlotToFile(str(pdf),"DWG To PDF.pc3") or pdf.stat().st_size==0:
                    raise RuntimeError("AutoCAD did not write a valid-sized PDF")
            finally:
                active(app,dwg).SetVariable("BACKGROUNDPLOT",original)
        active(app,dwg).SaveAs(str(export),65)  # ac2018_dxf
        active(app,export).Close(False)
        active(app,work).Close(False)
        return {"dwg":str(dwg),"pdf":str(pdf) if sheet else None,"readback":str(export),
                "editable_reopened":True,"model_entities":count,"media":media}

    def readback(self,source,destination):
        """Export a trusted local DWG copy; leave the original unchanged."""
        destination=destination.resolve()
        destination.mkdir()
        work,export=(destination/name for name in ("working.dwg","readback.dxf"))
        copy_new(source,work)
        app=connect()
        app.Visible=True
        c=open_exact(app,work)
        c.SaveAs(str(export),65)
        active(app,export).Close(False)
        return export
