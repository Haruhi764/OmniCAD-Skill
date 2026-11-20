# Changelog

## 1.1.0

- Added reviewed stepped-shaft and boss-flange recipes, editable section hatching, diameter/fit dimensions, native circular-runout frames, and vector datum and surface-texture marks.
- Added light, standard and full OQA with explicit discipline expectations, artifact-bound AutoCAD edit/replot evidence and distinct manual review states.
- Added intent and same-lineage DXF scope reports. Bounded revisions now verify their actual changed identities before writing.
- Added strict PDF validation and a narrowly scoped repair for duplicate AutoCAD Catalog PageMode entries. Retain the raw plot and preserve the existing page streams.
- Added synthetic A/B/C examples, actual plot previews, bilingual documentation and regression cases.

## 1.0.0

- Flag internal review notes in native DXF readbacks and include the scan in the manifest release gate.
- Document how to trace each customer change and keep unresolved issues separate from formal drawings.

- Added provenance-tagged native 2D DXF generation and geometry QA.
- Added tracked scope decisions, artifact fingerprints and separate visual confirmation.
- Added local intake cache, bounded revision operations and verified restore.
- Added a Windows AutoCAD COM adapter for DWG, full-bleed PDF and native DXF readback.
- Added a synthetic part example, offline tests, a CAD smoke script and a native regression checker.
