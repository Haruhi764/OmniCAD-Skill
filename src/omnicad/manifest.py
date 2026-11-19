"""Validate explicit drafting inputs without inferring geometry from prose."""
import json
import math
from pathlib import Path


KINDS = {"line", "circle", "arc", "polyline", "text", "linear_dimension"}
SCOPES = {"required", "optional", "excluded", "undecided"}


class InvalidJob(ValueError):
    pass


def number(value, at, lower=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InvalidJob(f"{at}: expected a finite number")
    if lower is not None and value <= lower:
        raise InvalidJob(f"{at}: expected a number greater than {lower}")
    return float(value)


def point(value, at):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InvalidJob(f"{at}: expected [x,y]")
    return tuple(number(x, at) for x in value)


def nonempty(value, at):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise InvalidJob(f"{at}: expected printable nonempty text")
    return value


def validate(data):
    if data.get("version") != 1 or data.get("units") != "mm":
        raise InvalidJob("Expected manifest version 1 and units mm")
    formats=data.get("required_formats",["dxf"])
    if not isinstance(formats,list) or not formats or set(formats)-{"dxf","dwg","pdf"}:
        raise InvalidJob("required_formats must contain dxf, dwg or pdf")
    if "pdf" in formats and "sheet" not in data:
        raise InvalidJob("PDF delivery requires a sheet")
    for field in ("title", "drawing_id"):
        nonempty(data[field], field)
    tolerance = number(data.get("tolerance_mm", 0.01), "tolerance_mm", 0)
    layers = data["layers"]
    if not isinstance(layers, dict) or not layers:
        raise InvalidJob("At least one named layer is required")
    if len({x.casefold() for x in layers}) != len(layers):
        raise InvalidJob("Layer names must be distinct irrespective of case")
    for name, details in layers.items():
        nonempty(name, "layer name")
        if name.casefold() in {"0", "defpoints", "_omnicad_viewport", "_omnicad_frame"}:
            raise InvalidJob(f"Reserved layer {name}")
        color = details.get("color", 7)
        if type(color) is not int or not 1 <= color <= 255:
            raise InvalidJob(f"{name}: invalid ACI color")
        weight = details.get("weight", 25)
        if weight not in {0,5,9,13,15,18,20,25,30,35,40,50,53,60,70,80,90,100,106,120,140,158,200,211}:
            raise InvalidJob(f"{name}: invalid CAD lineweight")
        if details.get("linetype", "CONTINUOUS").upper() not in {"CONTINUOUS", "CENTER", "DASHED"}:
            raise InvalidJob(f"{name}: unsupported linetype")
    nonempty(data.get("font", "Arial.ttf"), "font")
    entities = {}
    for entity in data["entities"]:
        key = nonempty(entity["id"], "entity id")
        if len(key.encode("utf8")) > 200:
            raise InvalidJob(f"{key}: identifier too long for XDATA")
        if key in entities or entity["type"] not in KINDS or entity["layer"] not in layers:
            raise InvalidJob(f"{key}: duplicate ID, invalid entity type or unknown layer")
        nonempty(entity["source"], f"{key}.source")
        entities[key] = entity
        kind = entity["type"]
        if kind in {"line", "linear_dimension"}:
            a, b = (point(entity[k], f"{key}.{k}") for k in ("start", "end"))
            if math.dist(a,b) <= tolerance:
                raise InvalidJob(f"{key}: coincident endpoints")
            if kind == "linear_dimension":
                point(entity["base"], f"{key}.base")
                number(entity.get("angle",0), f"{key}.angle")
                number(entity["expected"], f"{key}.expected", 0)
        elif kind in {"circle", "arc"}:
            point(entity["center"], f"{key}.center")
            number(entity["radius"], f"{key}.radius", 0)
            if kind == "arc":
                a,b = (number(entity[k], f"{key}.{k}") for k in ("start_angle","end_angle"))
                if math.isclose((b-a)%360,0,abs_tol=1e-10):
                    raise InvalidJob(f"{key}: zero/full arc; use a circle for a full sweep")
        elif kind == "polyline":
            pts = [point(p,key) for p in entity["points"]]
            closed = entity.get("closed",False)
            if type(closed) is not bool or len(pts) < (3 if closed else 2):
                raise InvalidJob(f"{key}: invalid polyline")
            pairs = list(zip(pts,pts[1:])) + ([(pts[-1],pts[0])] if closed else [])
            if any(math.dist(a,b) <= tolerance for a,b in pairs):
                raise InvalidJob(f"{key}: degenerate edge or duplicate closing vertex")
            if closed and abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in pairs)) <= tolerance**2:
                raise InvalidJob(f"{key}: near-zero enclosed area")
        else:
            point(entity["insert"], key)
            nonempty(entity["text"], key)
            number(entity["height"],key,0)
    req_ids = set()
    for req in data["requirements"]:
        key = nonempty(req["id"], "requirement id")
        nonempty(req["source"], f"{key}.source")
        nonempty(req["statement"], f"{key}.statement")
        if key in req_ids or req["scope"] not in SCOPES:
            raise InvalidJob(f"{key}: duplicate requirement or invalid scope")
        req_ids.add(key)
        if any(x not in entities for x in req.get("entities",[])):
            raise InvalidJob(f"{key}: unknown entity referenced")
        if req["scope"] in {"excluded","undecided"}:
            nonempty(req.get("decision"), f"{key}.decision")
        if type(req.get("visual",False)) is not bool:
            raise InvalidJob(f"{key}.visual must be boolean")
    if not req_ids:
        raise InvalidJob("At least one requirement is required")
    if "sheet" in data:
        sheet=data["sheet"]
        width,height=point(sheet["size_mm"],"sheet.size_mm")
        margin=sheet.get("left_margin",25)
        border=sheet.get("edge_margin",10)
        number(border,"edge_margin",0)
        number(margin,"left_margin",0)
        if width-margin-border<180 or height-2*border<115:
            raise InvalidJob("Sheet usable area is too small")
        point(sheet["view_center"],"sheet.view_center")
        number(sheet["scale_denominator"],"sheet.scale_denominator",0)
    return data


def load(path: Path):
    try:
        return validate(json.loads(path.read_text(encoding="utf-8-sig")))
    except (KeyError, TypeError, AttributeError) as exc:
        raise InvalidJob(f"Invalid manifest: {exc}") from exc
