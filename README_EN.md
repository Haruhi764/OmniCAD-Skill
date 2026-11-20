# OmniCAD-Skill

Editable 2D CAD drafting and evidence-led verification for local Codex and CLI workflows.

[中文](README.md) · [V1.1 workflows](references/v11.md) · [Validation](references/validation.md) · [Changelog](CHANGELOG.md)

OmniCAD accepts explicit, reviewed geometry. Architectural and civil jobs use editable DXF manifests and discipline-specific OQA checks. Mechanical recipes add stepped shafts and boss flanges with keyways, shoulder fillets, chamfers, conventional threads, sections, fits, runout and surface texture annotations.

Requires Python 3.10+. Native DWG/PDF publication uses licensed Windows AutoCAD and its PDF plot configuration. PNG previews use Poppler.

    python -m pip install ".[intake,autocad]"
    omnicad mechanical examples/shaft-c.json job.json
    omnicad build job.json drawing.dxf
    omnicad oqa drawing.dxf --job job.json --domain mechanical --mode standard
    omnicad publish job.json drawing.dxf publication --verify-native

Install the folder containing [SKILL.md](SKILL.md) in a supported local skill directory to use it from Codex. The [bracket manifest](examples/bracket.json) is still supported.

![Native AutoCAD plotting of the synthetic transmission shaft](examples/previews/shaft-c.png)

OQA separates automated, native and manual evidence. Revisions can use same-lineage DXF comparisons and an explicit scope allowlist. Native DWG work uses an AutoCAD copy. Engineering design judgment, arbitrary DWG patching, OCR/vectorization, BIM, 3D and other vendor adapters are outside the current release.

Contributions should include a synthetic reproduction and existing regression tests. The project uses the [MIT license](LICENSE). Dependencies retain their own licenses and are not redistributed. See [provenance](references/provenance.md).
