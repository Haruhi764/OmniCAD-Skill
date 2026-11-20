"""Geometry recipes. All physical dimensions come from the reviewed input."""
from math import atan2, cos, degrees, dist, hypot, radians, sin, sqrt

from .manifest import InvalidJob, number, nonempty, validate


LAYERS = {
    "OUTLINE": {"weight": 50}, "DIM": {"weight": 18}, "CENTER": {"weight": 13, "linetype": "CENTER"},
    "HIDDEN": {"weight": 13, "linetype": "DASHED"}, "HATCH": {"weight": 13},
    "THREAD": {"weight": 18}, "CUT": {"weight": 35}, "SYMBOLS": {"weight": 25}, "LABEL": {"weight": 18},
}


class Recipe:
    def __init__(self, data):
        self.data = data
        self.entities = []
        self.source = nonempty(data["source"], "source")

    def add(self, name, kind, layer, **atts):
        self.entities.append({"id": name, "type": kind, "layer": layer, "source": self.source, **atts})

    def line(self, name, a, b, layer="OUTLINE"):
        if dist(a, b) > .001:
            self.add(name, "line", layer, start=a, end=b)

    def poly(self, name, coords, layer="OUTLINE", closed=False):
        self.add(name, "polyline", layer, points=coords, closed=closed)

    def arc(self, name, center, radius, start, end, layer="OUTLINE"):
        self.add(name, "arc", layer, center=center, radius=radius, start_angle=start, end_angle=end)

    def circle(self, name, center, radius, layer="OUTLINE"):
        self.add(name, "circle", layer, center=center, radius=radius)

    def text(self, name, label, at, layer="LABEL", size=2.55):
        self.add(name, "text", layer, text=label, insert=at, height=size*self.data.get("scale", 1))

    def dim(self, name, a, b, position, vertical=False, fit=None):
        axis = int(vertical)
        notation = {"display": "%%c<>" + (" "+fit if fit else "")} if name.startswith("diameter") else {}
        self.add(name, "linear_dimension", "DIM", start=a, end=b, base=position,
                 angle=90 if vertical else 0, expected=abs(a[axis]-b[axis]), **notation)

    def arrow(self, name, tip, tail, layer):
        dx, dy = tail[0]-tip[0], tail[1]-tip[1]
        length = hypot(dx, dy)
        dx, dy = dx/length, dy/length
        x, y = tip[0]+2.4*dx, tip[1]+2.4*dy
        self.add(name, "triangle", layer, points=[tip, (x-.55*dy,y+.55*dx), (x+.55*dy,y-.55*dx)])

    def leader(self, name, tip, knee, end, label=None, at=None, layer="DIM"):
        self.poly(name, [tip, knee, end], layer)
        self.arrow(name+"-tip", tip, knee, layer)
        if label:
            self.text(name+"-note", label, at or (knee[0]+.5,knee[1]+1.2), layer)

    def hatch(self, name, edges):
        self.add(name, "hatch", "HATCH", edges=edges)

    def job(self, center):
        data = self.data
        sheet = {"size_mm": [420, 297], "left_margin": 13, "edge_margin": 10,
                 "view_center": data.get("view_center", center), "scale_denominator": data.get("scale",1)}
        req = {"id": "G1", "source": self.source, "statement": "Reviewed part and drawing annotations",
               "scope": "required", "visual": True, "entities": [e["id"] for e in self.entities]}
        return validate({"version": 1, "units": "mm", "title": data["title"], "drawing_id": data["drawing_id"],
                         "font": data.get("font", "Arial.ttf"), "layers": LAYERS, "sheet": sheet,
                         "required_formats": data.get("required_formats", ["dxf"]),
                         "entities": self.entities, "requirements": [req]})


def lines(vertices):
    return [{"type": "line", "start": a, "end": b} for a, b in zip(vertices, vertices[1:])]


def _surface(job, name, at, value):
    x, y = at
    value = number(value, name, 0)
    job.poly(name+"-mark", [(x-2,y+3.46), at, (x+4.6,y+7.97),(x+19,y+7.97)], "SYMBOLS")
    job.line(name+"-bar", (x-2,y+3.46), (x+2,y+3.46), "SYMBOLS")
    job.text(name, f"Ra {value:g}", (x+5,y+9.25), "SYMBOLS")


def _datum(job, x, r, datum):
    y = -r
    job.arrow("datum-tip", (x,y), (x,y-4), "SYMBOLS")
    job.line("datum-stem", (x,y-2.4), (x,y-10), "SYMBOLS")
    job.poly("datum-box", [(x-3.6,y-10),(x+3.6,y-10),(x+3.6,y-17),(x-3.6,y-17)],
             "SYMBOLS", True)
    job.text("datum-letter", datum, (x-1.0,y-15.1), "SYMBOLS", 3)


def _cut(job, name, tip, tail, label, at):
    job.line(name, tail, tip, "CUT")
    job.arrow(name+"-arrow", tip, tail, "CUT")
    job.text(name+"-label", label, at, "CUT")


def _slot_section(job, x, y, radius, half_width, floor, chord, name):
    angle = degrees(atan2(chord, half_width))
    start, end = 180-angle, 360+angle
    right = (x+half_width,y+chord)
    left = (x-half_width,y+chord)
    a, b = (x-half_width,y+floor), (x+half_width,y+floor)
    vertices = [right, b, a, left]
    job.arc(name+"-arc",(x,y),radius,start,end)
    job.poly(name+"-slot", list(reversed(vertices)))
    job.hatch(name+"-hatch", [{"type":"arc","center":(x,y),"radius":radius,
                               "start_angle":start,"end_angle":end}, *lines(vertices)])
    job.arc(name+"-crown",(x,y),radius,angle,180-angle,"HIDDEN")
    job.line(name+"-axis-x",(x-radius-4,y),(x+radius+4,y),"CENTER")
    job.line(name+"-axis-y",(x,y-radius-4),(x,y+radius+1),"CENTER")
    job.dim("slot-width",a,b,(x,y+radius+9))
    job.dim("slot-depth",b,(x,y+radius),(x+radius+9,y),True)
    job.text(name+"-caption","K-K",(x-3,y-radius-10))


def _shaft(data):
    j = Recipe(data)
    lands = data["lands"]
    if not isinstance(lands, list) or not 2 <= len(lands) <= 12:
        raise InvalidJob("Supply two to twelve shaft lands")
    radii = [number(v["diameter"], "land diameter", 0)/2 for v in lands]
    lengths = [number(v["length"], "land length", 0) for v in lands]
    x = [0.]
    for size in lengths:
        x.append(x[-1]+size)
    length = x[-1]
    max_r = max(radii)
    if "total_length" in data and abs(number(data["total_length"], "total_length", 0)-length)>.001:
        raise InvalidJob("Shaft length does not match the supplied axial chain")
    for a,b in zip(radii,radii[1:]):
        if abs(a-b)<.011:
            raise InvalidJob("Adjacent lands require distinct diameters")

    # A fillet is placed in the smaller land at each explicitly listed shoulder.
    fillets = {}
    lo, hi = x[:-1].copy(), x[1:].copy()
    for spec in data.get("fillets", []):
        i = spec["after"]
        r = number(spec["radius"], "fillet radius", 0)
        if type(i) is not int or i in fillets or not 1 <= i < len(lands) or r >= abs(radii[i]-radii[i-1]):
            raise InvalidJob("Fillet shoulder index, duplication or clearance")
        fillets[i] = r
        if radii[i-1] < radii[i]:
            hi[i-1] -= r
        else:
            lo[i] += r

    chamfers = data.get("chamfers", {})
    c_left = number(chamfers["left"], "left chamfer", 0) if "left" in chamfers else 0
    c_right = number(chamfers["right"], "right chamfer", 0) if "right" in chamfers else 0
    end_radius = radii[0]
    thread_stop = 0
    thread = data.get("thread")
    if thread is not None:
        end_radius = number(thread["diameter"], "major diameter", 0)/2
        pitch = number(thread["pitch"], "pitch", 0)
        thread_stop = number(thread["length"], "thread length", 0)
        if end_radius > radii[0] or not c_left < thread_stop < hi[0] or 1.226869*pitch >= 2*end_radius:
            raise InvalidJob("Thread interferes with the left land or its chamfer")
    lo[0] = max(c_left,thread_stop)
    hi[-1] -= c_right
    if min(end_radius-c_left, radii[-1]-c_right, *(b-a for a,b in zip(lo,hi))) <= .01:
        raise InvalidJob("A chamfer, thread or fillet consumes its land")

    slot = data.get("keyway")
    if slot is not None:
        i = slot["land"]
        if type(i) is not int or not 1 <= i <= len(lands) or slot.get("ends") not in (None, "flat"):
            raise InvalidJob("Keyway land or end-form convention")
        i -= 1
        u = number(slot["start"], "keyway start")
        stop = u + number(slot["length"], "keyway length", 0)
        half = number(slot["width"], "keyway width", 0)/2
        dep = number(slot["depth"], "keyway depth", 0)
        r_slot = radii[i]
        if not lo[i] < u < stop < hi[i] or half >= r_slot or dep >= r_slot:
            raise InvalidJob("Keyway interferes with a shoulder, chamfer or thread")
        floor = r_slot-dep
        chord = sqrt(r_slot**2-half**2)
        if floor >= chord:
            raise InvalidJob("Keyway depth does not expose both slot walls")

    for sign in (-1,1):
        for n, r in enumerate(radii):
            left, right = lo[n], hi[n]
            if slot is not None and sign==1 and n==i:
                j.poly("shaft-slot-profile", [(left,r),(u,r),(u,chord),(stop,chord),(stop,r),(right,r)])
                j.poly("shaft-slot-bottom", [(u,chord),(u,floor),(stop,floor),(stop,chord)])
            else:
                j.line(f"land-{n+1}-{sign}", (left,sign*r), (right,sign*r))
        for n in range(1,len(lands)):
            before, after = radii[n-1:n+1]
            r = fillets.get(n,0.)
            small, big = sorted((before,after))
            station = x[n]
            j.line(f"shoulder-edge-{n}-{sign}",(station,sign*(small+r)),(station,sign*big))
            if r:
                up = before < after
                if up:
                    angles = (270,360) if sign==1 else (0,90)
                else:
                    angles = (180,270) if sign==1 else (90,180)
                j.arc(f"fillet-{n}-{sign}",(station-r if up else station+r,sign*(small+r)),r,*angles)
        j.line(f"chamfer-left-{sign}",(0,sign*(end_radius-c_left)),(c_left,sign*end_radius))
        j.line(f"chamfer-right-{sign}",(length-c_right,sign*radii[-1]),(length,sign*(radii[-1]-c_right)))
        if thread is not None:
            root = end_radius - .6134345*pitch
            start = max(0.,root-(end_radius-c_left))
            j.line(f"thread-major-{sign}",(c_left,sign*end_radius),(thread_stop,sign*end_radius))
            j.line(f"thread-minor-{sign}",(start,sign*root),(thread_stop,sign*root),"THREAD")
            j.line(f"thread-step-{sign}",(thread_stop,sign*root),(thread_stop,sign*radii[0]))
    if c_right:
        j.line("chamfer-rim-right",(length-c_right,-radii[-1]),(length-c_right,radii[-1]))
    for n, pos in enumerate(x):
        r = ((end_radius-c_left) if n==0 else (radii[-1]-c_right) if n==len(lands)
             else min(radii[n-1:n+1])+fillets.get(n,0))
        j.line(f"station-{n}",(pos,-r),(pos,r))
    ys = max_r+33
    for n,(a,b) in enumerate(zip(x,x[1:])):
        j.dim(f"length-{n+1}",(a,max(radii[max(0,n-1):n+1])),(b,max(radii[n:n+2])),(a,ys))
    j.dim("length-total",(0,end_radius),(length,radii[-1]),(0,ys+16))
    previous = -8.
    positions = []
    for n, (a,b,r) in enumerate(zip(lo,hi,radii)):
        center = (a+b)/2
        if slot is not None and n==i:
            center = (a+u)/2 if (u-a)>=(b-stop) else (stop+b)/2
        positions.append(center)
        j.dim(f"diameter-{n+1}",(center,-r),(center,r),(center,0),True,lands[n].get("fit"))
        if previous<center-6.2:
            j.line(f"axis-{n}",(previous,0),(center-6.2,0),"CENTER")
        previous = center+.9
    j.line("axis-right",(previous,0),(length+8,0),"CENTER")
    if thread is not None:
        j.dim("thread-length",(0,end_radius),(thread_stop,radii[0]),(0,max_r+14))
        j.leader("thread-note",(max(c_left,thread_stop/2),end_radius),(3,max_r+7),(-33,max_r+7),
                 f"M{2*end_radius:g}×{pitch:g}",(-32,max_r+8.2))
    for side, c, at, turn in (
        ("left",c_left,(c_left/2,-end_radius+c_left/2),-1),
        ("right",c_right,(length-c_right/2,-radii[-1]+c_right/2),1)):
        if c:
            knee = (at[0]+18*turn,-max_r-13)
            end = (knee[0]+24*turn,knee[1])
            j.leader("chamfer-"+side,at,knee,end,f"C{c:g}×45°",(min(knee[0],end[0])+1,knee[1]+1.5))
    for n,r in fillets.items():
        side = -1 if radii[n-1]<radii[n] else 1
        small = min(radii[n-1:n+1])
        tip = (x[n]+side*r*(1-sqrt(.5)), -small-r*(1-sqrt(.5)))
        knee = (x[n]+side*10,-max_r-19)
        j.leader(f"fillet-note-{n}",tip,knee,(knee[0]+side*11,knee[1]),f"R{r:g}",
                 (min(knee[0],knee[0]+side*11)+.7,knee[1]+1.6))
    if "centre_holes" in data:
        label = nonempty(data["centre_holes"]["designation"],"centre_holes.designation")
        for name,at,sign in (("left",0,-1),("right",length,1)):
            j.poly("centre-hole-"+name,[(at+3.6*sign,2.25),(at,0),(at+3.6*sign,-2.25)],"SYMBOLS")
            elbow=(at+14*sign,18)
            end=(elbow[0]+45*sign,elbow[1])
            j.leader("centre-hole-label-"+name,(at+2*sign,1.25),elbow,end,label,
                     (min(elbow[0],end[0])+.5,19.6),"SYMBOLS")
    if slot is not None:
        station=(u+stop)/2
        j.dim("key-position",(x[i],r_slot),(u,r_slot),(u,r_slot+17))
        j.dim("key-length",(u,r_slot),(stop,r_slot),(u,r_slot+17))
        for sign in (-1,1):
            y=sign*(r_slot+8)
            j.line(f"cut-station-{sign}",(station,y-3),(station,y+3),"CUT")
            _cut(j,f"key-cut-{sign}",(station,y),(station-8,y),"K",(station-12,y+1))
        cut_x = length+48 if data.get("plan") else station
        cut_y = -max_r-59
        _slot_section(j,cut_x,cut_y,r_slot,half,floor,chord,"key-section")
        if data.get("local_section"):
            px,py=station+62,-max_r-55
            wave=[(px,py),(px+40,py),(px+39,py-7),(px+40,py-12),(px+31,py-13),
                  (px+21,py-12),(px+12,py-13),(px+1,py-12),(px+2,py-6),(px,py)]
            j.line("local-slot-floor",wave[0],wave[1])
            j.poly("local-slot-breaks",wave[1:],"HATCH")
            j.hatch("local-slot-hatch",lines(wave))
            j.line("local-slot-crown",(px,py+dep),(px+40,py+dep),"HIDDEN")
            j.text("local-slot-caption", "Slot local section",(px,py-19))
    if data.get("plan"):
        if slot is not None and slot.get("ends")!="flat":
            raise InvalidJob("Plan keyway endpoints require a confirmed supported end form")
        # Copy the main-view rotation envelope at a fixed projection offset.
        y=-2*max_r-35
        profile = [e for e in j.entities if (e["layer"]=="OUTLINE" and
                   e["id"].startswith(("land-","shoulder-edge-","station-","fillet-","chamfer-","thread-major-","thread-step-","shaft-slot-profile")))]
        for ent in profile:
            spec={k:v for k,v in ent.items() if k not in {"id","type","layer","source"}}
            def shift(p):
                return p[0],p[1]+y
            for key in ("start","end","center"):
                if key in spec:
                    spec[key]=shift(spec[key])
            if "points" in spec:
                spec["points"]=[shift(p) for p in spec["points"]]
            if ent["id"]=="shaft-slot-profile":
                spec["points"]=[spec["points"][0],spec["points"][-1]]
            j.add("plan-"+ent["id"],ent["type"],"OUTLINE",**spec)
        j.line("plan-axis",(-8,y),(length+8,y),"CENTER")
        if slot is not None:
            j.poly("plan-slot",[(u,y-half),(stop,y-half),(stop,y+half),(u,y+half)],closed=True)
        j.text("plan-label","PLAN",(length/2-4,y-max_r-8))
    if data.get("left_view"):
        if thread is not None:
            raise InvalidJob("End projection of a threaded land is outside this recipe")
        center=(length+43,0)
        if c_left:
            j.circle("left-view-chamfer",center,radii[0]-c_left)
        seen = set()
        occlusion = 0
        for n,r in enumerate(radii):
            if r not in seen:
                j.circle(f"left-view-{n}",center,r,"OUTLINE" if r>occlusion else "HIDDEN")
                seen.add(r)
            occlusion=max(occlusion,r)
        j.line("left-view-axis-x",(center[0]-max_r-4,0),(center[0]+max_r+4,0),"CENTER")
        j.line("left-view-axis-y",(center[0],-max_r-4),(center[0],max_r+4),"CENTER")
        j.text("left-view-label","LEFT VIEW",(center[0]-8,-max_r-11))
    if spec:=data.get("runout"):
        datum, actual, code = spec["datum_land"], spec["controlled_land"], spec["datum"]
        if (type(datum) is not int or type(actual) is not int or datum==actual or
                not (1<=datum<=len(lands) and 1<=actual<=len(lands))):
            raise InvalidJob("Invalid datum and controlled land references")
        _datum(j,positions[datum-1],radii[datum-1],code)
        target=positions[actual-1]+min(10.,(hi[actual-1]-positions[actual-1])*.5)
        level=-max_r-24
        j.leader("runout-leader",(target,-radii[actual-1]),(target,level),(target+18,level),layer="SYMBOLS")
        j.add("runout-frame","runout","SYMBOLS",insert=(target+18,level),value=spec["value"],datum=code)
    for n,land in enumerate(lands):
        if "ra" in land:
            start = lo[n] + min((hi[n]-lo[n])*.16,5.)
            if slot is not None and n==i and u<=start<=stop:
                raise InvalidJob("Surface marking requires a confirmed land outside the keyway")
            _surface(j,f"finish-{n+1}",(start,radii[n]),land["ra"])
    if "general_ra" in data:
        y=-max_r-82
        j.text("general-finish-label","Other machined surfaces",(-30,y+1))
        _surface(j,"general-finish",(12,y),data["general_ra"])
    if "material" in data:
        j.text("material",nonempty(data["material"],"material"),(-30,-max_r-94))
    return j.job((length/2+(27 if data.get("plan") or data.get("left_view") else 0), -max_r/2-13))


def _flange(data):
    j=Recipe(data)
    r=number(data["diameter"],"base diameter",0)/2
    t=number(data["thickness"],"base thickness",0)
    upper=number(data["boss_diameter"],"boss diameter",0)/2
    h=number(data["boss_height"],"boss height",0)
    bore=number(data["bore"],"bore",0)/2
    bolt=data["bolts"]
    count=bolt["count"]
    phase=number(bolt["phase_degrees"],"bolt phase")
    pitch=number(bolt["pcd"],"bolt pitch circle",0)/2
    radius=number(bolt["diameter"],"bolt diameter",0)/2
    c=number(data["edge_chamfer"],"edge chamfer",0) if "edge_chamfer" in data else 0
    if (type(count) is not int or not 2<=count<=24 or count % 2 or
        not bore<upper<pitch-radius<pitch+radius<r-c or 2*c>=t or
        2*pitch*sin(radians(180/count))<=2*radius):
        raise InvalidJob("Flange bore, bolt pattern or chamfer interferes")
    for name,value in (("overall_height",t+h),):
        if name in data and abs(number(data[name],name,0)-value)>.001:
            raise InvalidJob("Flange height chain differs")
    for name,rr in (("base",r),("boss",upper),("bore",bore),("pitch",pitch)):
        j.circle("plan-"+name,(0,0),rr,"CENTER" if name=="pitch" else "OUTLINE")
    # The section follows the first and opposite bolt, whatever the plan phase.
    angles = [radians(phase+i*360/count) for i in range(count)]
    for i, angle in enumerate(angles):
        x,y=pitch*cos(angle),pitch*sin(angle)
        j.circle(f"bolt-{i+1}",(x,y),radius)
        j.line(f"bolt-axis-x-{i+1}",(x-radius-1.5,y),(x+radius+1.5,y),"CENTER")
        j.line(f"bolt-axis-y-{i+1}",(x,y-radius-1.5),(x,y+radius+1.5),"CENTER")
    j.line("plan-axis-x",(-r-3,0),(r+3,0),"CENTER")
    j.line("plan-axis-y",(0,-r-3),(0,r+3),"CENTER")
    j.text("flange-bolts",f"{count}×%%c{2*radius:g} THRU   %%c{2*pitch:g} PCD",(r+18,-r+7))
    j.text("flange-spacing",f"{360/count:g}° EQUAL SPACING",(r+18,-r))
    if abs(phase % 360)<1e-9:
        for s in (-1,1):
            _cut(j,f"flange-cut-{s}",(s*(r+9),0),(s*(r+9),-9),"A",(s*(r+9)-2,3))
    else:
        theta=radians(phase)
        for s in (-1,1):
            x,y=s*(r+9)*cos(theta),s*(r+9)*sin(theta)
            _cut(j,f"flange-cut-{s}",(x,y),(x+9*sin(theta),y-9*cos(theta)),"A",(x-1,y+3))
    j.text("plan-title","PLAN",(-5,-r-10))
    j.dim("diameter-base",(-r,0),(r,0),(-r,-r-15))
    by=r+8
    edge=[(-r+c,by),(r-c,by)]
    if c:
        edge.extend([(r,by+c),(r,by+t-c)])
    edge.extend([(r-c,by+t),(upper,by+t),(upper,by+t+h),(-upper,by+t+h),(-upper,by+t),(-r+c,by+t)])
    if c:
        edge.extend([(-r,by+t-c),(-r,by+c)])
    j.poly("front-outline",edge,closed=True)
    j.line("front-axis",(0,by-4),(0,by+t+h+4),"CENTER")
    for angle in sorted({round(pitch*cos(q)+s*radius,8) for q in angles for s in (-1,1)}):
        j.line(f"hidden-bolt-{angle}",(angle,by),(angle,by+t),"HIDDEN")
    for s in (-1,1):
        j.line(f"hidden-bore-{s}",(s*bore,by),(s*bore,by+t+h),"HIDDEN")
    j.text("front-title","FRONT",(-6,by+t+h+3.5))

    cx=2*r+22
    cy=-19.
    far=[(pitch+radius,0),(r-c,0)]
    if c:
        far.extend([(r,c),(r,t-c)])
    far.extend([(r-c,t),(pitch+radius,t)])
    near=[(bore,0),(pitch-radius,0),(pitch-radius,t),(upper,t),(upper,t+h),(bore,t+h)]
    for side in (-1,1):
        for n, shape in enumerate((far,near)):
            points=[(cx+side*px,cy+py) for px,py in shape]
            j.poly(f"section-metal-{side}-{n}",points,closed=True)
            j.hatch(f"section-hatch-{side}-{n}",lines(points+points[:1]))
        for i,off in enumerate((0,side*pitch)):
            if i==0 and side==1:
                continue
            j.line(f"section-axis-{side}-{i}",(cx+off,cy-4),(cx+off,cy+(t if i else t+h)+4),"CENTER")
    j.dim("diameter-bore",(cx-bore,cy+t+h),(cx+bore,cy+t+h),(cx,cy+t+h+10))
    j.dim("diameter-boss",(cx-upper,cy+t+h),(cx+upper,cy+t+h),(cx,cy+t+h+21))
    j.dim("thickness",(cx+r-c,cy),(cx+r-c,cy+t),(cx+r+8,cy),True)
    # Keep height arrows off the section and use exact reference levels.
    j.dim("boss-height",(cx+upper,cy+t),(cx+upper,cy+t+h),(cx+r+16,cy),True)
    j.dim("overall-height",(cx+r-c,cy),(cx+upper,cy+t+h),(cx+r+24,cy),True)
    j.text("section-title","A-A",(cx-3,cy-12))
    if c:
        j.leader("flange-chamfers",(cx+r-c/2,cy+t-c/2),(cx+r+7,cy+t+27),(cx+r+24,cy+t+27),
                 f"2×C{c:g}×45°",(cx+r+8,cy+t+28.4))
    return j.job((r+18,(by+t+h+6.05-r-16.6)/2))


def compile_recipe(data):
    """Convert an explicit reviewed recipe into the existing editable job schema."""
    if data.get("units") != "mm":
        raise InvalidJob("Mechanical recipe units must be mm")
    number(data.get("scale",1),"scale",0)
    for field in ("plan","left_view","local_section"):
        if field in data and type(data[field]) is not bool:
            raise InvalidJob(f"{field} must be a boolean")
    kind=data.get("kind")
    if kind == "stepped_shaft":
        return _shaft(data)
    if kind == "boss_flange":
        return _flange(data)
    raise InvalidJob("Unknown mechanical recipe")
