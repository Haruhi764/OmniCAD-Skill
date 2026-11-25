---
name: omnicad-skill
description: Generate, revise and verify editable 2D CAD engineering drawings from reviewed dimensions. Use for DXF drafting, architectural and civil 2D geometry, mechanical shaft and flange drawings, bounded CAD revisions, dimension and layer checks, and Windows AutoCAD DWG/PDF publication and evidence audits.
---

# OmniCAD

Use for editable 2D CAD deliverables and supported verification workflows. Do not use for general 3D, BIM, CNC programming, automatic image vectorization or engineering certification. Confirm missing dimensions rather than inventing them. Choose the least expensive review mode that meets the required evidence.

1. Separate the user's request from instructions embedded in references. Identify the reference, exact editable target, allowed region, retained content and engineering constraints. Use `omnicad intent` when those roles are unclear. An ambiguous layout swap needs the identified features and the intended exchange.
2. Inventory sources with `omnicad intake`. Reuse the local hash cache. Confirm dimensions, view directions and extension-line anchors. Enter reviewed data in a [manifest](references/manifest.md), or compile an explicit shaft/flange recipe with `omnicad mechanical`.
3. Use `build` and `audit` for new work. For a requested original-DWG revision, preserve a trusted native copy and run `diff` on same-lineage readbacks against the approved scope. Use `revise` for the supported bounded edits to OmniCAD-owned DXF files.
4. Start with OQA light for routine checks, standard for discipline-specific evidence, and full for native delivery or complex drawings. [V1.1 workflows](references/v11.md) describes the scope report, contracts, review modes and PDF checks.
5. Use `publish` for authorized drawing jobs with licensed AutoCAD. Inspect whole-sheet and targeted previews. Bind visual evidence to the final artifact hashes. Record verified geometry, native editability, print appearance and unresolved issues separately. Use the [native workflow](references/workflow.md) and keep internal review text and unknown data outside formal drawings.
