"""Native annotations shared by explicit manifests and mechanical recipes."""
import math

from .manifest import InvalidJob, number, nonempty, point


TYPES = {"hatch": "HATCH", "triangle": "SOLID", "runout": "TOLERANCE"}


def runout_content(spec):
    # Autodesk AcDbFcf uses the h glyph for circular runout and %%v separators.
    return r"{\Fgdt;h}" + f"%%v{spec['value']:g}%%v%%v{spec['datum']}%%v%%v"


def edge_endpoints(edge):
    if edge["type"] == "line":
        return tuple(edge["start"]), tuple(edge["end"])
    return tuple(tuple(c + edge["radius"]*f(math.radians(a)) for c, f in
                       zip(edge["center"], (math.cos, math.sin)))
                 for a in (edge["start_angle"], edge["end_angle"]))


def validate(spec, tol):
    name = spec["id"]
    kind = spec["type"]
    if kind == "runout":
        point(spec["insert"], name)
        number(spec["value"], name, 0)
        datum = nonempty(spec["datum"], name)
        if len(datum) != 1 or not "A" <= datum <= "Z":
            raise InvalidJob(f"{name}: datum must be one uppercase letter")
    elif kind == "triangle":
        coords = [point(p, name) for p in spec["points"]]
        if len(coords) != 3:
            raise InvalidJob(f"{name}: expected a triangle")
        a, b, c = coords
        if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])) <= tol**2:
            raise InvalidJob(f"{name}: degenerate triangle")
    else:
        if not isinstance(spec["edges"], list) or len(spec["edges"]) < 2:
            raise InvalidJob(f"{name}: hatch needs a closed sequence of edges")
        sequence = []
        for edge in spec["edges"]:
            if edge["type"] == "line":
                point(edge["start"], name)
                point(edge["end"], name)
            elif edge["type"] == "arc":
                point(edge["center"], name)
                number(edge["radius"], name, 0)
                a = number(edge["start_angle"], name)
                b = number(edge["end_angle"], name)
                if abs((b-a) % 360) < 1e-9:
                    raise InvalidJob(f"{name}: zero or full hatch arc")
            else:
                raise InvalidJob(f"{name}: unsupported hatch edge")
            pair = edge_endpoints(edge)
            if math.dist(*pair) <= tol:
                raise InvalidJob(f"{name}: degenerate hatch edge")
            sequence.append(pair)
        if any(math.dist(a[1], b[0]) > tol for a, b in zip(sequence, sequence[1:]+sequence[:1])):
            raise InvalidJob(f"{name}: open or disordered hatch boundary")
        number(spec.get("spacing_scale", 0.8), name, 0)


def draw(space, spec, attrs, paper_scale):
    kind = spec["type"]
    if kind == "triangle":
        return space.add_solid(spec["points"], dxfattribs=attrs)
    if kind == "runout":
        style = "MECH_FRAME"
        if style not in space.doc.dimstyles:
            space.doc.dimstyles.new(style, dxfattribs={"dimtxt": 3*paper_scale, "dimgap": .7*paper_scale})
        return space.new_entity("TOLERANCE", attrs | {"insert": spec["insert"],
                                "content": runout_content(spec), "dimstyle": style})
    e = space.add_hatch(dxfattribs=attrs)
    e.set_pattern_fill("ANSI31", color=256, scale=spec.get("spacing_scale", 0.8))
    boundary = e.paths.add_edge_path()
    for edge in spec["edges"]:
        if edge["type"] == "line":
            boundary.add_line(edge["start"], edge["end"])
        else:
            boundary.add_arc(edge["center"], edge["radius"], edge["start_angle"], edge["end_angle"])
    return e


def compare(spec, entity, close):
    kind = spec["type"]
    if kind == "runout":
        if not close(entity.dxf.insert, spec["insert"]) or entity.dxf.content != runout_content(spec):
            return ["runout frame content or location"]
    elif kind == "triangle":
        if any(not close(entity.dxf.get("vtx"+str(i)), p) for i, p in enumerate(spec["points"])):
            return ["triangle vertices"]
    else:
        if entity.dxf.pattern_name != "ANSI31" or entity.dxf.solid_fill or len(entity.paths.paths) != 1:
            return ["hatch pattern or loops"]
        if not close(entity.dxf.pattern_scale, spec.get("spacing_scale", .8)):
            return ["hatch pattern scale"]
        edges = getattr(entity.paths.paths[0], "edges", [])
        if len(edges) != len(spec["edges"]):
            return ["hatch edge count"]
        for a, b in zip(edges, spec["edges"]):
            if b["type"] == "arc":
                if (a.EDGE_TYPE != "ArcEdge" or not a.ccw or not close(a.center, b["center"])
                    or not close(a.radius, b["radius"]) or any(
                        abs((getattr(a, k)-b[k]+180) % 360-180) > 1e-6 for k in ("start_angle", "end_angle"))):
                    return ["hatch arc boundary"]
            elif a.EDGE_TYPE != "LineEdge" or not all(close(getattr(a, k), b[k]) for k in ("start", "end")):
                return ["hatch line boundary"]
    return []
