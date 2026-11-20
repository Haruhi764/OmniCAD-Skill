# Validation and case-study findings

## V1.1 regression

| Area | Actual evidence | Scope |
|---|---|---|
| Offline | 27 unittest cases pass locally on Windows/Python 3.12. Tests include all V1.0 cases plus A/B/C geometry, malformed input, stale evidence, scope changes, architecture/civil role checks and strict PDF repair. | Linux and additional Python versions are covered by the repository CI matrix. |
| Native | AutoCAD 2023 reopened the existing synthetic bracket and three mechanical recipe outputs. A/B/C native samples were selected, moved or edited, and restored. The readback geometry audit passed and the second plot matched the first page visually and by render. | Other CAD releases and physical printing remain unverified. |
| PDF | The original C plot reproduced the duplicate Catalog PageMode failure. Normalized copies passed strict parsing, retained vector pages and rendered identically to the raw driver outputs. | The first viewer mode is retained. Other PDF defects need review. |
| Architecture and civil | A prior architectural DWG readback was checked locally without editing it. Synthetic wall/opening/axis and elevation/section contracts ran against editable DXF entities. | Engineering completeness, commercial civil commands and arbitrary legacy edits remain outside this evidence. |
| OQA | The native publication audit used exact artifact hashes. The workflow keeps source scope, confirmed visual evidence and unverified engineering questions separate. | Reports count covered checks. No independent grade or token savings estimate is claimed. |

## V1.0 local evidence

| Level | Evidence |
|---|---|
| Implemented | Local intake/cache, traceability, 2D DXF, layout and roundtrip audit, bounded revision, backup/restore, lesson log and Windows ActiveX publication |
| Offline tests | Unit and integration cases cover native DXF, Unicode, fabricated dimension text, wrong viewport, duplicate geometry, text overlap, stale baseline, scope conflicts, cache changes and PDF CropBox |
| Actual AutoCAD | AutoCAD 2023, Windows, Python 3.12. A synthetic plate saved as DWG, reopened read/write with six model entities, plotted as a single A1 landscape sheet and exported native DXF. Entity, geometry and layout audit reported zero errors/fixes. The resulting PDF rendered with visible Chinese text, dimension, centerline and title block |
| Local legacy regression | Read-only checks on two private CAD exports matched their recorded geometry counts and A1 paper and crop bounds. The regression inputs are kept outside the repository |
| Not independently verified here | Remote GitHub Actions, other AutoCAD versions, alternate CAD brands, physical printing, IFC/BIM applications, OCR/automatic vectorization, arbitrary legacy drawing edits |

AutoCAD's tested driver produced a PDF that pypdf read with a nonfatal duplicate PageMode dictionary warning. Poppler also read and rendered it. The page/crop verification does not certify every PDF structure or plot driver.

## Lessons turned into code

- A teaching drawing brief asked for a defined number of delivered sheets. A review note discussed both enlarged scope and a concrete change to section markers. Treating these as a single item hid the unresolved scope. The eventual user confirmation covered the marker work. The earlier absence of complete section sheets was a scope boundary, not proof that marker work failed. The requirement ledger now keeps each separate sheet, marker and explicit scope decision distinct, and a unit test verifies an undecided required item blocks release.
- Geometry checks need to bind expected coordinates and actual measurement, not just label text. Regression checks detect a changed native dimension even if its text is overridden to the expected number.
- Native CAD document objects can become stale after SaveAs or closing the last document. The Windows adapter reacquires the exact file and maintains a job-owned open work document during reopening. It sends no generic command text and never closes a user-owned drawing.
- A changed drawing can invalidate prior visual review without invalidating every other observation. Publication and review records bind their artifact digests. Use a single whole-sheet and one focused render where sufficient. Local source caches avoid repeated extraction and compact output avoids sending document content on every run. No token savings percentage was measured.
- The original CAD documents contained incomplete data and cross-document conflicts. Example and tests are fully synthetic so the release can be reviewed without reproducing private drawings. Unit-check rules should be updated only after a failure is reproduced or a new invariant is independently demonstrated.

Run local tests with `python -m unittest discover -s tests -v`. If the system temp directory is restricted, point `OMNICAD_TEST_TMP` at an existing writable test directory. Native smoke testing is opt-in with `python scripts/autocad_smoke.py NEW_OUTPUT_DIRECTORY`. Update the changelog and keep a prior tree or tag before changing rules.
