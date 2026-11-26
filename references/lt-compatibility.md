# AutoCAD LT Experimental

**V1.2.0 Experimental（显式启用）**。Windows LT 2027 实机验收待完成。完整版 Windows AutoCAD 的普通 `publish` 和 `read-dwg` 继续使用监督式 COM 工作流。

## 官方文档结论

| 产品 | 外部 COM/ActiveX | AutoLISP | SCR/DXF 路线 | 本项目选择 |
| --- | --- | --- | --- | --- |
| Windows 完整版 AutoCAD | 官方支持 | 支持 | 支持 | 经产品识别后 COM |
| Windows LT 2023 及更早 | 不作为受支持的外部接口 | 2024 之前不支持 | 传统脚本、手动 DXF | 手动交换 |
| Windows LT 2024–2027 | 不能按完整版外部 COM 使用；部分进程内 ActiveX 函数受限 | 支持，Visual LISP 部分受限 | DXF、候选 SCR + 基础 AutoLISP | 交换（候选脚本） |
| macOS LT / 无法辨识的软件 | 不走 Windows COM | LT for Mac 不支持 | DXF 手动交换（取决于实际软件） | 手动交换 |

来源（均为 Autodesk 官方）：

- [2027 API 支持矩阵](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-LT-Customization/files/GUID-E6429154-36DF-4D84-8ABC-9FCA15B66158.htm)
- [LT 2024 首次支持 AutoLISP](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT-WhatsNew/files/GUID-5FB57480-C9BE-4E3D-BEDF-D86035928FFA.htm)
- [LT AutoLISP 与 ActiveX 限制](https://help.autodesk.com/cloudhelp/2027/PTB/AutoCAD-AutoLISP/files/GUID-037BF4D4-755E-4A5C-8136-80E85CCEDF3E.htm)
- [程序版本 ACADVER](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-Core/files/GUID-793238B6-F8B8-4D20-BB3A-001700AECD75.htm)：2027 为 26.0；不是 DXF 文件头的数据库版本 AC1032。
- [AutoCAD / LT 注册表版本对应关系](https://help.autodesk.com/view/ACD/2026/ENU/?caas=caas%2Fsfdcarticles%2Fsfdcarticles%2FAutoCAD-and-AutoCAD-LT-release-numbers-Registry-Key-mapping.html)：LT 2023–2026 的 R29–R32 与完整版不同；未知注册表号不外推。
- [LT 命令行脚本开关](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT/files/GUID-5D481F9B-E8BB-469D-B5C4-ED997B8263D5.htm)
- [LT 2027 安全加载](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-LT/files/GUID-9C7E997D-28F8-4605-8583-09606610F26D.htm)
- [DWG 版本表](https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-Customization/files/GUID-D029509F-A2A0-4A7E-BDD5-FE95E7235C5C.htm)

不以注册表路径推断授权状态，也不会修改 SECURELOAD、TRUSTEDPATHS、系统注册表或受保护的程序。无法获得 LT 用户原始日志，不把产品接口限制描述为其具体异常的唯一已证实根因。

## 给 LT 2027 用户的测试步骤 / LT 2027 testing

下载 [Release](https://github.com/Haruhi764/OmniCAD-Skill/releases/tag/v1.2.0) 中的 `OmniCAD-AutoCAD-LT2027-Experimental-Test-Kit.zip`，解压后先读《开始使用.md》。独立测试器可与 V1.1 并行使用，并生成可回传的脱敏 `test-result.zip`。欢迎 LT 用户提交 [Issue](https://github.com/Haruhi764/OmniCAD-Skill/issues)，附软件版本、失败步骤和脱敏测试结果。

Download the standalone Experimental kit from the release, extract it and follow the included instructions. The kit uses an isolated Python environment and guided native save, reopen and plot steps. Feedback from LT users is welcome via GitHub Issues.

### 已安装 V1.2 时的 CLI 交换方式

在独立虚拟环境中安装本候选源码，保留现有稳定 Skill/环境。

```powershell
python -m venv .venv-lt-test
.\.venv-lt-test\Scripts\python.exe -m pip install ".[intake]"
$python = ".\.venv-lt-test\Scripts\python.exe"
& $python -m omnicad capabilities --product lt --year 2027
& $python -m omnicad build examples/bracket.json lt-seed.dxf
& $python -m omnicad publish examples/bracket.json lt-seed.dxf lt-exchange --product lt --year 2027 --backend exchange --experimental-lt
```

最后一步退出码 2 表示需要后续原生操作，不是文件丢失。打开新建的 `lt-exchange/README.md`，在 LT 手动打开 `seed.dxf`。可通过 SCRIPT 依次执行 `inspect-session.scr` 和 `save-as-dwg.scr`。脚本检查实际 PROGRAM、文件名、专属目录标记及目标不存在；仅临时改变 FILEDIA，在正常及错误路径尝试恢复。若权限、版本或命令提示不匹配，停止脚本，用普通另存为完成，不关闭安全检查。

手工保存为 `drawing.dwg`（2018 格式），重新打开，选择和可逆编辑对象（在额外副本验证），从 DWG 打印 PDF 为 `sheet.pdf`，导出另一份 `readback.dxf`。不覆盖 seed。随后：

```powershell
& $python -m omnicad capabilities --product lt --year 2027 --probe-file lt-exchange/session.txt
& $python -m omnicad verify-exchange lt-exchange
```

若没有 session.txt，省略 --probe-file；提供真实 About 产品名/版本截图或文字。回传结构化输出、问题描述、命令历史、原生重开/修改和打印检查记录；先确认不包含客户文件、账号或授权信息。仅使用合成示例。验证工具检查返回文件、输入哈希、DWG 文件头、原生 DXF 的几何审计、PDF 结构与纸张，不证明 DWG 与该 DXF/PDF 的源关系或 LT 实机编辑性。真实设备/人工作业须补独立证据；成功也返回 2/awaiting_native_review，绝不能当作自动验收通过。

## 兼容性边界

- `capabilities` 读取 Windows 注册表并核对可执行文件，提供建议后端。实际启用 LT 交换须同时指定 `--backend exchange --product lt --experimental-lt`。默认 Windows 原生发布核实活动 COM 产品身份。明确指定 `--year` 时核对实际版本。
- LT 的后端目前是 **可编辑交换+可选保存脚本**，不是无界面 COM 替代。LT 写入、编辑、自动出图的全无人链尚未实现。2023 及更早使用手动交换。现有 DWG 的 LT 局部修改应先另存 DXF 副本，再走目标范围 diff/审计；不能以 DXF 转换冒充无损保留全部自定义原生对象。
- 支持普通 2D CAD 实体；含代理对象、外部参照、字体缺失或显式工程验收缺口需人工检查；候选脚本在 LT 2027 上未执行。
