# Ladder Fabricator

回路の条件をJSONで記述し、デバイスコメント付きのラダーSVGと論理・接続構造JSONを生成するPythonツールです。

Pythonパッケージ名とCLIコマンドは`gx3-ladder-export`です。

GX Works3やGX3ファイルを使わず、依頼内容から作った小さなJSONだけでラダー図を生成できます。
座標や配線を手書きする必要はありません。Python 3.10以上で動作し、実行時の追加依存もありません。

## できること

- a接点・b接点・立ち上がり接点と、直列（AND）・並列（OR）・否定（NOT）を組み合わせる
- OUT、SET、RST、立ち上がりパルスPLSと、演算結果を反転するINV命令を表す
- 条件構造から接点、分岐、合流、円形コイル、命令枠、母線を自動配置する
- `X0 AND (X1 OR X2)` のような共有接点を複製せずに描く
- デバイスコメントをSVGへ表示し、全文をSVGのtitleと構造JSONへ保持する
- 同じ入力から、安定した要素IDと明示的な接続関係を生成する
- 未対応の命令や壊れた入力を、曖昧な図にせずエラーとして返す

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

インストールせず、リポジトリ内から実行することもできます。

```powershell
python -m gx3_ladder_export examples/basic.json -o outputs/basic.svg
```

## AIとこのツールの役割

このパッケージ自体は自然言語を解釈しません。AIまたは利用者が要求を回路JSONへ変換し、
このツールが形式の検証、論理構造の保持、配置、SVG生成を担当します。

この分離により、入力した論理をJSONで確認してから図を生成できます。同じJSONからSVGと
構造JSONを繰り返し生成でき、AIや描画環境を実行時の依存にしません。

## 入力形式

`logic` には次の4形式を入れ子で指定します。

| JSON | 意味 | ラダー表現 |
|---|---|---|
| `"X0"` | X0がON | X0のa接点 |
| `{"not": "X0"}` | X0がOFF | X0のb接点 |
| `{"device": "X0", "contact": "rising"}` | X0のOFF→ON | 立ち上がり接点 |
| `{"and": ["X0", "X1"]}` | 両方が成立 | 直列 |
| `{"or": ["X0", "X1"]}` | どちらかが成立 | 並列 |
| `{"inv": {"and": ["X0", "X1"]}}` | そこまでの演算結果を反転 | INV命令 |

出力の`type`は通常コイルの`coil`、保持ONの`set`、デバイスをリセットする`rst`、
条件の立ち上がりで1スキャン出力する`pls`を指定できます。SVGではGX Works3のMOVなどと同じ規則で、
白い命令枠を命令セルとオペランドセルに分けます。`SET | Y0`、`RST | C0`、`PLS | M1`のように
対象デバイスを枠内へ、デバイスコメントを対応するセルの下へ表示します。
INVはPLCの演算順序を明確にするため、`logic`の最外側だけで使用します。

[命令サンプル](examples/instructions.json)には、立ち上がり接点→SET、RST、PLS、AND結果→INV→OUTを収録しています。

複数の回路は`rungs`へ並べます。詳しい制約、正規化規則、入力上限は
[回路JSON v1](docs/FORMAT_JA.md)を参照してください。

## 生成物

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

from gx3_ladder_export import build_bundle, parse_circuit, render_svg

payload = json.loads(Path("examples/basic.json").read_text(encoding="utf-8"))
circuit = parse_circuit(payload)
bundle = build_bundle(circuit)
Path("basic.svg").write_text(render_svg(bundle), encoding="utf-8")
```

処理は`parse_circuit`（検証・正規化）、`build_bundle`（接続・配置）、
`render_svg`（SVG化）の3段階です。中間の`bundle`を使えば、別の表示形式も追加できます。

## 対応範囲

| 項目 | 対応 |
|---|---|
| 接点 | a接点、b接点、立ち上がり接点 |
| 論理 | AND、OR、NOT、入れ子、最外側のINV |
| 出力 | 各回路に1つのOUT、SET、RST、PLS |
| 接点デバイス | X、Y、M、L、B |
| OUT/SET/PLSの対象 | Y、M、L、B |
| RSTの対象 | X、Y、M、L、SM、F、B、SB、S、T、ST、C、D、W、SD、SW、R、Z、LC、LZ |
| 文書 | 複数回路、回路名、デバイスコメント |
| 出力 | SVG、論理・接続構造JSON |

タイマー回路の生成、立ち下がり接点、比較・データ命令、ラベル、GX3の取込みは未対応です。
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

- [入力形式と出力仕様](docs/FORMAT_JA.md)
- [流用調査と設計方針](docs/REUSE_AUDIT_JA.md)
- [流用元と変更点](NOTICE.md)

## データの扱い

入力と出力はローカルファイルです。利用者のPLCプロジェクト、生成物、設備情報を外部へ送信しません。
リポジトリの`examples/`には手作りの合成回路だけを置きます。

## ライセンス

本リポジトリは独自ライセンスです。利用条件は[LICENSE.txt](LICENSE.txt)を確認してください。
