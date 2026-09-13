# Ladder Fabricator

回路の条件をJSONで記述し、MELSEC iQ-FまたはKEYENCE KV-X表記の、デバイスコメント付き
ラダーSVGと論理・接続構造JSONを生成するPythonツールです。

Pythonパッケージ名は`gx3-ladder-export`です。CLIは`ladder-fabricator`を使用でき、
従来名の`gx3-ladder-export`も同じ機能の別名として残しています。

## AI・自動化エージェント向け必読

このREADMEを、回路作成用JSON（共通AST）の**人・AI共通の正本**とします。AIが回路を生成、
変更、レビュー、またはSVGへ変換する場合は、作業前に少なくとも
[AST・命令リファレンス（正本）](#ast命令リファレンス正本)、
[AIの作成手順](#aiの作成手順)、[対応範囲](#対応範囲)を読んでください。

このリポジトリには、各AI製品が自動的に読む規約ファイルからREADMEへ誘導する入口も置いています。
入口ファイルへ仕様を複製せず、仕様変更はREADMEと実装を同じコミットで更新します。

| AI／エージェント | 自動読込を狙う入口 |
|---|---|
| OpenAI CodexほかAGENTS.md対応エージェント | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Cursor | `.cursor/rules/ladder-fabricator.mdc`、`.cursorrules` |
| Windsurf | `.windsurfrules` |
| Cline | `.clinerules` |
| Aider | `.aider.conf.yml` |
| llms.txt対応クローラー／一般AI | `llms.txt`、`AI_INSTRUCTIONS.md` |

外部AIがリポジトリ規約を無視する場合まで技術的に強制することはできません。主要製品の自動読込規約、
ルートREADMEの冒頭、汎用入口を重ね、どの入口からでも同じ正本へ到達させています。

重要な境界:

- AIは依頼内容を下記ASTへ変換する。座標、配線、SVG要素は作成しない
- 再生成可能な入力は作成用JSONであり、`--format json`の構造JSONは再入力しない
- 表にない命令やデバイスを推測、別命令への置換、単純OUTへの縮退で表現しない
- 必ず`--validate-only`の後に`rung-text --comments`で論理を確認してからSVGを生成する
- 構造検証の成功はPLCの実行、安全性、CPU固有のデバイス範囲を保証しない

## 対応PLCモード

| モード | 対象環境 | SVGで使う主な命令表記 |
|---|---|---|
| 三菱電機モード | MELSEC iQ-F / GX Works3 | OUT、SET、RST、PLS、PLF、INV、比較、PID、MOV |
| KEYENCEモード | KV-X / KV STUDIO | OUT、SET、RES、DIFU、DIFD、CON、比較、PID、MOV |

同じ中間形式の論理・接続構造を使い、指定したモードに応じてデバイス検証、命令名、
SVGの表現を切り替えます。従来の`schema_version: 1`は三菱電機モードとして扱い、
`schema_version: 2`では`target`に三菱電機またはKEYENCEを明示できます。

GX Works3やGX3ファイルを使わず、依頼内容から作った共通ASTから直接ラダー図を生成できます。
座標や配線を手書きする必要はありません。Python 3.10以上で動作し、実行時の追加依存もありません。

## できること

- a接点・b接点・立ち上がり接点・立ち下がり接点と、直列（AND）・並列（OR）・否定（NOT）を組み合わせる
- 比較、OUT、SET、RST、PLS、PLF、PID、MOVと、演算結果を反転するINV命令を表す
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

### CLI一覧

| 指定 | 内容 |
|---|---|
| `ladder-fabricator INPUT` | SVGを標準出力 |
| `-o PATH`／`--output PATH` | 結果をUTF-8ファイルへ保存し、親フォルダを作成 |
| `--format svg` | SVGを生成。既定値 |
| `--format json` | 描画・参照用の構造JSONを生成 |
| `rung-text INPUT` | `--format rung-text`の短縮形 |
| `--format rung-text` | 条件から出力への確認用テキストを生成 |
| `--comments` | rung-textへ参照デバイスのコメントを追加 |
| `--target melsec-iq-f` | 入力内のtargetを一時的にMELSEC iQ-Fへ上書き |
| `--target keyence-kv-x` | 入力内のtargetを一時的にKEYENCE KV-Xへ上書き |
| `--validate-only` | 作成用JSONの構造検証だけを実行 |

## AIとこのツールの役割

このパッケージ自体は自然言語を解釈しません。AIまたは利用者が要求を共通ASTへ変換し、
このツールが形式の検証、論理構造の保持、メーカー別命令への変換、配置、SVG生成を担当します。

この分離により、入力した論理をrung-textで確認してから図を生成できます。
同じASTから三菱電機・KEYENCE向けの命令表記、構造JSON、SVGを生成するため、各出力が
別々に回路の意味を解釈することはありません。

```text
依頼文 → メモリ上の共通AST → 接続・配置 → SVG
                         └→ rung-text --comments（任意の確認表示）
```

## AST・命令リファレンス（正本）

CLI入力のJSONは検証後にメモリ上の共通ASTへ変換されます。ここにない表記は未対応です。
より内部的な正規化規則と構造JSONについては[回路JSON v1 / v2](docs/FORMAT_JA.md)に記載しています。

### 文書

```json
{
  "schema_version": 2,
  "target": {"vendor": "melsec", "series": "iq-f"},
  "title": "文書名",
  "comments": {"X0": "開始", "Y0": "運転出力"},
  "rungs": [
    {
      "id": "run_output",
      "title": "回路名",
      "logic": "X0",
      "output": {"type": "coil", "device": "Y0"}
    }
  ]
}
```

| フィールド | 必須 | 形式と制限 |
|---|---|---|
| `schema_version` | 必須 | `1`または`2`。v1はMELSEC iQ-F固定 |
| `target` | v2で必須 | 下表の`vendor`と`series`を完全一致で指定 |
| `title` | 任意 | 文書名、160文字以内 |
| `comments` | 任意 | デバイス名からコメントへのマップ。最大512件、各2048文字以内 |
| `rungs` | 必須 | 1～64回路の配列 |

各回路の`id`は英字で開始し、英数字、`_`、`-`だけを使う48文字以内の一意な値です。
`title`は任意の160文字以内、`logic`と`output`は必須です。未知フィールドは拒否されます。

### 対象PLC

| target ID／指定 | 対象 | v1 | v2 |
|---|---|---|---|
| `melsec-iq-f`／`{"vendor":"melsec","series":"iq-f"}` | MELSEC iQ-F / GX Works3 | 既定値 | 指定可能 |
| `keyence-kv-x`／`{"vendor":"keyence","series":"kv-x"}` | KEYENCE KV-X / KV STUDIO | 不可 | 指定可能 |

保存・共有する入力にはv2と`target`を明記します。CLIの`--target`は一時的な上書き用です。

### logicで使える全表記

次の形は相互に入れ子にできます。ただし`inv`だけは`logic`の最外側に限定されます。

| 種類 | JSON | 成立条件／表示 |
|---|---|---|
| a接点省略形 | `"X0"` | X0がON |
| a接点 | `{"device":"X0","contact":"a"}` | X0がON |
| b接点 | `{"device":"X0","contact":"b"}` | X0がOFF |
| b接点省略形 | `{"not":"X0"}` | X0がOFF |
| 立ち上がり接点 | `{"device":"X0","contact":"rising"}` | OFF→ONの1スキャン |
| 立ち下がり接点 | `{"device":"X0","contact":"falling"}` | ON→OFFの1スキャン |
| AND | `{"and":["X0","X1"]}` | 全条件成立。2項以上 |
| OR | `{"or":["X0","X1"]}` | いずれか成立。2項以上 |
| NOT | `{"not":{"or":["X0","X1"]}}` | 子条件全体を否定し、接点極性とAND/ORへ正規化 |
| INV | `{"inv":{"and":["X0","X1"]}}` | 最外側だけ。MELSECはINV、KV-XはCON |
| 比較 | `{"compare":{"operator":">=","left":"D101","right":"D100"}}` | ワードデバイス同士の比較 |

比較演算子は`=`、`<>`、`<`、`<=`、`>`、`>=`です。定数との比較には未対応です。
`not`で立ち上がり／立ち下がり接点を反転することはできません。`inv`は論理的なNOTへ
置換されず、PLC命令として保持されます。

### outputで使える全表記

1回路につき出力は1つです。`coil`だけは`type`を省略でき、既定値になります。

| type | 作成用JSON | MELSEC | KEYENCE | 意味 |
|---|---|---|---|---|
| `coil` | `{"type":"coil","device":"Y0"}` | OUT | OUT | 条件結果を通常出力 |
| `set` | `{"type":"set","device":"M0"}` | SET | SET | 条件成立時に保持ON |
| `rst` | `{"type":"rst","device":"M0"}` | RST | RES | ビットOFF／対応する現在値を0 |
| `pls` | `{"type":"pls","device":"M0"}` | PLS | DIFU | 条件の不成立→成立時に1スキャン出力 |
| `plf` | `{"type":"plf","device":"M0"}` | PLF | DIFD | 条件の成立→不成立時に1スキャン出力 |
| `pid` | 下記 | PID | PID | SVとPVからMVを演算 |
| `mov` | `{"type":"mov","source":"D0","destination":"D10"}` | MOV | MOV | ワード値を転送 |

PIDの属性順序は目標値（SV）、測定値（PV）、パラメータ先頭、出力値（MV）です。

```json
{
  "type": "pid",
  "setpoint": "D100",
  "process_value": "D101",
  "parameters": "D200",
  "destination": "D300"
}
```

三菱iQ-Fではパラメータ先頭から25点を占有するため、他用途と重ならない領域を指定します。
PIDの具体的なパラメータ値、スケーリング、周期、出力上限はこのASTでは設定・検証しません。

### メーカー別に使用可能なデバイス

| 用途 | MELSEC iQ-F | KEYENCE KV-X |
|---|---|---|
| 接点 | X、Y、M、L、B | R、B、MR、LR、CR、T、C |
| `coil`、`set`、`pls`、`plf` | Y、M、L、B | R、B、MR、LR |
| `rst` | X、Y、M、L、SM、F、B、SB、S、T、ST、C、D、W、SD、SW、R、Z、LC、LZ | R、B、MR、LR、T、C、DM、EM、FM、ZF、W、TM |
| 比較、`pid`、`mov`のワード | D、W、SD、SW、R、Z | DM、EM、FM、ZF、W、TM |

MELSECのX/Y/B/SB/W/SWは16進、その他の対応デバイスは10進です。小文字とゼロ埋めは
正規化されます。KEYENCEのR/MR/LRは末尾ビット番号00～15を検査し、B/Wは16進です。
KV-XのR/MR/LR/T/C/DM/EM/FM/TMは先頭に`@`を付けたローカル指定も保持します。
CPUごとのデバイス上限は検査しません。

### 検証上限と拒否する入力

- UTF-8（BOM可）、入力ファイル最大1 MiB
- 1文書1～64回路、条件ノード合計512以内、条件の深さ24以内
- `and`と`or`は2項以上。空配列、1項だけの配列は拒否
- 重複回路ID、重複JSONキー、正規化後に重複するコメントキーは拒否
- ラベル、ビット／桁指定、添字、間接指定、未知フィールドは拒否
- 入力JSON自身を出力先として上書きする指定は拒否
- エラー時は部分的なSVGを出力せず、未対応命令をOUTへ置き換えない

### AIの作成手順

AIは次の順序を固定して使用します。

1. 依頼から対象PLC、デバイスとコメント、各回路の成立条件、出力を抽出する
2. このREADMEの表にある作成用JSONだけでASTを作る。座標や配線は記述しない
3. `ladder-fabricator circuit.json --validate-only`を実行する
4. `ladder-fabricator rung-text circuit.json --comments`を実行し、依頼と条件式を照合する
5. `ladder-fabricator circuit.json -o output.svg`でSVGを生成する
6. 必要な場合だけ`--format json`で導出済み構造JSONを生成する
7. 結果には「形式検証済み」と「PLC動作・実機安全性は未保証」を区別して記載する

入力の意味が複数に解釈できる場合や、表にない命令が必要な場合は、推測して生成せず不足仕様を明示します。

[命令サンプル](examples/instructions.json)には、立ち上がり接点、SET、RST、PLS、INVを収録しています。
[KEYENCE例](examples/keyence-kv-x.json)にはKV-XのデバイスとRESへの変換を収録しています。
[ロードセルPID押圧制御](examples/servo_force_pid.py)は、メモリ上のASTからPID・MOVを含むSVGを生成します。

## 生成物

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
    parse_circuit, render_circuit, render_rung_text,
)

payload = json.loads(Path("examples/basic.json").read_text(encoding="utf-8"))
circuit = parse_circuit(payload)
print(render_rung_text(circuit, comments=True))
Path("basic.svg").write_text(render_circuit(circuit), encoding="utf-8")
```

`parse_circuit`が入力をメモリ上の共通ASTへ検証・正規化します。`render_rung_text`は
その任意の確認表示であり、SVG生成には通りません。`render_circuit`がASTから接続と配置を
導出し、そのままSVGを返します。

## 対応範囲

| 項目 | 対応 |
|---|---|
| 接点 | a接点、b接点、立ち上がり接点、立ち下がり接点 |
| 論理 | AND、OR、NOT、入れ子、最外側のINV |
| 比較 | ワードデバイス同士の`= <> < <= > >=` |
| 出力 | 各回路に1つのOUT、SET、RST、PLS、PLF、PID、MOV（KVではRES、DIFU、DIFD） |
| MELSEC接点デバイス | X、Y、M、L、B |
| MELSEC OUT/SET/PLS/PLFの対象 | Y、M、L、B |
| MELSEC RSTの対象 | X、Y、M、L、SM、F、B、SB、S、T、ST、C、D、W、SD、SW、R、Z、LC、LZ |
| MELSEC 比較/PID/MOVの対象 | D、W、SD、SW、R、Z |
| KEYENCE接点デバイス | R、B、MR、LR、CR、T、C |
| KEYENCE OUT/SET/DIFU/DIFDの対象 | R、B、MR、LR |
| KEYENCE RESの対象 | R、B、MR、LR、T、C、DM、EM、FM、ZF、W、TM |
| KEYENCE 比較/PID/MOVの対象 | DM、EM、FM、ZF、W、TM |
| 文書 | 複数回路、回路名、デバイスコメント |
| 出力 | SVG、論理・接続構造JSON |

タイマーの計時命令、カウンタの加算命令、定数比較、MOV以外の算術・データ命令、ラベル、
GX3/KV STUDIOプロジェクトの取込みは未対応です。ワードデバイス同士の比較、PID、MOVには対応しています。
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
