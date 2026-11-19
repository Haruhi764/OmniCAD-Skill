---
name: omnicad-skill
description: Build or revise editable 2D CAD drawings from explicit dimensions, track drawing requirements, and verify DXF or Windows AutoCAD DWG/A1 delivery. Use for CAD drawing production, evidence audits, or bounded revisions. For raster or PDF references, identify missing dimensions and build a reviewed manifest before drafting.
---

# OmniCAD

1. Separate the user's scope from third-party notes in attachments. Record each drawing, section, callout, numbering change and required delivery format in the manifest. If a full section is mentioned but scope is unclear, log it as undecided and keep the review blocked. A section marker is a separate artifact from a section view.
2. Inventory sources with `omnicad intake`. Reuse its local hash cache. Confirm PDF dimensions and references visually, including which edges extension lines identify. Use source or derived geometry explicitly, and keep ambiguous or pixel-only dimensions out of the production geometry. See [manifest format](references/manifest.md).
3. For a new drawing, run `omnicad build`, then `omnicad audit`. For a small revision to an OmniCAD drawing, use its current fingerprint with `omnicad revise` and a fresh output directory. For existing third-party DWGs, preserve the source and use a trusted native CAD copy. Readback is available, but generic DWG editing is outside the V1 patch API.
4. Use `omnicad publish` only for a user-authorized DWG or PDF job on Windows with licensed AutoCAD. Open only a job-owned copy. Inspect rendered full sheets and targeted previews before writing visual evidence bound to the output hashes. See [native and publishing workflow](references/workflow.md).
5. Report the evidence level for geometry, text, print appearance and actual deliverables separately. At closeout, use `omnicad lesson` to retain concrete, reusable issues and fixes in a project-local ignored log.
6. Record each explicit customer change as its own required entry with the source, affected drawing, expected result and evidence from the saved revision. Keep unresolved design matters in a separate issue log. Run `omnicad formal-check` on each native DXF readback, review every hit in context, and preserve formal engineering warnings. See [closeout rules](references/workflow.md).
