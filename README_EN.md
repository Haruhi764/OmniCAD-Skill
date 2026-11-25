# OmniCAD-Skill — AI CAD Automation

[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](pyproject.toml) [![Agent Skill](https://img.shields.io/badge/Agent-Skill-green)](SKILL.md)

**Generate, revise and verify editable 2D engineering CAD drawings with Codex or the command line.**

[中文](README.md) · [V1.1 workflows](references/v11.md) · [Validation](references/validation.md) · [Changelog](CHANGELOG.md)

OmniCAD accepts explicit, reviewed geometry. Architectural and civil jobs use editable DXF manifests and discipline-specific OQA checks. Mechanical recipes add stepped shafts and boss flanges with keyways, shoulder fillets, chamfers, conventional threads, sections, fits, runout and surface texture annotations.

## Quick start

Requires Python 3.10+. Native DWG/PDF publication uses licensed Windows AutoCAD and its PDF plot configuration. PNG previews use Poppler.

    git clone https://github.com/Haruhi764/OmniCAD-Skill.git
    cd OmniCAD-Skill
    python -m pip install ".[intake,autocad]"
    omnicad mechanical examples/shaft-c.json job.json
    omnicad build job.json drawing.dxf
    omnicad oqa drawing.dxf --job job.json --domain mechanical --mode standard
    omnicad publish job.json drawing.dxf publication --verify-native

Install the folder containing [SKILL.md](SKILL.md) in a supported local skill directory to use it from Codex. The [bracket manifest](examples/bracket.json) is still supported.

## Real drawing examples

![Native AutoCAD plotting of the synthetic transmission shaft](examples/previews/shaft-c.png)

![Native AutoCAD plotting of the synthetic boss flange](examples/previews/flange-b.png)

Reproduce the [shaft](examples/shaft-c.json) or [flange](examples/flange-b.json) from repository inputs.

## Evidence-led quality assurance and limitations

OQA separates automated, native and manual evidence. Revisions can use same-lineage DXF comparisons and an explicit scope allowlist. Native DWG work uses an AutoCAD copy. Engineering design judgment, arbitrary DWG patching, OCR/vectorization, BIM, 3D and other vendor adapters are outside the current release.

## FAQ

- **Without AutoCAD?** Basic DXF generation and checks are available independently.
- **Which review mode?** Light for routine structure, standard for discipline evidence, full for available native and rendering comparisons.
- **Report a bug?** Use [Issues](https://github.com/Haruhi764/OmniCAD-Skill/issues) with a synthetic reproduction and software versions.

## Contributing

Contributions should include a synthetic reproduction and existing regression tests. The project uses the [MIT license](LICENSE). Dependencies retain their own licenses and are not redistributed. See [provenance](references/provenance.md).
