# Local CAD execution and publishing

Use Python 3.10 or later. The core uses ezdxf. Add the `intake` extra for PDF and images, and the `autocad` extra on Windows for native publication. AutoCAD licensing, fonts and the PDF driver stay with the host. An explicit `publish` or `read-dwg` may launch AutoCAD. Prefer a local copy of a trusted DWG, since CAD software can load file-associated content. The adapter uses identified job-owned files and does not change security settings or supply user-provided command strings to the CAD command line.

```text
omnicad build examples/bracket.json sample.dxf
omnicad audit examples/bracket.json sample.dxf --report draft.json
omnicad publish examples/bracket.json sample.dxf sample-release
omnicad preview sample-release/sheet.pdf review.png --dpi 100
omnicad audit examples/bracket.json sample-release/readback.dxf --publication sample-release/report.json --review reviewed.json --report reviewed-report.json
```

PowerShell and shell examples assume the repository as the working directory and new paths. The optional preview uses local Poppler. For a detail crop supply `--region X Y W H` in rendered page pixels. The publish operation writes its own DXF copy, DWG, PDF when a sheet is declared, native DXF readback and a machine report. AutoCAD must expose a size-matched full-bleed medium on its built-in PDF driver. An audit exit code of 2 is a QA hold and may include valid files, for example while the required visual check remains open. Code 1 indicates an operational error. Keep any files produced so you can diagnose the failure. Resume into a fresh output directory.

Check whole-sheet positioning and text at a useful scale, then inspect detail zones for overlap or crop. Page and crop dimensions and the provenance hashes are checked separately from visual appearance. Rendering verifies the digital plot, not a physical printer. Confirm proprietary fonts on the destination workstation. Audit detects DXF structural errors, expected geometry/dimensions, layer settings, duplicated lines/circles, approximate text overlap and viewport fit. It does not prove all intersections, clearances, code compliance, layout semantics or view-to-view equivalence.

For a repair, run `omnicad revise JOB DXF CHANGES NEW_DIRECTORY`. It writes the original byte-for-byte backup, revised file, updated manifest and record after in-memory checks. `omnicad restore BACKUP SHA256 NEW_DXF` verifies and restores the backup to a new filename. Ship only intended deliverables, not the audit work copies or cache. Core files are reusable for authored building plans, civil details, bridges, machine drawings and process diagrams, with domain symbols explicitly described by the job. BIM, 3D and vendor-specific pressure/structural checks are separate.

For a customer revision, give each requested change a required ID. Capture the source, exact drawing and region, expected result, and before/after properties or plot review. If the same equipment is shown on multiple drawings, check its identifiers and quantities on each sheet and record the distinct physical and logical placements. For native handle-based edits, record target handles plus the baseline hash. Bind post-save evidence to the final DWG, PDF and DXF readback hashes. Geometry with unresolved authority or installation data belongs in a separate issue log with the decision needed. Preserve formal installation warnings and engineering notes in the drawing.

Run `omnicad formal-check READBACK.dxf --report notes.json` after native save and before final release. Code 2 means a marker requires review. The core audit also blocks release when markers are found. The check scans model and layouts, insert attributes and referenced block definitions. It does not inspect xref contents, raster text or every CAD text-bearing object. Do not remove an engineering note just because it has a flagged word. Review the complete text, move internal comments into the issue log, and retain the applicable technical instruction on the sheet. Visually check the final PDF as well.
