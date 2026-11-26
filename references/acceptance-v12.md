# V1.2 验收标准

`oqa --mode light|standard|full` 用于分级检查。需要明确专业类型及验收门槛时使用 `accept`。

1. **硬门槛**：DXF 结构与原生对象、非代理整图；正式内容检查；审核后的 manifest 几何及图层、单位、图纸/比例、显式角色数量与数值；尺寸显示与实测一致；真实 DWG 重开、编辑样本、独立双次打印一致、PDF 结构与纸张/渲染。关键输入缺失、原生证据缺失为 pending，硬错误为 failed。
2. **质量分**：重复尺寸、视觉文字/字体和布局/比例、PDF 视觉检查，每一证据点为 1 分；显示得分/可得分及未验证数。它不是跨专业百分制，没有用高分补偿关键失败的机制。视觉问题未证实则不能判最终通过；发现错误也必须纠正。
3. 实际碰撞、卫生工艺合理性、标准件、公差语义、图签署名及施工安全依独立工程复核。程序能够验证被编码的输入，不能自动推定工程正确。正式成果不写任何内部待确认文字。

| domain | 角色 | 硬性数值/语义证据 |
| --- | --- | --- |
| mechanical | profile, dimensions, annotations, sections | 主体长度/半径/端点/闭合，尺寸实测值；符号与剖视及制造语义人工复核 |
| civil | geometry, elevations, axes, sections, components | 构件端点/长度/闭合等、轴网、明确标高文本；构造与剖切人工复核 |
| architecture | walls, openings, axes, dimensions | 墙体端点/闭合，轴网，尺寸实测；门窗/墙界及尺度复核 |
| food-process | equipment, flow, labels, sequence | 有向线段端点，逐项标签；工序名称匹配不是完整拓扑证明，必须核实节点映射及箭头 |
| workshop-layout | walls, openings, axes, dimensions, equipment, routes, schedule | 边界、轴线、尺寸、物料路线及设备表文本；设备实际净距/卫生分区需专业复核 |

## 合同格式

```json
{
  "model_units": 4,
  "dimension_display_tolerance": 0.001,
  "roles": {
    "geometry": [{"layer": "BOUNDARY", "type": "LWPOLYLINE", "count": 1, "field": "closed", "values": [true]}],
    "axes": [{"layer": "GRID", "type": "LINE", "count": 1, "field": "length", "values": [6000], "tolerance": 0.001}],
    "elevations": [{"layer": "LEVEL", "type": "TEXT", "count": 1, "field": "text", "values": ["+0.000"]}]
  }
}
```

这是 civil 的不完整示例，缺少 sections/components 会进入 pending；数值仅为合成示例。每个 numeric role 必须显式提供正的有限容差，单位与模型/字段一致。容差为数字比较阈值，**不代表加工或施工公差**，不可套用到所有工程。支持 length、radius、measurement、text、closed 和有序 endpoints；endpoints 是 `[[[startX,startY],[endX,endY]],...]`，反向不能通过，位置匹配允许指定的数字容差。

```
omnicad accept model.dxf --domain civil --contract contract.json --job job.json --target dxf --report acceptance.json
omnicad accept readback.dxf --domain mechanical --contract contract.json --job job.json --publication publication/report.json --review review.json --report acceptance.json
```

审查文件仅在其 SHA256 与实际成果一致时采用：

```json
{"sha256":{"dxf":"...","dwg":"...","pdf":"..."},"checks":{"engineering_completeness":{"state":"passed","note":"独立人员核实的具体依据"},"visual_labels":{"state":"passed","note":"..."}, "layout_and_scale":{"state":"passed","note":"..."}, "pdf_visual_layout":{"state":"passed","note":"..."}}}
```

实际报告可包括 requirement:编号、dimension_display 等有人工需求的具名项；仅能解除被明确列为 unverified 的人工项，不能覆盖失败的几何、缺失文件/实机证据。对完整交付 `--target dwg-pdf`（默认）使用匹配原生出版记录，双次打印逐页比较。对交换包仅可报告返回文件审计，不能制造 AutoCAD 实测记录。

自动证据来自拍照之外的几何/文件检查；AutoCAD 证据来自本地原生发布；人工证据记录来源与哈希。系统不是签字审查或标准验证替代品。普通关键字命中须评估真实来源，禁止自动删除必要署名；全量 DWG 自定义属性和复杂元数据尚需 CAD 环境人工核对。
