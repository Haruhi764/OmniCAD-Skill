# Installation and compatibility / 安装与兼容性

Download `OmniCAD-Skill-1.2.0.zip` and `SHA256SUMS.txt` from the [V1.2.0 release](https://github.com/Haruhi764/OmniCAD-Skill/releases/tag/v1.2.0). Compare the archive's SHA-256 with the entry in the checksum file before extraction. Existing V1.1 users can keep both environments and test V1.2 in a separate folder.

```powershell
Get-FileHash .\OmniCAD-Skill-1.2.0.zip -Algorithm SHA256
Expand-Archive .\OmniCAD-Skill-1.2.0.zip .\OmniCAD-v120
Set-Location .\OmniCAD-v120\OmniCAD-Skill-1.2.0
py -3 -m venv .venv-v120
$py = ".\.venv-v120\Scripts\python.exe"
& $py -m pip install ".\wheelhouse\omnicad_skill-1.2.0-py3-none-any.whl[intake,autocad]"
& $py -m pip show omnicad-skill
& $py -m omnicad capabilities
& $py -m omnicad build examples/bracket.json work-v120.dxf
& $py -m omnicad audit examples/bracket.json work-v120.dxf
```

Use `python` in place of `py -3` if needed. Windows without AutoCAD or other supported Python platforms can use the wheel with `[intake]` for DXF and PDF checks. The wheel bundles OmniCAD. Pip obtains runtime dependencies separately. From a clean source checkout use `python -m pip install ".[intake,autocad]"` inside its own venv. Poppler is separately installed for render and print comparison.

## Upgrade, uninstall and rollback / 升级、卸载与回滚

1. 把 V1.2 解压到新目录，创建独立虚拟环境，使用其 Python 路径运行上面的合成示例。原 V1.1 环境可以继续用于生产。测试新版本时使用新的输出文件名和目录。
2. 需要在 Codex 中启用 V1.2 Skill 时，将原 Skill 文件夹备份到技能扫描范围之外，再装入含 `SKILL.md` 的 V1.2 源码文件夹。每次只启用一个同名 Skill。CLI 可独立使用。
3. 回滚时把 V1.1 Skill 文件夹放回原位，恢复此前的 V1.1 Python 路径。历史版本可从 [V1.1.0 Release](https://github.com/Haruhi764/OmniCAD-Skill/releases/tag/v1.1.0) 取回。
4. 卸载 V1.2 CLI 可运行 `& $py -m pip uninstall omnicad-skill`，或关闭相关进程后移除本次专用虚拟环境。需要移除 Skill 时，仅移除启用的 V1.2 Skill 文件夹。工程文件、测试输出及旧版环境分别保存。

Install and verify the new CLI in its own venv before switching the active Codex skill. Back up the old skill outside discovery, then enable the V1.2 folder containing `SKILL.md`. Roll back by restoring the old skill and using its original interpreter. Remove V1.2 with pip inside that environment or remove its dedicated venv once its programs have exited.

## Compatibility / 兼容性

| Workflow | Platform and evidence |
| --- | --- |
| DXF build, revision and OQA | Python 3.10+. PDF checks use `intake`. Run repository tests before deploying to a new environment. |
| Native DWG save, reopen, edit and PDF | Licensed full AutoCAD on Windows with `autocad` and `intake` extras. Release smoke tested on full AutoCAD 2023 (R24.2). Other versions need local verification. |
| AutoCAD LT | **Experimental** opt-in DXF exchange. Windows LT 2027 native acceptance pending. [Test kit and workflow](lt-compatibility.md). |
| PDF visual and print comparison | Install Poppler for raster comparison. Inspect fonts, legibility and layout manually. |

## Known limitations / 已知问题

- Native work locks within the user session. A timeout stops the worker and preserves the checkpoint. Verify the AutoCAD session before using `omnicad native-reset --confirm-host-reviewed` and create a new output directory for a new attempt.
- Native PDF drivers, plot styles and fonts vary. The repair utility covers the known duplicate PDF catalog `PageMode` case. Other structural errors require review.
- DXF interchange can lose custom entities, application metadata, external dependencies, or native behavior. Keep the original DWG and test a copy. LT users complete native save, reopen and plot inside AutoCAD LT.
- Digital comparison tolerances are tied to the reviewed drawing contract. Engineering judgments, ambiguous annotations and visual readability need independent review.
