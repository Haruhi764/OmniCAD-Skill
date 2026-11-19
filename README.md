# OmniCAD-Skill

OmniCAD 将有明确依据的制图要求转换为可编辑二维 CAD 图形，按需求编号追踪实现与验收。V1.0 可以独立执行 DXF 绘图与校验，也可以调用本地授权 AutoCAD 保存 DWG、真实重开、出图和回读。

需要 Python 3.10+。建议在独立虚拟环境中安装。DWG/PDF 出图需要 Windows 和已授权安装的 AutoCAD、其 PDF 配置及对应字体。输出截图需要 Poppler 的 pdftoppm。

```text
python -m pip install ".[intake,autocad]"
omnicad build examples/bracket.json sample.dxf
omnicad audit examples/bracket.json sample.dxf --report draft.json
omnicad publish examples/bracket.json sample.dxf sample-release
omnicad preview sample-release/sheet.pdf review.png
python -m unittest discover -s tests -v
```

在纯离线 DXF 环境可仅安装项目本身，PDF 和图片检查使用 intake 附加依赖。Codex Skill 的启用与 CLI 安装是两个步骤。确认安装目录无同名技能后，把带 [SKILL.md](SKILL.md) 的项目目录放入本机受支持的技能目录。

| 能力 | V1.0 现状 |
|---|---|
| 资料预检 | PDF 文本与纸幅、DOCX 正文及表格文本、图片/DXF 元数据、DWG 文件头、UTF-8 任务书，按哈希缓存 |
| 原生二维绘图 | 线、圆、圆弧、多段线、中文文字、原生直线尺寸。图层、线宽、线型、字体及固定比例布局可配置 |
| 校验和追踪 | 校验单位、测量值、实体、边距及视口，筛查重合的线或圆和可能的文字重叠，追踪需求与证据 |
| 局部修改 | 自有 DXF 的文字替换及受限移动，校验基线后备份、修改、复检，可恢复至新的输出文件 |
| AutoCAD | Windows COM 原生保存及重开，导出同源 DXF 和 PDF。支持可信 DWG 的工作副本回读 |
| 出图复核 | 检查纸幅和裁切尺寸，可整页或分区渲染。目视确认记录绑定发布物指纹 |
| 扩展接口 | 已实现 AutoCAD 适配器。SolidWorks/Revit 尚无实现 |

资料预检提供证据索引，设计几何由复核后的 [manifest](references/manifest.md) 明确给出。复杂 OCR、自动矢量化、通用 DWG 编辑、BIM 和 3D 尚未实现。项目可复用绘图核心，不含行业自动设计或合规判断。见[工作流程](references/workflow.md)和[验证记录](references/validation.md)。

原创代码采用 [MIT 许可证](LICENSE)。第三方依赖及工具按各自许可使用，详情见[来源和许可](references/provenance.md)。私有回归资料应存放在 Git 忽略的 `.local` 目录下。
