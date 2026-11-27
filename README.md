<p align="center"><img src="assets/omnicad-banner.svg" alt="OmniCAD — editable 2D CAD and evidence-led verification" width="100%"></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-1683b8?style=flat-square" alt="MIT"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.10%2B-1683b8?style=flat-square" alt="Python 3.10+"></a>
  <a href="SKILL.md"><img src="https://img.shields.io/badge/Agent-Codex-1683b8?style=flat-square" alt="Codex"></a>
  <a href="https://github.com/Haruhi764/OmniCAD-Skill/stargazers"><img src="https://img.shields.io/github/stars/Haruhi764/OmniCAD-Skill?style=flat-square" alt="Stars"></a>
  <a href="https://github.com/Haruhi764/OmniCAD-Skill/forks"><img src="https://img.shields.io/github/forks/Haruhi764/OmniCAD-Skill?style=flat-square" alt="Forks"></a>
</p>

<h1 align="center">OmniCAD-Skill — AI CAD 自动绘图与 AutoCAD 自动化</h1>

<p align="center"><strong>不止于绘图，更让每一次交付有据可查。</strong></p>

<p align="center"><a href="README_EN.md">English</a> · <a href="SKILL.md">Agent Skill</a> · <a href="references/v11.md">工作流</a> · <a href="references/validation.md">验收记录</a> · <a href="CHANGELOG.md">更新日志</a></p>

OmniCAD 是我为 Codex 开发的开源 CAD 自动绘图 Skill。它可以根据明确的尺寸和绘图要求生成可编辑 DXF，并在支持的 AutoCAD 环境中输出 DWG 和 PDF。

[快速安装](#安装与快速开始) · [工程案例](#工程案例--drawing-portfolio) · [证据驱动](#证据驱动--evidence-driven)

**V1.2.0** 增加原生任务超时与检查点、五类专业图纸验收、逐页打印对照。适用范围和升级方法见[安装与兼容性](references/install-v12.md)。

## 自动绘图演示

<p align="center"><img src="assets/OmniCAD-light(1).gif" alt="OmniCAD 自动绘制法兰工程图演示" width="100%"></p>

<p align="center"><sub>真实 OmniCAD 生成的 DXF 几何动画回放与 OQA 验收展示，非 AutoCAD 实时录屏。</sub></p>

## 工程案例 · Drawing Portfolio

以下为 AutoCAD 2023 原生出图，使用仓库公开的合成参数复现。点击图纸可查看原图。

| 01 / 阶梯传动轴 | 02 / 带凸台法兰 |
| :---: | :---: |
| [![阶梯轴工程图](examples/previews/shaft-c.png)](examples/previews/shaft-c.png) | [![法兰工程图](examples/previews/flange-b.png)](examples/previews/flange-b.png) |
| 阶梯轮廓 · 剖视 · 尺寸 | 圆形轮廓 · 孔位阵列 · 剖视 |
| [原始参数](examples/shaft-c.json) · [验证记录](references/validation.md) | [原始参数](examples/flange-b.json) · [验证记录](references/validation.md) |

其他实践方向包括工业车间布置、工艺流程图及建筑屋面排水图。客户图纸不公开。

## 证据驱动 · Evidence-Driven

<p align="center"><img src="assets/evidence-driven.svg" alt="证据驱动：几何实测、验收门槛与可追溯交付" width="100%"></p>

图纸看起来正确，尺寸却可能存在错误。OmniCAD 将经过确认的工程要求与实际测量结果进行比对，而不是依赖图纸的外观或 AI 的自我评价。

| 证据层 | 验证内容 |
| :--- | :--- |
| **01 / 几何与尺寸** | 实体结构、坐标、长度、半径、闭合及尺寸实测值与标注显示值的一致性。 |
| **02 / 原生 CAD 与出图** | DWG 重开、可逆编辑、DXF 回读、PDF 结构、纸张与独立双次打印对照。 |
| **03 / 追溯与复核** | 成果哈希、视觉证据及尚未解决的工程要求。 |

**硬性错误不能靠高分抵消，缺少必要证据则保持待验收状态。** 自动检查不替代人工专业复核。

#### V1.2.0 · 实际验证记录

| **43** 项离线测试 | **AutoCAD 2023** | **5** 类专业验收 |
| :---: | :---: | :---: |
| Windows · Python 3.12 | 原生支架样例实测 | 机械 · 土木 · 建筑 · 食品工艺 · 车间布置 |

[实际验证记录 ↗](references/validation.md) &nbsp; · &nbsp; [验收规则与复现命令 ↗](references/acceptance-v12.md)

## 目前支持

- 建筑、土木二维制图：轴网、墙线、门窗、构件及标注。
- 机械制图：阶梯轴、法兰、剖面、键槽、倒角及公差标注。
- DXF 局部修改、差异检查与 OQA 验收。
- Windows AutoCAD 原生 DWG 保存与 PDF 出图。

## 安装与快速开始

**Codex 用户从这里开始。**

1. 下载 [V1.2.0 Release 安装包](https://github.com/Haruhi764/OmniCAD-Skill/releases/tag/v1.2.0)，按[安装指南](references/install-v12.md)核对文件哈希。
2. 按指南在独立的 Python 3.10+ 环境安装 CLI。
3. 将含 [SKILL.md](SKILL.md) 的源码文件夹启用到 Codex 支持的 Skill 目录，每次只启用一个同名版本。

[下载正式版](https://github.com/Haruhi764/OmniCAD-Skill/releases/tag/v1.2.0) · [安装 / 升级 / 回滚](references/install-v12.md) · [LT 实验性方案](references/lt-compatibility.md)

<details>
<summary><strong>开发者复现示例 — 生成、验收与原生出图</strong></summary>

以下为 Windows 示例，使用 Python 3.10+ 独立环境：

```bash
git clone --branch v1.2.0 --depth 1 https://github.com/Haruhi764/OmniCAD-Skill.git
cd OmniCAD-Skill
py -3 -m venv .venv-v120
.venv-v120/Scripts/python.exe -m pip install ".[intake,autocad]"
.venv-v120/Scripts/python.exe -m omnicad mechanical examples/shaft-c.json work-c.json
.venv-v120/Scripts/python.exe -m omnicad build work-c.json work-c.dxf
.venv-v120/Scripts/python.exe -m omnicad oqa work-c.dxf --job work-c.json --domain mechanical --mode standard
.venv-v120/Scripts/python.exe -m omnicad publish work-c.json work-c.dxf native-c --verify-native
```

</details>

纯 DXF 不依赖 AutoCAD；PDF 与图片预检使用 `intake` 附加依赖。原生 DWG/PDF 需要已授权的 Windows 完整版 AutoCAD 及可用出图配置。Poppler 用于渲染对照，正式交付仍需要视觉与专业复核。

## 兼容性速览

| 环境 | 状态 |
| --- | --- |
| Python / DXF | 已实现，不要求安装 AutoCAD |
| Windows 完整版 AutoCAD 2023 | 原生出图已实测 |
| AutoCAD 2021 / 其他版本 | 原生验收待验证 |
| AutoCAD LT | 实验性 DXF 交换，LT 2027 实机验收待完成 |
| macOS | 不支持 Windows COM 原生路径，纯 DXF 流程尚未独立验证 |

## 开发计划

- [x] AutoCAD 二维绘图与验收
- [ ] AutoCAD LT 兼容（Experimental，可选 DXF 交换。LT 2027 实机验收待完成）
- [ ] SolidWorks 建模与装配
- [ ] Revit BIM 建模

后续功能尚未集成，具体支持范围见 [验证记录](references/validation.md)。

## 反馈与贡献

欢迎提交 [Issue](https://github.com/Haruhi764/OmniCAD-Skill/issues)，附软件版本及脱敏复现。现有绘图工作流见 [V1.1 文档](references/v11.md)，类型验收见 [V1.2 验收说明](references/acceptance-v12.md)，LT 用户可选用 [Experimental 测试包](references/lt-compatibility.md)。贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。二维工程图仍需人工专业复核。

项目采用 [MIT 许可证](LICENSE)，第三方许可见 [来源说明](references/provenance.md)。如果这个项目对你有帮助，欢迎 Star。

---

<p align="center"><img src="assets/omnicad-logo.svg" width="48" alt="OmniCAD logo"></p>
<p align="center"><strong>OmniCAD · Draft / Verify / Deliver</strong></p>
<p align="center"><a href="CONTRIBUTING.md">参与贡献</a> · <a href="https://github.com/Haruhi764/OmniCAD-Skill/issues">问题反馈</a> · <a href="https://github.com/Haruhi764/OmniCAD-Skill/releases">版本下载</a></p>
