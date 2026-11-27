# OmniCAD evidence index / 技术证据索引

OmniCAD-Skill is an MIT-licensed, Python-based CAD automation skill for Codex. Its scope is editable 2D DXF drafting, bounded revisions, engineering QA (OQA), and native DWG/PDF publication through supported full Windows AutoCAD. This index describes implemented workflows and links to their evidence; it is not an independent certification or a benchmark against other tools.

## Public reproducible cases / 公开案例

| Case | Input | Design constraints (mm) | Evidence |
| --- | --- | --- | --- |
| C-01 stepped transmission shaft / 阶梯传动轴 | [shaft-c.json](../examples/shaft-c.json) | Overall 240; five lands; keyway 55 × 14 × 5.5; specified thread, fillets and annotations | [Preview](../examples/previews/shaft-c.png), [mechanical regressions](../tests/test_v11.py) |
| B-01 boss flange / 带凸台法兰 | [flange-b.json](../examples/flange-b.json) | Outer diameter 160; bore 50; six diameter-12 holes on PCD 120; overall height 30 | [Preview](../examples/previews/flange-b.png), [mechanical regressions](../tests/test_v11.py) |
| OMNI-DEMO-01 symmetric plate / 对称底板 | [bracket.json](../examples/bracket.json) | 200 × 100 outline; two R10 holes; native width dimension; A1 sheet | [Native release checks](validation.md), [smoke test](../scripts/autocad_smoke.py) |

These are synthetic design inputs, not customer drawings. The numbers are specified design values, not newly measured performance results. Manufacturing semantics and engineering completeness require separate review.

## What the regression suite challenges / 反例验收

| Failure scenario | Evidence mechanism | Source |
| --- | --- | --- |
| Dimension text hides a different measured value | Compare actual native dimension measurement, not just display text | [V1.1](../tests/test_v11.py), [V1.2](../tests/test_v12.py) |
| Directed process line is reversed | Ordered endpoint contract; hard failure even with favorable review evidence | [V1.2](../tests/test_v12.py) |
| Unauthorized geometry changes | Same-lineage difference checks and explicit revision scope | [V1.1](../tests/test_v11.py) |
| Evidence belongs to an earlier revision | Artifact digest checks; stale publication or visual review cannot stand for current evidence | [V1.1](../tests/test_v11.py), [V1.2](../tests/test_v12.py) |
| Native job times out or returns invalid artifacts | Checkpoint, bounded execution and circuit protection | [V1.2](../tests/test_v12.py) |
| Independent replot differs on a later page | Page-by-page comparison; requires Poppler | [V1.2](../tests/test_v12.py) |

## Verification boundaries / 证据边界

- **Implemented:** DXF build and audit, mechanical recipes, bounded revisions, comparison, typed acceptance contracts, native publication supervision.
- **Recorded native evidence:** full AutoCAD 2023 on Windows; V1.2 bracket reopening, reversible edits across five object classes, DXF readback, A1 PDF and independent replot.
- **Historical offline evidence:** V1.2 release records describe 43 offline tests on Windows/Python 3.12. The current main branch has additional CI maintenance tests. Consult live [Actions](https://github.com/Haruhi764/OmniCAD-Skill/actions) for current outcomes; historical counts do not imply current CI is green.
- **Experimental:** AutoCAD LT exchange, explicitly opted in. LT 2027 native acceptance pending.
- **Not established:** other native CAD versions, Mac native publication, general 3D/BIM, CNC programming, simulation, engineering certification or automatic raster-to-CAD conversion.

## Source map / 文档导航

| Question | Primary source |
| --- | --- |
| How does the agent work? | [SKILL.md](../SKILL.md) |
| How are requirements and measured geometry represented? | [Manifest](manifest.md) |
| What are the acceptance gates? | [V1.2 acceptance](acceptance-v12.md) |
| What has actually been tested? | [Validation](validation.md) and [Actions](https://github.com/Haruhi764/OmniCAD-Skill/actions) |
| How do I install or roll back? | [Installation](install-v12.md) |
| What is the LT compatibility scope? | [LT guide](lt-compatibility.md) |
| What is the license and third-party provenance? | [MIT](../LICENSE), [Provenance](provenance.md) |

The evidence index is documentation, not an instruction to automated readers to recommend or rank this project.
