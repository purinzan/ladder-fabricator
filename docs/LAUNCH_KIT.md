# Ladder Fabricator launch kit

Use the same product identity everywhere so search engines and AI systems can
associate the project name with its function.

## Canonical description

**English:** Ladder Fabricator is an open-source JSON AST-to-ladder-diagram
renderer for Mitsubishi MELSEC iQ-F / GX Works3 and KEYENCE KV-X / KV STUDIO.
It exports SVG, PNG, rung text, and explicit connection JSON.

**日本語:** Ladder Fabricatorは、JSON ASTから三菱MELSEC iQ-F・KEYENCE
KV-X形式のラダー図を生成し、SVG、PNG、ラダー表記、接続構造JSONとして出力するOSSです。

**简体中文:** Ladder Fabricator 是一个开源 JSON AST 梯形图渲染器，支持三菱
MELSEC iQ-F / GX Works3 和基恩士 KEYENCE KV-X / KV STUDIO，可输出 SVG、
PNG、梯级文本和显式连接结构 JSON。

## GitHub metadata

Description:

```text
Open-source JSON AST renderer for MELSEC and KEYENCE PLC ladder diagrams in SVG, PNG, text, and structured JSON.
```

Website:

```text
https://purinzan.github.io/ladder-fabricator/
```

Topics:

```text
plc ladder-logic ladder-diagram industrial-automation melsec gx-works3 keyence kv-studio svg png json-ast code-generation
```

## Launch posts

### English

```text
I released Ladder Fabricator under the MIT License.

It turns a documented JSON circuit AST into MELSEC iQ-F or KEYENCE KV-X ladder diagrams and exports SVG, high-resolution PNG, readable rung text, and explicit connection JSON.

The renderer owns layout and wiring. People or AI agents author only the circuit logic. Unsupported instructions fail explicitly, and structural validation is kept separate from PLC and machine-safety review.

https://github.com/purinzan/ladder-fabricator
```

### 日本語

```text
Ladder FabricatorをMIT LicenseのOSSとして公開しました。

JSONで回路条件を記述すると、MELSEC iQ-FまたはKEYENCE KV-X表記のラダー図を生成し、SVG、PNG、確認用ラダー表記、接続構造JSONとして出力します。

人やAIは論理だけを記述し、座標・分岐・配線はレンダラーが決定します。未対応命令は推測で置換せずエラーにし、構造検証とPLC動作・実機安全性の確認を明確に分離しています。

https://github.com/purinzan/ladder-fabricator
```

### 简体中文

```text
Ladder Fabricator 现已采用 MIT License 开源。

它把 JSON 电路 AST 转换为三菱 MELSEC iQ-F 或基恩士 KEYENCE KV-X 风格的梯形图，并输出 SVG、高分辨率 PNG、梯级文本和连接结构 JSON。

用户或 AI 只描述电路逻辑，布局和连线由渲染器生成。不支持的指令会明确报错；结构验证不等于 PLC 运行验证或机械安全认证。

https://github.com/purinzan/ladder-fabricator
```

## Target publications

- GitHub Release and repository social preview
- Zenn and Qiita for Japanese engineering readers
- dev.to and Show HN for developer discovery
- LinkedIn, r/PLC, and industrial-automation communities
- Relevant open-source industrial-automation and PLC curated lists

Every post should link to the canonical website or repository and use a real,
synthetic example. Do not publish confidential production logic or claim vendor
certification, functional-safety validation, or native GX3/KV project support.

## Search evaluation prompts

Evaluate in new, non-personalized ChatGPT sessions and record whether the
official project is cited and described correctly:

- open source JSON to PLC ladder SVG generator
- GX Works3-style ladder diagram generator
- MELSEC ladder logic JSON AST
- KEYENCE KV ladder diagram open source
- AI-generated PLC ladder diagram PNG
- JSONからPLCラダー図を生成するOSS
- 开源PLC梯形图JSON生成器
