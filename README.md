# Ladder Fabricator

回路の条件をJSONで記述し、MELSEC iQ-FまたはKEYENCE KV-X表記の、デバイスコメント付き
ラダーSVGと論理・接続構造JSONを生成するPythonツールです。

Pythonパッケージ名は`gx3-ladder-export`です。CLIは`ladder-fabricator`を使用でき、
従来名の`gx3-ladder-export`も同じ機能の別名として残しています。

## 対応PLCモード

| モード | 対象環境 | SVGで使う主な命令表記 |
|---|---|---|
| 三菱電機モード | MELSEC iQ-F / GX Works3 | OUT、SET、RST、PLS、PLF、INV |
| KEYENCEモード | KV-X / KV STUDIO | OUT、SET、RES、DIFU、DIFD、CON |

同じ中間形式の論理・接続構造を使い、指定したモードに応じてデバイス検証、命令名、
SVGの表現を切り替えます。従来の`schema_version: 1`は三菱電機モードとして扱い、
`schema_version: 2`では`target`に三菱電機またはKEYENCEを明示できます。

GX Works3やGX3ファイルを使わず、依頼内容から作った小さな共通AST（JSON）だけでラダー図を生成できます。
座標や配線を手書きする必要はありません。Python 3.10以上で動作し、実行時の追加依存もありません。

## できること

- a接点・b接点・立ち上がり接点と、直列（AND）・並列（OR）・否定（NOT）を組み合わせる
- OUT、SET、RST、立ち上がりPLS、立ち下がりPLFと、演算結果を反転するINV命令を表す
- 条件構造から接点、分岐、合流、円形コイル、命令枠、母線を自動配置する
- `X0 AND (X1 OR X2)` のような共有接点を複製せずに描く
- デバイスコメントをSVGへ表示し、全文をSVGのtitleと構造JSONへ保持する
- GX Works3のラダー編集画面を基準に、1px配線、薄い点線グリッド、行コメント帯、命令セルの色と寸法を再現する
- 同じ入力から、安定した要素IDと明示的な接続関係を生成する
- 未対応の命令や壊れた入力を、曖昧な図にせずエラーとして返す
- KEYENCE KV-XモードでR/MR/LR等を検証し、RES、DIFU、CONへ正しく変換する

## 依頼からSVGまで

例えば、次のように回路を依頼します。

> X0がONで、X1またはX2がON、かつX3がOFFならY0を出力してください。
>
> X0は開始条件、X1とX2は運転条件、X3は停止要求、Y0は運転出力です。

人またはAIが、この要求を作成用JSONへ変換します。

```json
{
  "schema_version": 1,
  "title": "運転条件",
  "comments": {
    "X0": "開始条件",
    "X1": "運転条件1",
    "X2": "運転条件2",
    "X3": "停止要求",
    "Y0": "運転出力"
  },
  "rungs": [
    {
      "id": "run_output",
      "logic": {
        "and": ["X0", {"or": ["X1", "X2"]}, {"not": "X3"}]
      },
      "output": {"type": "coil", "device": "Y0"}
    }
  ]
}
```

保存したJSONをCLIへ渡すとSVGを生成します。

```powershell
python -m pip install .
gx3-ladder-export examples/basic.json -o outputs/basic.svg
```

接続・条件構造も必要な場合はJSONで出力できます。

```powershell
gx3-ladder-export examples/basic.json --format json -o outputs/basic.structure.json
```

入力だけを検証する場合:

```powershell
gx3-ladder-export examples/basic.json --validate-only
```

AIと人が確認しやすい`rung-text --comments`形式にする場合:

```powershell
ladder-fabricator rung-text examples/basic.json --comments
```

```text
# 共有接点を保持した並列回路
shared_branch  X0 AND (X1 OR X2) AND /X3 -> Y0  # X0="開始条件", X1="条件1", X2="条件2", X3="停止要求", Y0="出力"
```

入力を検証・正規化した再利用可能なASTとして保存する場合:

```powershell
ladder-fabricator examples/basic.json --format ast -o outputs/basic.ast.json
```

KEYENCE KV-Xの中間ファイルからSVGを生成する場合:

```powershell
gx3-ladder-export examples/keyence-kv-x.json -o outputs/keyence-kv-x.svg
```

KEYENCE用JSONは`schema_version: 2`と
`"target": {"vendor": "keyence", "series": "kv-x"}`を持ちます。同じ意味の`rst`、
`pls`、`plf`、`inv`は、MELSECではRST/PLS/PLF/INV、KEYENCEでは
RES/DIFU/DIFD/CONとしてSVGと構造JSONへ出力されます。

インストールせず、リポジトリ内から実行することもできます。

```powershell
python -m gx3_ladder_export examples/basic.json -o outputs/basic.svg
```

## AIとこのツールの役割

このパッケージ自体は自然言語を解釈しません。AIまたは利用者が要求を共通ASTへ変換し、
このツールが形式の検証、論理構造の保持、メーカー別命令への変換、配置、SVG生成を担当します。

この分離により、入力した論理をJSONまたはrung-textで確認してから図を生成できます。
同じASTから三菱電機・KEYENCE向けの命令表記、構造JSON、SVGを生成するため、各出力が
別々に回路の意味を解釈することはありません。

```text
依頼文 → 共通AST → rung-text --comments
                 ├→ メーカー別命令 → 構造JSON → SVG
                 └→ 正規化AST（保存・再入力）
```

## 入力形式

作成用JSONが共通ASTの保存形式です。`logic`には次の形式を入れ子で指定します。

| JSON | 意味 | ラダー表現 |
|---|---|---|
| `"X0"` | X0がON | X0のa接点 |
| `{"not": "X0"}` | X0がOFF | X0のb接点 |
| `{"device": "X0", "contact": "rising"}` | X0のOFF→ON | 立ち上がり接点 |
| `{"and": ["X0", "X1"]}` | 両方が成立 | 直列 |
| `{"or": ["X0", "X1"]}` | どちらかが成立 | 並列 |
| `{"inv": {"and": ["X0", "X1"]}}` | そこまでの演算結果を反転 | INV命令 |

出力の`type`は通常コイルの`coil`、保持ONの`set`、デバイスをリセットする`rst`、
条件の立ち上がり・立ち下がりで1スキャン出力する`pls`/`plf`を指定できます。SVGではMOVなどと同じセル構造で、
命令枠を命令セルとオペランドセルに分けます。`SET | Y0`、`RST | C0`、`PLS | M1`のように、
対象デバイスとそのコメントを命令枠内へ表示します。
INVはPLCの演算順序を明確にするため、`logic`の最外側だけで使用します。

[命令サンプル](examples/instructions.json)には、立ち上がり接点→SET、RST、PLS、AND結果→INV→OUTを収録しています。

複数の回路は`rungs`へ並べます。詳しい制約、正規化規則、入力上限は
[回路JSON v1](docs/FORMAT_JA.md)を参照してください。

## 生成物

### 正規化AST

`--format ast`は、短縮表記とNOTを正規化した共通ASTを出力します。メーカー固有の
RST/RESなどへ変換する前の意味を保持し、そのまま再入力できます。

### rung-text

`rung-text`はASTを「成立条件 → 出力」の1行形式にします。`--comments`を付けると、
その回路で参照するデバイスコメントだけを同じ行へ追加します。

### SVG

接点、分岐、合流、INV、母線、出力コイル、SET/RST/PLS命令を描画します。各要素には構造JSONと対応する
`data-node`または`data-connection`属性が付きます。ブラウザー、文書、Web画面へそのまま表示できます。

### 構造JSON

次の情報を機械的に扱える形で出力します。

- 正規化した条件構造
- 接点・コイル・分岐・合流・母線のノード
- ポートを持つ明示的な接続
- 各ノードの座標と配線の折れ線
- 出力条件と現在の制限事項

構造JSONは描画・参照用の導出結果です。再生成には作成用JSONを使用します。

## Python API

```python
import json
from pathlib import Path

from gx3_ladder_export import (
    build_bundle, circuit_to_ast, parse_circuit, render_rung_text, render_svg,
)

payload = json.loads(Path("examples/basic.json").read_text(encoding="utf-8"))
circuit = parse_circuit(payload)
canonical_ast = circuit_to_ast(circuit)
print(render_rung_text(circuit, comments=True))
bundle = build_bundle(circuit)
Path("basic.svg").write_text(render_svg(bundle), encoding="utf-8")
```

`parse_circuit`が共通ASTを検証・正規化します。`circuit_to_ast`と`render_rung_text`は
同じASTを保存用・確認用に変換し、`build_bundle`が接続と配置を導出して`render_svg`が描画します。

## 対応範囲

| 項目 | 対応 |
|---|---|
| 接点 | a接点、b接点、立ち上がり接点、立ち下がり接点 |
| 論理 | AND、OR、NOT、入れ子、最外側のINV |
| 出力 | 各回路に1つのOUT、SET、RST、PLS、PLF（KVではRES、DIFU、DIFD） |
| MELSEC接点デバイス | X、Y、M、L、B |
| MELSEC OUT/SET/PLSの対象 | Y、M、L、B |
| MELSEC RSTの対象 | X、Y、M、L、SM、F、B、SB、S、T、ST、C、D、W、SD、SW、R、Z、LC、LZ |
| KEYENCE接点デバイス | R、B、MR、LR、CR、T、C |
| KEYENCE OUT/SET/DIFUの対象 | R、B、MR、LR |
| KEYENCE RESの対象 | R、B、MR、LR、T、C、DM、EM、FM、ZF、W、TM |
| 文書 | 複数回路、回路名、デバイスコメント |
| 出力 | SVG、論理・接続構造JSON |

タイマー回路の生成、比較・データ命令、ラベル、GX3/KV STUDIOプロジェクトの取込みは未対応です。
RSTではタイマ・カウンタの現在値やワードデバイスを0にする対象として、`T0`、`ST0`、`C0`、`D0`などを指定できます。
未対応入力はエラーとして返し、OUTへ置き換えて表示することはありません。

形式検証の成功は、PLC上の動作や実機へ投入できることの保証ではありません。
CPUごとのデバイス範囲、配線、センサー極性、安全条件は利用側で確認してください。
立ち上がり接点、PLS、SET/RSTの意味は構造へ保持しますが、前回値や保持デバイスの状態を本ツール内で実行・監視はしません。

## 開発

```powershell
python run_tests.py
python -m pip install build
python -m build --wheel
```

CIはWindows、Linux、macOSのPython 3.10と3.12で実行します。真理値、生成接続、
SVGの端点、共有接点、入力上限、文字エスケープ、実CLIを検証しています。

## KEYENCE KV版の調査データ

KV-Xを主対象とするメーカー別出力の準備として、公式マニュアル群、命令分類、
GX Works3との命令差分、KVデバイス体系を`data/keyence_kv/`に収録しています。
登録制PDFそのものや利用者の登録情報はリポジトリへ入れません。

検索用SQLiteは標準ライブラリだけで生成できます。

```powershell
python tools/build_keyence_reference_db.py
sqlite3 reference/keyence/kv_reference.sqlite3 "SELECT concept_ja, gx3_json, kv_json FROM instruction_mappings WHERE relation <> 'same';"
```

現在は基本回路と意味差が大きい命令を確認済み中核として収録しています。現行KV-Xの
全命令・全型サフィックス・CPU別制限は、公式コマンドリファレンス取得後に同じDBへ追加します。
調査範囲、根拠資料、設計への反映方法は
[KEYENCE KV版の命令・デバイス調査](docs/KEYENCE_KV_RESEARCH_JA.md)を参照してください。

- [入力形式と出力仕様](docs/FORMAT_JA.md)
- [流用調査と設計方針](docs/REUSE_AUDIT_JA.md)
- [GX Works3表示の測定基準](docs/GX_WORKS3_VISUAL_REFERENCE_JA.md)
- [流用元と変更点](NOTICE.md)

## データの扱い

入力と出力はローカルファイルです。利用者のPLCプロジェクト、生成物、設備情報を外部へ送信しません。
リポジトリの`examples/`には手作りの合成回路だけを置きます。

## ライセンス

本リポジトリは独自ライセンスです。利用条件は[LICENSE.txt](LICENSE.txt)を確認してください。
