from io import BytesIO
import json
from math import atan2, degrees, hypot
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import ezdxf

from omnicad import dxf, intent, mechanical, oqa, records
from omnicad.annotations import runout_content
from omnicad.manifest import InvalidJob

ROOT = Path(__file__).resolve().parents[1]


def recipe(name):
    return json.loads((ROOT/"examples"/(name+".json")).read_text())


def tagged(document):
    return dxf.indexed(document.modelspace())


class Mechanics(unittest.TestCase):
    def check_sample(self, name):
        manifest = mechanical.compile_recipe(recipe(name))
        doc = dxf.build(manifest)
        self.assertTrue(records.clean(dxf.audit(doc, manifest)))
        return doc,manifest

    def test_original_shaft_measurements_and_sections(self):
        d,_=self.check_sample("shaft-a")
        els=tagged(d)
        self.assertEqual([els[f"station-{i}"].dxf.start.x for i in range(4)],[0,40,130,180])
        self.assertEqual([els[f"diameter-{i}"].get_measurement() for i in (1,2,3)],[25,35,20])
        self.assertEqual(els["length-total"].get_measurement(),180)
        self.assertEqual(els["slot-width"].get_measurement(),10)
        self.assertEqual(els["slot-depth"].get_measurement(),5)
        self.assertEqual(els["key-length"].get_measurement(),50)
        self.assertAlmostEqual(els["fillet-1-1"].dxf.radius,1)
        self.assertEqual([(p[0]) for p in els["plan-slot"].get_points("xy")],[60,110,110,60])

    def test_flange_holes_and_cut_not_shading_voids(self):
        d,_=self.check_sample("flange-b")
        els=tagged(d)
        bolts=[els[f"bolt-{i}"] for i in range(1,7)]
        for i,e in enumerate(bolts):
            x,y,_=e.dxf.center
            self.assertAlmostEqual(hypot(x,y),60)
            self.assertAlmostEqual(degrees(atan2(y,x)) % 360,i*60)
            self.assertEqual(e.dxf.radius,6)
        self.assertEqual(els["diameter-bore"].get_measurement(),50)
        self.assertEqual(els["overall-height"].get_measurement(),30)
        self.assertEqual(len(d.modelspace().query("HATCH")),4)
        section_x=els["diameter-bore"].dxf.defpoint2.x+25
        for i in range(2):
            for s in (-1,1):
                p=els[f"section-metal-{s}-{i}"]
                projected=[abs(x-section_x) for x,_ in p.get_points("xy")]
                self.assertTrue(all(x<=54 if i else x>=66 for x in projected))
                self.assertGreaterEqual(min(projected),25)

    def test_complex_shaft_measurements_and_misleading_labels(self):
        d,m=self.check_sample("shaft-c")
        e=tagged(d)
        self.assertEqual([e[f"station-{i}"].dxf.start.x for i in range(6)],[0,35,80,160,205,240])
        self.assertEqual([e[f"diameter-{i}"].get_measurement() for i in range(1,6)],[25,35,45,35,25])
        self.assertEqual(e["slot-width"].get_measurement(),14)
        self.assertAlmostEqual(e["slot-depth"].get_measurement(),5.5)
        self.assertEqual(e["thread-length"].get_measurement(),20)
        self.assertEqual(e["runout-frame"].dxftype(),"TOLERANCE")
        self.assertEqual(e["runout-frame"].dxf.content,runout_content({"value":.02,"datum":"A"}))
        self.assertEqual(e["diameter-2"].override().get("dimpost"),"%%c<> h6")
        self.assertEqual(e["diameter-4"].override().get("dimpost"),"%%c<> h6")
        self.assertNotIn("plan-slot",e)
        e["diameter-4"].dxf.text="%%c35 h6"
        self.assertIn("diameter-4",dxf.audit(d,m)["entity_errors"])

    def test_infeasible_or_unspecified_features_are_rejected(self):
        cases=[("shaft-c", "total_length", 239),
               ("shaft-c", "thread", {"diameter":26,"pitch":1.5,"length":20}),
               ("shaft-c","plan",True),
               ("flange-b","bolts",{"count":5,"phase_degrees":0,"pcd":120,"diameter":12}),
               ("flange-b","bore",85)]
        for name,key,value in cases:
            bad=recipe(name)
            bad[key]=value
            with self.subTest(name=name,key=key),self.assertRaises(InvalidJob):
                mechanical.compile_recipe(bad)


class Workflow(unittest.TestCase):
    def test_intent_keeps_reference_target_and_swap_separate(self):
        plan=intent.analyze("照着这个图画",reference=["sample.pdf"])
        self.assertEqual(plan["route"],"redraw")
        plan=intent.analyze("以原始DWG为基础，只修改这里，设备和车间位置调换，其余部分保持不变",
                            ["sample.pdf"],"original.dwg",preserve=["axes"])
        self.assertEqual(plan["route"],"revise")
        self.assertTrue(plan["requires_diff"])
        self.assertEqual(len(plan["missing"]),2)
        self.assertEqual(plan["preserve"],["axes"])
        self.assertEqual(intent.analyze("只改这里")["route"],"revise")

    def test_diff_flags_unauthorized_geometry_and_shared_layer(self):
        m=mechanical.compile_recipe(recipe("shaft-c"))
        a,b=dxf.build(m),dxf.build(m)
        self.assertTrue(intent.compare_drawings(a,b,[])["scope_verified"])
        tagged(b)["finish-2"].dxf.text="Ra 1.8"
        result=intent.compare_drawings(a,b,["Model:finish-2"])
        self.assertTrue(result["scope_verified"])
        b.layers.get("OUTLINE").color=3
        result=intent.compare_drawings(a,b,["Model:finish-2"])
        self.assertEqual(result["outside_allowlist"],["layers:OUTLINE"])

    def test_architecture_and_civil_contracts_separate_real_evidence(self):
        d=ezdxf.new()
        d.units=4
        m=d.modelspace()
        for layer in ("WALL","DOOR","GRID","LEVEL","SECTION"):
            d.layers.new(layer)
        m.add_line((0,0),(1000,0),dxfattribs={"layer":"WALL"})
        m.add_line((100,0),(100,300),dxfattribs={"layer":"DOOR"})
        m.add_line((0,0),(0,900),dxfattribs={"layer":"GRID"})
        m.add_line((-60,50),(120,50),dxfattribs={"layer":"SECTION"})
        m.add_text("+0.000",dxfattribs={"layer":"LEVEL"})
        spec=lambda layer, typ="LINE": [{"type":typ,"count":1,"layer":layer}]
        with TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP")) as temp:
            path=Path(temp)/"test.dxf"
            dxf.save_new(d,path)
            a=oqa.inspect(path,"standard","architecture",contract={"walls":spec("WALL"),"openings":spec("DOOR"),"axes":spec("GRID")})
            self.assertEqual({r["check"]:r for r in a["rows"]}["openings"]["state"],"passed")
            c=oqa.inspect(path,"full","civil",contract={"elevations":[{"type":"TEXT","count":1,"layer":"LEVEL","field":"text","values":["+0.000"]}],"sections":spec("SECTION")})
            checks={r["check"]:r for r in c["rows"]}
            self.assertEqual(checks["elevations"]["state"],"passed")
            self.assertEqual(checks["dwg_reopen"]["state"],"unverified")
            self.assertEqual(checks["components"]["evidence_level"],"manual")

    def test_stale_publication(self):
        with TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP")) as temp:
            root=Path(temp)
            for n in ("readback.dxf","drawing.dwg"):
                (root/n).write_bytes(b"data")
            info={"autocad":{"dwg":str(root/"drawing.dwg"),"readback":str(root/"readback.dxf")},
                  "trace":{"artifacts_sha256":{"dxf":records.digest(root/"readback.dxf"),"dwg":records.digest(root/"drawing.dwg")}}}
            oqa.validate_publication(info,root/"readback.dxf")
            (root/"drawing.dwg").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError,"fingerprint changed"):
                oqa.validate_publication(info,root/"readback.dxf")


def make_pdf(mode_key=b"/PageMode", second=b"/UseOutlines"):
    root=(b"<< /Type /Catalog /Pages 2 0 R /PageMode /UseOC "
          + mode_key + b" " + second + b" >>")
    nodes=[root,b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
           b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] >>"]
    result=BytesIO(b"%PDF-1.4\n")
    result.seek(0,2)
    offsets=[]
    for i,node in enumerate(nodes,1):
        offsets.append(result.tell())
        result.write(f"{i} 0 obj\n".encode()+node+b"\nendobj\n")
    start=result.tell()
    result.write(b"xref\n0 4\n0000000000 65535 f \n")
    for offset in offsets:
        result.write(f"{offset:010} 00000 n \n".encode())
    result.write(b"trailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n"+str(start).encode()+b"\n%%EOF\n")
    return result.getvalue()


class PdfRegression(unittest.TestCase):
    def test_repairs_only_duplicate_catalog_entry_preserving_offsets(self):
        from pypdf.errors import PdfReadError
        from omnicad.pdfquality import repair_plot, strict_reader

        duplicate=make_pdf()
        with TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP")) as temp:
            original, fixed=(Path(temp)/name for name in ("old.pdf","new.pdf"))
            original.write_bytes(duplicate)
            with self.assertRaises(PdfReadError):
                strict_reader(duplicate)
            report=repair_plot(original,fixed)
            self.assertEqual(report,{"state":"repaired","kept":"/UseOC","removed":"/UseOutlines"})
            self.assertEqual(original.read_bytes(),duplicate)
            revised=fixed.read_bytes()
            self.assertEqual(len(revised),len(duplicate))
            self.assertEqual(len(strict_reader(revised).pages),1)
            self.assertEqual(repair_plot(fixed,Path(temp)/"other.pdf"),{"state":"unchanged"})

    def test_unsupported_duplicates_are_not_written(self):
        from omnicad.pdfquality import repair_plot

        with TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP")) as temp:
            first,second=(Path(temp)/n for n in ("old.pdf","new.pdf"))
            first.write_bytes(make_pdf(second=b"/UnexpectedMode"))
            with self.assertRaisesRegex(ValueError,"Unsupported PageMode"):
                repair_plot(first,second)
            self.assertFalse(second.exists())


if __name__=="__main__":
    unittest.main()
