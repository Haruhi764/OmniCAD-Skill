"""Offline candidate regressions. No application launch or customer's data."""
import json
import os
from pathlib import Path
import subprocess
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import ezdxf

from omnicad import acceptance, capabilities as cap, cli, dxf, exchange, formal, oqa, records, supervisor
from omnicad.manifest import load
from omnicad.backend import active, ready_identity

ROOT=Path(__file__).resolve().parents[1]

def temp():
    return TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP"))


class CapabilityTests(unittest.TestCase):
    def test_native_binding_finds_exact_non_active_document(self):
        from types import SimpleNamespace

        with temp() as t:
            copy = Path(t) / "working.dxf"
            expected = SimpleNamespace(FullName=str(copy), ModelSpace=SimpleNamespace(Count=1))
            other = SimpleNamespace(FullName=str(Path(t) / "foreign.dwg"))
            app = SimpleNamespace(
                ActiveDocument=SimpleNamespace(FullName=str(copy)),  # an Open wrapper
                Documents=SimpleNamespace(Count=2, Item=[other, expected].__getitem__),
            )
            self.assertIs(active(app, copy), expected)

    def test_startup_identity_retries_busy_but_not_disconnect(self):
        class ComError(Exception):
            def __init__(self, code):
                self.hresult = code

        class App:
            class Documents:
                Count = 0

        host = cap.Host("autocad", 2023, "win32")
        with patch("omnicad.backend.session_identity", side_effect=[ComError(-2147418111), host]) as probe, \
                patch("omnicad.backend.time.sleep"):
            self.assertEqual(ready_identity(App()), host)
            self.assertEqual(probe.call_count, 2)
        with patch("omnicad.backend.session_identity", side_effect=ComError(-2147023174)) as probe:
            with self.assertRaises(ComError):
                ready_identity(App())
            self.assertEqual(probe.call_count, 1)

    def test_legacy_full_route_and_experimental_opt_in(self):
        full = cap.Host("autocad", 2023, "win32")
        lt = cap.Host("lt", 2027, "win32")
        for hosts in ([], [full], [full, lt], [full, cap.Host("autocad", 2026, "win32")]):
            host, backend = cap.publication_route(hosts, "auto", "auto", None, False, "win32")
            self.assertEqual((host.product, host.year, backend), ("autocad", None, "com"))
        with self.assertRaises(ValueError):
            cap.publication_route([lt], "auto", "auto", None, False, "win32")
        with self.assertRaisesRegex(ValueError, "Experimental LT requires"):
            cap.publication_route([lt], "exchange", "lt", 2027, False, "win32")
        self.assertEqual(cap.publication_route([lt], "exchange", "lt", 2027, True, "win32")[1], "exchange")

    def test_matrix_and_negotiation(self):
        for year in (2023,2024,2027):
            host=cap.Host("lt",year,"win32")
            self.assertFalse(host.interfaces["external_com"])
            self.assertEqual(host.interfaces["autolisp"],year>=2024)
            self.assertEqual(cap.choose([host])[1],"exchange")
            with self.assertRaises(ValueError):
                cap.choose([host],"com")
        self.assertFalse(cap.Host("lt",2027,"darwin").interfaces["autolisp"])
        self.assertEqual(cap.choose([])[1],"exchange")
        full=cap.Host("autocad",2023,"win32",executable="acad.exe")
        lt=cap.Host("lt",2027,"win32",executable="acadlt.exe")
        self.assertEqual(cap.choose([full])[1],"com")
        self.assertEqual(cap.choose([full,lt])[1],"exchange")
        self.assertEqual(cap.choose([full,lt],product="autocad")[1],"com")
        with self.assertRaises(ValueError):
            cap.choose([lt],"com",product="autocad")
        self.assertEqual(cap.identity("AutoCAD LT 2027"),"lt")
        self.assertEqual(cap.identity(r"C:\Autodesk\AutoCAD 2023\acad.exe"),"autocad")
        self.assertFalse(cap.Host("lt",2027,"win32").interfaces["native_runtime_verified"])

    def test_session_conflict_and_probe(self):
        class App:
            Name="AutoCAD"
            FullName=r"C:\Autodesk\AutoCAD LT 2027\acadlt.exe"
            Version="25"
        self.assertEqual(cap.session_identity(App()).product,"unknown")
        with temp() as t:
            f=Path(t)/"session.txt"
            f.write_text("PROGRAM=acadlt\nACADVER=26.0s (LMS Tech)\nOS=WINDOWS\n")
            host=cap.probe_session_file(f)
            self.assertEqual(host.product,"lt")
            self.assertEqual(host.year,2027)
            self.assertEqual(host.version,"26.0s (LMS Tech)")
            self.assertFalse(host.interfaces["native_runtime_verified"])

    def test_lt_cli_exchange_without_com(self):
        with temp() as t:
            root=Path(t)
            job=ROOT/"examples"/"bracket.json"
            seed=root/"sample.dxf"
            dxf.save_new(dxf.build(load(job)),seed)
            before=records.digest(seed)
            out=root/"out"
            args=cli.parser().parse_args(["publish",str(job),str(seed),str(out),
                                          "--product","lt","--year","2027","--backend","exchange","--experimental-lt"])
            # Explicitly model a requested Windows LT host on every CI runner.
            with patch("omnicad.capabilities.installed_windows", return_value=[]), \
                    patch("omnicad.capabilities.sys.platform", "win32"), \
                    patch("omnicad.supervisor.execute",side_effect=AssertionError("No COM for LT")):
                result,status=cli.run(args)
            self.assertEqual(status,2)
            self.assertEqual(result["status"],"awaiting_native")
            self.assertEqual(len(result["scripts"]),2)
            self.assertEqual(records.digest(seed),before)
            script=(out/"save-as-dwg.scr").read_text()
            self.assertIn("SEED.DXF",script)
            self.assertIn('not (findfile target)',script)
            self.assertNotIn("vlax",script)
            self.assertNotIn("SECURELOAD",script)
            self.assertEqual(exchange.verify(out)["status"],"awaiting_native")
            (out/"seed.dxf").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"changed"):
                exchange.verify(out)

    def test_lt_cli_exchange_non_windows(self):
        for platform in ("linux", "darwin"):
            with self.subTest(platform=platform), temp() as t:
                root = Path(t)
                job = ROOT / "examples" / "bracket.json"
                seed = root / "sample.dxf"
                dxf.save_new(dxf.build(load(job)), seed)
                before = records.digest(seed)
                out = root / "out"
                args = cli.parser().parse_args([
                    "publish", str(job), str(seed), str(out),
                    "--product", "lt", "--year", "2027", "--backend",
                    "exchange", "--experimental-lt"])
                with patch("omnicad.capabilities.installed_windows", return_value=[]), \
                        patch("omnicad.capabilities.sys.platform", platform), \
                        patch("omnicad.supervisor.execute", side_effect=AssertionError("No COM for LT")):
                    result, status = cli.run(args)
                self.assertEqual(status, 2)
                self.assertEqual(result["status"], "awaiting_native")
                self.assertEqual(result["scripts"], [])
                self.assertFalse(result["native_verified"])
                self.assertTrue((out / "seed.dxf").is_file())
                self.assertFalse((out / "save-as-dwg.scr").exists())
                self.assertFalse((out / "inspect-session.scr").exists())
                self.assertEqual(records.digest(seed), before)
                self.assertEqual(exchange.verify(out)["status"], "awaiting_native")

    def test_pre_lisp_manual_exchange(self):
        with temp() as t:
            root=Path(t)
            job=load(ROOT/"examples"/"bracket.json")
            seed=root/"sample.dxf"
            dxf.save_new(dxf.build(job),seed)
            result=exchange.prepare(job,seed,root/"out",cap.Host("lt",2023,"win32"))
            self.assertEqual(result["scripts"],[])


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temp()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.seed=self.root/"s.dxf"
        self.seed.write_bytes(b"seed")
        self.state=self.root/"state"
        self.shared=self.root/"shared"
        self.job={"source":str(self.seed),"destination":str(self.root/"out"),"operation":"readback"}
        self.calls=0

    def worker(self,request):
        self.calls+=1
        target=Path(request["destination"])
        target.mkdir()
        file=target/"readback.dxf"
        file.write_bytes(b"synthetic return")
        return {"readback":str(file)}

    def run_job(self,runner=None,job=None,budget=8):
        return supervisor.execute(job or self.job,self.state,10,budget,runner or self.worker,self.shared)

    def test_hash_checkpoint_and_budget(self):
        first,e=self.run_job()
        self.assertFalse(e["reused"])
        _,e=self.run_job()
        self.assertTrue(e["reused"])
        self.assertEqual(self.calls,1)
        with self.assertRaisesRegex(RuntimeError,"budget"):
            self.run_job(job=self.job|{"destination":str(self.root/"next")},budget=1)
        Path(first["readback"]).write_bytes(b"corrupt")
        with self.assertRaisesRegex(RuntimeError,"changed"):
            self.run_job()

    def test_backend_change_invalidates_reuse(self):
        self.run_job()
        with patch("omnicad.supervisor.backend_fingerprint",return_value="other code"):
            with self.assertRaises(FileExistsError):
                self.run_job()
        self.assertEqual(self.calls,1)

    def test_timeout_cross_project_circuit_and_reset(self):
        def timeout(_):
            raise subprocess.TimeoutExpired("worker",10)
        with self.assertRaisesRegex(RuntimeError,"timeout"):
            self.run_job(timeout)
        with self.assertRaisesRegex(RuntimeError,"circuit"):
            supervisor.execute(self.job|{"destination":str(self.root/"another")},
                               self.root/"other-state",10,8,self.worker,self.shared)
        self.assertEqual(self.calls,0)
        with self.assertRaises(ValueError):
            supervisor.reset_circuit(False,self.shared)
        supervisor.reset_circuit(True,self.shared)
        self.run_job(job=self.job|{"destination":str(self.root/"next")})
        self.assertEqual(self.calls,1)

    def test_invalid_artifact_opens_circuit(self):
        with self.assertRaisesRegex(RuntimeError,"out-of-scope"):
            self.run_job(lambda _: {"readback":str(self.seed)})
        self.assertTrue((self.shared/"circuit.json").exists())

    def test_lock_and_rpc_classification(self):
        self.shared.mkdir()
        with supervisor.exclusive(self.shared/"native.lock"):
            with self.assertRaisesRegex(RuntimeError,"lock"):
                self.run_job()
        class RPC(Exception):
            hresult=-2147023174
        self.assertEqual(supervisor.classify(RPC()),"disconnected")
        with self.assertRaisesRegex(RuntimeError,"disconnected"):
            self.run_job(lambda _: (_ for _ in ()).throw(RPC()))
        self.assertEqual(json.loads((self.shared/"circuit.json").read_text())["reason"],"disconnected")


class TypedAcceptanceTests(unittest.TestCase):
    def test_ordered_process_flow_and_hard_gate(self):
        with temp() as t:
            p=Path(t)/"flow.dxf"
            doc=ezdxf.new(); doc.units=4
            for layer in ("FLOW","L","E"):
                doc.layers.new(layer)
            m=doc.modelspace()
            m.add_line((10,0),(0,0),dxfattribs={"layer":"FLOW"})
            m.add_text("洗浄",dxfattribs={"layer":"L"})
            m.add_circle((0,0),2,dxfattribs={"layer":"E"})
            dxf.save_new(doc,p)
            label={"type":"TEXT","count":1,"layer":"L","field":"text","values":["洗浄"]}
            flow={"type":"LINE","count":1,"layer":"FLOW","field":"endpoints",
                  "values":[[[0,0],[10,0]]],"tolerance":0.001}
            c={"model_units":4,"roles":{"equipment":[{"layer":"E","type":"CIRCLE","count":1}],
                      "labels":[label],"sequence":[label],"flow":[flow]}}
            review={"sha256":{"dxf":records.digest(p)},"checks":{k:{"state":"passed","note":"simulated"}
                     for k in ("engineering_completeness","visual_labels","layout_and_scale")}}
            result=acceptance.evaluate(p,"food-process",c,review=review,target="dxf")
            self.assertIn("flow",result["hard_failures"])
            self.assertEqual(result["verdict"],"failed")
            flow["values"]=[[[10,0],[0,0]]]
            result=acceptance.evaluate(p,"food-process",c,target="dxf")
            self.assertEqual(result["verdict"],"pending")
            del flow["tolerance"]
            with self.assertRaisesRegex(ValueError,"explicit"):
                acceptance.evaluate(p,"food-process",c,target="dxf")

    def test_closure_and_dimension_override(self):
        doc=ezdxf.new(); doc.units=4
        m=doc.modelspace()
        poly=m.add_lwpolyline([(0,0),(1,0),(1,1)],close=False)
        r=oqa._role_values([poly],{"type":"LWPOLYLINE","field":"closed","values":[True]})
        self.assertFalse(r["values_ok"])
        dim=m.add_linear_dim(base=(0,-1),p1=(0,0),p2=(10,0),angle=0,text="12").dimension
        self.assertEqual(acceptance._check_dimensions(doc,.001)["state"],"failed")
        dim.dxf.text="<>"
        self.assertEqual(acceptance._check_dimensions(doc,.001)["state"],"passed")

    def test_formal_metadata_and_debug_layers_are_only_flagged(self):
        doc=ezdxf.new()
        doc.layers.new("DEBUG_geometry")
        doc.modelspace().add_text("AI Generated")
        checks=formal.internal_notes(doc)
        self.assertEqual(len(checks),2)
        self.assertIn("DEBUG_geometry",doc.layers)
        self.assertEqual(len(doc.modelspace()),1)
        class Reader:
            metadata={"/Author":"Codex", "/Producer":"AutoCAD"}
        self.assertEqual(formal.pdf_metadata_notes(Reader()),[{"field":"/Author","value":"Codex"}])

    @unittest.skipUnless(shutil.which("pdftoppm"),"Poppler not available")
    def test_independent_plot_checks_every_page(self):
        from pypdf import PdfWriter
        with temp() as t:
            root=Path(t)
            for name, second_width in (("a",100),("b",110)):
                w=PdfWriter()
                w.add_blank_page(width=100,height=100)
                w.add_blank_page(width=second_width,height=100)
                with (root/(name+".pdf")).open("wb") as stream:
                    w.write(stream)
            self.assertFalse(oqa.verify_print(root/"a.pdf",root/"b.pdf"))
            self.assertTrue(oqa.verify_print(root/"a.pdf",root/"a.pdf"))


if __name__=="__main__":
    unittest.main()
