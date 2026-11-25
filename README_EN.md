<p align="center"><img src="assets/omnicad-banner.svg" alt="OmniCAD — editable 2D CAD and evidence-led verification" width="100%"></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-1683b8?style=flat-square" alt="MIT"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.10%2B-1683b8?style=flat-square" alt="Python 3.10+"></a>
  <a href="SKILL.md"><img src="https://img.shields.io/badge/Agent-Codex-1683b8?style=flat-square" alt="Codex"></a>
  <a href="https://github.com/Haruhi764/OmniCAD-Skill/stargazers"><img src="https://img.shields.io/github/stars/Haruhi764/OmniCAD-Skill?style=flat-square" alt="Stars"></a>
  <a href="https://github.com/Haruhi764/OmniCAD-Skill/forks"><img src="https://img.shields.io/github/forks/Haruhi764/OmniCAD-Skill?style=flat-square" alt="Forks"></a>
</p>

<h1 align="center">OmniCAD-Skill — AI CAD Automation &amp; Automatic CAD Drawing</h1>

<p align="center"><strong>Editable engineering drawings. Verifiable results.</strong></p>

<p align="center"><a href="README.md">中文</a> · <a href="SKILL.md">Agent Skill</a> · <a href="references/v11.md">Workflow</a> · <a href="references/validation.md">Validation</a> · <a href="CHANGELOG.md">Changelog</a></p>

OmniCAD is an open-source CAD automation skill for Codex. Generate editable DXF from reviewed dimensions and drafting requirements, and publish DWG and PDF in supported AutoCAD environments.

[Quick start](#quick-start) · [Skill instructions](SKILL.md) · [Changelog](CHANGELOG.md)

## Drawing showcase

<p align="center"><img src="assets/OmniCAD-light(1).gif" alt="OmniCAD automated flange drafting showcase" width="100%"></p>

<p align="center"><sub>Actual OmniCAD-generated DXF geometry, animated replay with OQA evidence; not a live AutoCAD recording.</sub></p>

## Real drawing examples

Native AutoCAD 2023 plots from reproducible synthetic repository inputs, not concept renders.

| Transmission shaft | Boss flange |
| :---: | :---: |
| ![Shaft](examples/previews/shaft-c.png) | ![Flange](examples/previews/flange-b.png) |
| [Reproduce](examples/shaft-c.json) | [Reproduce](examples/flange-b.json) |

Other drafting experience includes industrial layouts, process diagrams and roof drainage plans. Client drawings are not public.

## Features

- Architectural and civil 2D drafting: grids, walls, openings, components and annotations.
- Mechanical drafting: stepped shafts, flanges, sections, keyways, chamfers and tolerances.
- Scoped DXF revisions, comparisons and OQA checks.
- Native DWG and PDF publication with supported Windows AutoCAD.

## Quick start

Requires Python 3.10+. Native DWG/PDF publication uses licensed Windows AutoCAD and its PDF plot configuration. PNG previews use Poppler.

```bash
git clone https://github.com/Haruhi764/OmniCAD-Skill.git
cd OmniCAD-Skill
python -m pip install ".[intake,autocad]"
omnicad mechanical examples/shaft-c.json job.json
omnicad build job.json drawing.dxf
omnicad oqa drawing.dxf --job job.json --domain mechanical --mode standard
omnicad publish job.json drawing.dxf publication --verify-native
```

Install the folder containing [SKILL.md](SKILL.md) in a supported local skill directory to use it from Codex. The [bracket manifest](examples/bracket.json) is still supported.

## Roadmap

- [x] AutoCAD 2D drafting and verification
- [ ] AutoCAD LT compatibility
- [ ] SolidWorks modeling and assemblies
- [ ] Revit BIM modeling

Planned integrations are not part of the current release. See [validation](references/validation.md) for tested scope.

## Feedback and contributions

Open an [issue](https://github.com/Haruhi764/OmniCAD-Skill/issues) with your software version and a sanitized reproduction. See the [workflow](references/v11.md) and [contribution guide](CONTRIBUTING.md). Arbitrary DWG editing, image vectorization and 3D modeling are not supported in this release. Engineering judgment requires human review.

[MIT license](LICENSE) · [Third-party provenance](references/provenance.md). Star the project if you find it useful.

---

<p align="center"><img src="assets/omnicad-logo.svg" width="48" alt="OmniCAD logo"></p>
<p align="center"><strong>OmniCAD · Draft / Verify / Deliver</strong></p>
<p align="center"><a href="CONTRIBUTING.md">Contribute</a> · <a href="https://github.com/Haruhi764/OmniCAD-Skill/issues">Report an issue</a> · <a href="https://github.com/Haruhi764/OmniCAD-Skill/releases">Releases</a></p>
