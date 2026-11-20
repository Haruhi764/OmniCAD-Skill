"""Editable 2D drafting and QA using portable DXF entities."""
from collections import Counter
from itertools import combinations
from pathlib import Path
import math

import ezdxf
from ezdxf import bbox

from .manifest import validate
from . import annotations

APPID="OMNICAD"
LAYOUT="OMNICAD_SHEET"
VIEW_LAYER="_OMNICAD_VIEWPORT"
FONT_STYLE="OMNICAD_TEXT"
TYPE_NAMES={"line":"LINE", "circle":"CIRCLE", "arc":"ARC", "polyline":"LWPOLYLINE",
            "text":"TEXT", "linear_dimension":"DIMENSION"}


def plotsize(sheet):
    width,height=sheet["size_mm"]
    left,edge=sheet.get("left_margin",25),sheet.get("edge_margin",10)
    return left,edge,width-edge,height-edge


def sheet_geometry(sheet):
    left,bottom,right,top=plotsize(sheet)
    usable=right-left,top-bottom
    view_width,view_height=usable[0]-14,usable[1]-56
    return (left+usable[0]/2,bottom+49+view_height/2),(view_width,view_height)


def rectangle(space, corners, layer):
    x,y,a,b=corners
    return space.add_lwpolyline([(x,y),(a,y),(a,b),(x,b)],close=True,dxfattribs={"layer":layer})


def build(job):
    validate(job)
    d=ezdxf.new("R2018")
    d.header["$LASTSAVEDBY"] = ""
    d.units=4
    d.header["$PSLTSCALE"]=0
    d.header["$MEASUREMENT"]=1
    d.appids.new(APPID)
    d.styles.new(FONT_STYLE,dxfattribs={"font":job.get("font","Arial.ttf")})
    for name,pattern in (("CENTER",[30,18,-4,4,-4]),("DASHED",[18,12,-6])):
        d.linetypes.new(name,dxfattribs={"pattern":pattern})
    for name,attrs in job["layers"].items():
        d.layers.new(name,dxfattribs={"color":attrs.get("color",7),
                                     "lineweight":attrs.get("weight",25),
                                     "linetype":attrs.get("linetype","CONTINUOUS").upper()})
    m=d.modelspace()
    for spec in job["entities"]:
        a={"layer":spec["layer"]}
        kind=spec["type"]
        if kind in annotations.TYPES:
            entity=annotations.draw(m,spec,a,job.get("sheet",{}).get("scale_denominator",1))
        elif kind=="line":
            entity=m.add_line(spec["start"],spec["end"],dxfattribs=a)
        elif kind=="circle":
            entity=m.add_circle(spec["center"],spec["radius"],dxfattribs=a)
        elif kind=="arc":
            entity=m.add_arc(spec["center"],spec["radius"],spec["start_angle"],spec["end_angle"],dxfattribs=a)
        elif kind=="polyline":
            entity=m.add_lwpolyline(spec["points"],close=spec.get("closed",False),dxfattribs=a)
        elif kind=="text":
            entity=m.add_text(spec["text"],dxfattribs=a|{"height":spec["height"],"insert":spec["insert"],"style":FONT_STYLE})
        else:
            sheet=job.get("sheet",{})
            scale=sheet.get("scale_denominator",1)
            override={"dimtxt":2.5*scale,"dimasz":1.8*scale,"dimtxsty":FONT_STYLE,"dimdec":2,"dimdsep":46,"dimzin":8}
            if sheet.get("architectural_ticks",False):
                override["dimblk"]="ARCHTICK"
            if "display" in spec:
                override["dimpost"] = spec["display"]
            dim=m.add_linear_dim(base=spec["base"],p1=spec["start"],p2=spec["end"],
                                 angle=spec.get("angle",0),override=override,dxfattribs=a)
            dim.render()
            entity=dim.dimension
        entity.set_xdata(APPID,[(1000,spec["id"])])
    if sheet:=job.get("sheet"):
        layout=d.layouts.new(LAYOUT)
        layout.page_setup(size=sheet["size_mm"],margins=(0,0,0,0),units="mm",device="DWG To PDF.pc3")
        d.layers.new("_OMNICAD_FRAME",dxfattribs={"color":7,"lineweight":35})
        d.layers.new(VIEW_LAYER,dxfattribs={"plot":0})
        d.layers.get(VIEW_LAYER).off()
        left,bottom,right,top=plotsize(sheet)
        rectangle(layout,(left,bottom,right,top),"_OMNICAD_FRAME")
        rectangle(layout,(right-160,bottom,right,bottom+38),"_OMNICAD_FRAME")
        layout.add_line((right-160,bottom+15),(right,bottom+15),dxfattribs={"layer":"_OMNICAD_FRAME"})
        for s,y,h in [(job["title"],bottom+24,4), (f'{job["drawing_id"]}   1:{sheet["scale_denominator"]:g}',bottom+6,3)]:
            layout.add_text(s,dxfattribs={"insert":(right-155,y),"height":h,"style":FONT_STYLE,"layer":"_OMNICAD_FRAME"})
        center,size=sheet_geometry(sheet)
        layout.add_viewport(center=center,size=size,view_center_point=sheet["view_center"],
                            view_height=size[1]*sheet["scale_denominator"],
                            dxfattribs={"layer":VIEW_LAYER,"flags":16384})
        d.layouts.set_active_layout(LAYOUT)
        d.header["$TILEMODE"]=0
    return d


def save_new(doc,path):
    # Exclusive create preserves existing DWGs, seeds and pending revisions.
    with Path(path).open("x",encoding="utf-8",newline="") as stream:
        doc.write(stream)


def indexed(space):
    ids={}
    for e in space:
        if not e.has_xdata(APPID):
            continue
        tags=e.get_xdata(APPID)
        if len(tags)!=1 or tags[0].code!=1000 or tags[0].value in ids:
            raise ValueError("Malformed or duplicate OMNICAD entity ID")
        ids[tags[0].value]=e
    return ids


def compare(spec, entity, tol):
    def close(actual, expected):
        if isinstance(expected,(list,tuple)):
            return math.dist(tuple(actual)[:len(expected)], tuple(expected))<=tol
        return abs(actual-expected)<=tol

    if entity.dxftype()!=(TYPE_NAMES | annotations.TYPES)[spec["type"]] or entity.dxf.layer.casefold()!=spec["layer"].casefold():
        return ["type or layer"]
    if entity.dxf.color!=256 or entity.dxf.lineweight!=-1 or entity.dxf.linetype.upper()!="BYLAYER":
        return ["ByLayer properties"]
    kind=spec["type"]
    if kind in annotations.TYPES:
        return annotations.compare(spec, entity, close)
    attrs={"line":[("start","start"),("end","end")],
           "linear_dimension":[("defpoint2","start"),("defpoint3","end")],
           "circle":[("center","center"),("radius","radius")],
           "arc":[("center","center"),("radius","radius")],
           "text":[("insert","insert"),("height","height")]}.get(kind,[])
    bad=[key for attr,key in attrs if not close(entity.dxf.get(attr),spec[key])]
    if kind=="text" and (entity.dxf.text!=spec["text"] or entity.dxf.style!=FONT_STYLE):
        bad.append("text or style")
    if kind=="arc":
        for att in ("start_angle","end_angle"):
            if abs((entity.dxf.get(att)-spec[att]+180)%360-180)>1e-6:
                bad.append(att)
    if kind=="polyline":
        points=list(entity.get_points("xyb"))
        if entity.closed!=spec.get("closed",False) or len(points)!=len(spec["points"]) or any(
                not close(p,expected) or abs(p[2])>1e-9 for p,expected in zip(points,spec["points"])):
            bad.append("polyline points, bulges or closure")
    if kind=="linear_dimension":
        if not close(entity.get_measurement(),spec["expected"]) or entity.dxf.text not in ("","<>"):
            bad.append("dimension measurement or override")
        if (entity.override().get("dimpost") or "") != spec.get("display", ""):
            bad.append("dimension prefix or fit")
        if abs((entity.dxf.angle-spec.get("angle",0)+180)%360-180)>1e-6:
            bad.append("dimension angle")
    return bad


def duplicates(entities):
    # Full geometric signatures for common primitives; intentionally ignores layer.
    keys={}
    matches=[]
    for key,e in entities.items():
        if e.dxftype()=="LINE":
            signature=("LINE",*sorted((tuple(e.dxf.start),tuple(e.dxf.end))))
        elif e.dxftype()=="CIRCLE":
            signature=("CIRCLE",tuple(e.dxf.center),e.dxf.radius)
        else:
            continue
        if signature in keys:
            matches.append([keys[signature],key])
        keys[signature]=key
    return matches


def text_collisions(entities,tol):
    ext=[(k,bbox.extents([v])) for k,v in entities.items() if v.dxftype()=="TEXT"]
    return [[a,b] for (a,x),(b,y) in combinations(ext,2) if x.has_data and y.has_data and all(
        min(x.extmax[i],y.extmax[i])-max(x.extmin[i],y.extmin[i])>tol for i in range(2))]


def check_sheet(doc, job):
    sheet=job.get("sheet")
    if not sheet:
        return []
    if LAYOUT not in doc.layout_names():
        return ["missing layout"]
    p=doc.layouts.get(LAYOUT)
    frame=[e for e in p.query("LWPOLYLINE") if e.dxf.layer=="_OMNICAD_FRAME"]
    if not frame or not frame[0].closed:
        return ["missing closed frame"]
    l,b,r,t=plotsize(sheet)
    actual=set(tuple(round(v,6) for v in xy) for xy in frame[0].get_points("xy"))
    expected={tuple(round(v,6) for v in xy) for xy in [(l,b),(r,b),(r,t),(l,t)]}
    result=[] if actual==expected else ["frame margins"]
    views=[e for e in p.query("VIEWPORT") if e.dxf.layer==VIEW_LAYER]
    if len(views)!=1:
        return result+["missing or duplicate model viewport"]
    v=views[0]
    center,size=sheet_geometry(sheet)
    checks=(math.dist(tuple(v.dxf.center)[:2],center),
            math.dist((v.dxf.width,v.dxf.height),size),
            math.dist(tuple(v.dxf.view_center_point)[:2],sheet["view_center"]),
            abs(v.dxf.view_height-v.dxf.height*sheet["scale_denominator"]))
    tol=job.get("tolerance_mm",.01)
    if max(checks)>tol or doc.layers.get(VIEW_LAYER).dxf.plot:
        result.append("model viewport position, scale, or print setting")
    box=bbox.extents(doc.modelspace())
    cx,cy=sheet["view_center"]
    w,h=(x*sheet["scale_denominator"]/2 for x in size)
    if box.has_data and (box.extmin.x<cx-w-tol or box.extmax.x>cx+w+tol or
                         box.extmin.y<cy-h-tol or box.extmax.y>cy+h+tol):
        result.append("geometry outside viewport")
    return result


def audit(doc,job):
    from .formal import internal_notes

    validate(job)
    tol=job.get("tolerance_mm",.01)
    m=doc.modelspace()
    check=doc.audit()
    ids=indexed(m)
    issues={}
    for spec in job["entities"]:
        key=spec["id"]
        bad=compare(spec,ids[key],tol) if key in ids else ["missing"]
        if bad:
            issues[key]=bad
    layer_errors=[]
    for name,a in job["layers"].items():
        if name not in doc.layers:
            layer_errors.append(name)
            continue
        got=doc.layers.get(name).dxf
        if (got.color,got.lineweight,got.linetype.upper())!=(a.get("color",7),a.get("weight",25),a.get("linetype","CONTINUOUS").upper()):
            layer_errors.append(name)
    expected={entity["id"] for entity in job["entities"]}
    return {"units_mm":doc.units==4,"entity_errors":issues,"unexpected_ids":sorted(set(ids)-expected),
            "untagged_model_entities":len(m)-len(ids),"layers_bad":layer_errors,"sheet_errors":check_sheet(doc,job),
            "duplicates":duplicates(ids), "possible_text_overlaps":text_collisions(ids,tol),
            "audit_errors":len(check.errors),"audit_fixes":len(check.fixes),"internal_notes":internal_notes(doc),
            "entity_types":dict(Counter(e.dxftype() for e in m))}
