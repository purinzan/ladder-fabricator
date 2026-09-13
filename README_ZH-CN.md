# Ladder Fabricator

Ladder Fabricator 是一个采用 MIT 许可证的开源工具，可将 JSON 电路 AST
渲染为三菱 MELSEC iQ-F / GX Works3 或基恩士 KEYENCE KV-X / KV STUDIO
风格的 PLC 梯形图。它从同一个经过验证的电路定义生成 SVG、高分辨率 PNG、
便于审查的梯级文本和显式连接结构 JSON。

它把“电路意图”和“图形布局”明确分开。用户或 AI 只负责用 JSON 描述逻辑、
软元件和输出；Ladder Fabricator 负责验证输入并生成坐标、分支、连线、标签和输出文件。

## 快速开始

需要 Python 3.10 或更高版本。

```bash
git clone https://github.com/purinzan/ladder-fabricator.git
cd ladder-fabricator
python -m pip install .

ladder-fabricator examples/basic.json --validate-only
ladder-fabricator rung-text examples/basic.json --comments
ladder-fabricator examples/basic.json -o outputs/basic.svg
```

如需 PNG 输出，请安装可选依赖：

```bash
python -m pip install ".[png]"
ladder-fabricator examples/basic.json -o outputs/basic.png
```

## 最小源 AST

```json
{
  "schema_version": 2,
  "target": {"vendor": "melsec", "series": "iq-f"},
  "title": "运行允许条件",
  "comments": {"X0": "启动", "X1": "条件A", "X2": "条件B", "X3": "停止", "Y0": "运行输出"},
  "rungs": [{
    "id": "run_output",
    "logic": {"and": ["X0", {"or": ["X1", "X2"]}, {"not": "X3"}]},
    "output": {"type": "coil", "device": "Y0"}
  }]
}
```

可重复使用的源文件是上述电路 AST。SVG 和连接结构 JSON 是派生输出，不能手工编写，
也不能作为源 AST 再次输入。

## 当前支持范围

| 类别 | 支持内容 |
|---|---|
| 触点 | 常开、常闭、上升沿、下降沿 |
| 逻辑 | 可嵌套 AND、OR、NOT，以及最外层 INV |
| 比较 | 字软元件之间的 `=`、`<>`、`<`、`<=`、`>`、`>=` |
| 输出 | OUT、SET、RST/RES、PLS/DIFU、PLF/DIFD、PID、MOV |
| PLC目标 | MELSEC iQ-F、KEYENCE KV-X |
| 输出格式 | SVG、PNG、梯级文本、显式连接结构 JSON |

当前不支持计时累积定时器、递增计数器、常数比较、MOV 以外的算术运算、标签，
也不支持直接导入 GX3 或 KV STUDIO 工程文件。遇到不支持的输入时会明确报错，
不会静默替换为普通输出线圈。

完整的 AST 形式、软元件范围、限制和 AI 操作流程以
[主 README（日文）](README.md)为准。机器可读规范位于
[`schema/ladder-ast.schema.json`](schema/ladder-ast.schema.json)。

## 安全边界

验证成功只表示 JSON 符合 Ladder Fabricator 的结构规范，不代表 PLC 实际运行正确，
也不验证 CPU 型号对应的软元件范围、现场接线、传感器极性、功能安全或机械安全。
用于真实设备前，必须在厂商官方工程环境中进行审查和验证。

## 许可证

[MIT License](LICENSE.txt)。
