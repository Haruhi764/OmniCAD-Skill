from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import ezdxf

from omnicad import dxf, intake, records
from omnicad.cli import main
from omnicad.formal import internal_notes
from omnicad.manifest import InvalidJob,load,validate
from omnicad.paper import check_pdf

EXAMPLE=Path(__file__).parents[1]/"examples"/"bracket.json"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=os.environ.get("OMNICAD_TEST_TMP"))
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.job=load(EXAMPLE)
        self.doc=dxf.build(self.job)
        self.source=self.root/"seed.dxf"
        dxf.save_new(self.doc,self.source)

    def test_native_roundtrip(self):
        native=ezdxf.readfile(self.source)
        report=dxf.audit(native,self.job)
        self.assertTrue(records.clean(report),report)
        self.assertEqual(report["entity_types"]["DIMENSION"],1)
        self.assertEqual(dxf.indexed(native.modelspace())["description"].dxf.text,"对称孔位示例")

    def test_formal_notes_block_release_in_referenced_content(self):
        block=self.doc.blocks.new("NOTE_BLOCK")
        block.add_mtext(r"资料\P不足")
        insert=self.doc.layouts.get(dxf.LAYOUT).add_blockref("NOTE_BLOCK", (30, 30))
        insert.add_attrib("REVIEW", "位置待 确认", (30, 35))
        self.doc.blocks.new("UNUSED").add_text("标识待核")
        self.doc.modelspace().add_text("外形及安装尺寸以厂家资料为准")
        findings=internal_notes(self.doc)
        self.assertEqual({f["marker"] for f in findings}, {"资料不足", "待确认"})
        qa=dxf.audit(self.doc,self.job)
        self.assertFalse(records.clean(qa))

    def test_tampered_dimension(self):
        dim=dxf.indexed(self.doc.modelspace())["width"]
        dim.dxf.defpoint3=(180,0,0)
        dim.dxf.text="200"
        errors=dxf.audit(self.doc,self.job)["entity_errors"]
        self.assertIn("width",errors)

    def test_bad_layout_is_not_silently_scaled(self):
        job=deepcopy(self.job)
        job["sheet"]["view_center"]=[10000,10000]
        d=dxf.build(job)
        self.assertIn("geometry outside viewport",dxf.audit(d,job)["sheet_errors"])

    def test_copy_protection(self):
        before=records.digest(self.source)
        with self.assertRaises(FileExistsError):
            dxf.save_new(self.doc,self.source)
        self.assertEqual(records.digest(self.source),before)

    def test_unresolved_scope_blocks_even_without_drawn_entities(self):
        self.job["requirements"][2].update(scope="undecided",decision="Owner to confirm section sheet")
        a=dxf.audit(self.doc,self.job)
        artifacts={"dxf":records.digest(self.source)}
        r=records.trace(self.job,a,artifacts,{"Q02":{"sha256":artifacts,"note":"Reviewed"}})
        self.assertEqual(r["blocking_requirements"],["Q03"])
        self.assertFalse(r["release_ready_by_manifest"])

    def test_visual_attestation_expires_after_revision(self):
        a=dxf.audit(self.doc,self.job)
        old={"dxf":"old"}
        self.assertFalse(records.trace(self.job,a,{"dxf":"new"},{"Q02":{"sha256":old,"note":"Reviewed"}})["release_ready_by_manifest"])
        self.assertTrue(records.trace(self.job,a,old,{"Q02":{"sha256":old,"note":"Reviewed"}})["release_ready_by_manifest"])

    def test_missing_delivery_format_blocks(self):
        self.job["required_formats"]=["dxf","dwg","pdf"]
        r=records.trace(self.job,dxf.audit(self.doc,self.job),{"dxf":"x"})
        self.assertEqual(r["missing_formats"],["dwg","pdf"])

    def test_revision_and_rollback(self):
        original=records.digest(self.source)
        ops={"input_sha256":original,"operations":[{"op":"set_text","id":"description","value":"复核意见","reason":"Fixture revision"}]}
        dest=self.root/"revision"
        records.revise(self.job,self.doc,self.source,ops,dest)
        self.assertEqual(records.digest(self.source),original)
        self.assertTrue(records.clean(dxf.audit(ezdxf.readfile(dest/"revised.dxf"),load(dest/"job.json"))))
        recovered=self.root/"recovered.dxf"
        records.restore(dest/"baseline.dxf",original,recovered)
        self.assertEqual(records.digest(recovered),original)

    def test_revision_rejects_stale_fingerprint(self):
        dest=self.root/"revision"
        with self.assertRaisesRegex(ValueError,"stale"):
            records.revise(self.job,self.doc,self.source,{"input_sha256":"x","operations":[]},dest)
        self.assertFalse(dest.exists())

    def test_revision_does_not_detach_dimension_relationships(self):
        ops={"input_sha256":records.digest(self.source),"operations":[{"op":"move","id":"outline","delta":[10,0],"reason":"x"}]}
        with self.assertRaisesRegex(ValueError,"remapping"):
            records.revise(self.job,self.doc,self.source,ops,self.root/"revision")

    def test_invalid_closed_boundary(self):
        self.job["entities"][0]["points"]=[[0,0],[1,0],[2,0]]
        with self.assertRaises(InvalidJob):
            validate(self.job)

    def test_retains_duplicate_and_overlap_warnings(self):
        copy=deepcopy(self.job["entities"][1])
        copy["id"]="hole-duplicate"
        self.job["entities"].append(copy)
        copy=deepcopy(self.job["entities"][5])
        copy["id"]="note-duplicate"
        self.job["entities"].append(copy)
        report=dxf.audit(dxf.build(self.job),self.job)
        self.assertEqual(report["duplicates"],[["hole-left","hole-duplicate"]])
        self.assertEqual(report["possible_text_overlaps"],[["description","note-duplicate"]])

    def test_intake_cache_is_keyed_by_file_and_format(self):
        a=self.root/"brief.txt"
        a.write_text("Section requested",encoding="utf-8")
        store=self.root/"cache"
        self.assertFalse(intake.inspect(a,store)["cache_hit"])
        self.assertTrue(intake.inspect(a,store)["cache_hit"])
        a.write_text("Conflicting brief",encoding="utf-8")
        self.assertFalse(intake.inspect(a,store)["cache_hit"])

    def test_docx_table_text_extracted_locally(self):
        p=self.root/"memo.docx"
        with ZipFile(p,"w") as z:
            z.writestr("word/document.xml",'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>40 m</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        self.assertEqual(intake.inspect_source(p,".docx")["paragraphs"],["40 m"])

    def test_pdf_crop_is_part_of_qa(self):
        try:
            from pypdf import PdfWriter
        except ImportError:
            self.skipTest("PDF QA extra not present")
        p=self.root/"sheet.pdf"
        w=PdfWriter()
        page=w.add_blank_page(width=841/25.4*72,height=594/25.4*72)
        page.cropbox.upper_right=(page.mediabox.width-10,page.mediabox.height)
        w.write(p)
        self.assertFalse(check_pdf(p,self.job)["paper_and_crop_ok"])

    def test_cli_artifacts_are_local_and_trace_is_blocking(self):
        output=self.root/"out.dxf"
        report=self.root/"report.json"
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["build",str(EXAMPLE),str(output)]),0)
            self.assertEqual(main(["audit",str(EXAMPLE),str(output),"--report",str(report)]),2)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["trace"]["blocking_requirements"],["Q02"])


if __name__=="__main__":
    unittest.main()
