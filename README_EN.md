# OmniCAD-Skill

OmniCAD is a local Codex skill and CLI for evidence-led, editable 2D CAD drafting. It links each requirement to its source, the native drawing entities, and the evidence for the delivered file.

Requires Python 3.10+. Use an isolated virtual environment. Native DWG and PDF publication requires licensed AutoCAD on Windows, its PDF plot configuration and suitable fonts. PNG previews require local Poppler.

```text
python -m pip install ".[intake,autocad]"
omnicad build examples/bracket.json sample.dxf
omnicad audit examples/bracket.json sample.dxf --report draft.json
omnicad publish examples/bracket.json sample.dxf sample-release
omnicad preview sample-release/sheet.pdf review.png
python -m unittest discover -s tests -v
```

Build and revision work without AutoCAD. Local intake inventories supported PDFs, DXFs, DWGs, DOCX files, images and UTF-8 texts and caches by content digest. Drafting requires explicit dimensions and entities in a reviewed manifest. OCR, generalized DWG editing, 3D and BIM are outside V1.

Audit includes explicit dimension measurements, layer settings, viewport fit and evidence-linked scope decisions. The COM adapter reopens a native DWG, plots its layout and exports an independent readback DXF. Visual approval is separate and bound to artifact hashes. The revision tool applies targeted changes to an OmniCAD-owned DXF with a verified backup.

The [skill entry point](SKILL.md), [manifest reference](references/manifest.md) and [native publishing workflow](references/workflow.md) describe installation and use. See [validation](references/validation.md) and [provenance](references/provenance.md) for test status and release conditions. The repository ships synthetic examples only.
