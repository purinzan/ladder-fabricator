# ラダー作成・SVG出力の流用調査

調査日: 2026-09-12

対象: [gx3-cli-mcp の調査時点のソース](https://github.com/purinzan/gx3-cli-mcp/tree/ef843a3c898432189d27fb04bf1838cccc9708d0)

範囲: 既存ソースと合成した小回路による調査。以下の調査結果は移植前の元実装について記録したもの。

## 今回の実装状況

このPRでは、作成用JSONから独立してSVGと接続情報を出力する基本機能を追加した。
a/b接点、AND/OR/NOT、各回路1つのOUT、複数回路とコメントに対応する。
入力検証、共有接点を保つ配置、明示接続、母線の終端修正、Python API/CLIを実装した。
出力ノード数が増える積和形展開は行わず、GX形式文字列・プロジェクトDBを経由しない。

元コードで生成できたSET/RST/PLSを含め、時間依存命令は今回の独立版の対応範囲に含めていない。
GX3取込み、ラベル、比較・データ命令、任意の接続グラフの再入力は今後の対象。
中核は接続構造を表す不変の式の木で、そこからID付き接続グラフと座標を導出する。
詳細は[入力形式](FORMAT_JA.md)と[流用元](../NOTICE.md)を参照。

## 結論

基本回路については、既存の論理JSON、回路生成、描画処理を流用できる。
GX3ファイルやプロジェクトDBを用意せず、論理JSONからコメント付きSVGを生成できた。
ゼロから形式と描画を作り直す必要はない。

ただし「条件式の作成」と「回路の形の保持」は別の要求。
既存の生成器は条件を積和形に展開し、同じ動作条件の別の形へ描き直す。
要求された分岐構造・命令・複数出力をそのまま扱うには、中間形式と配置処理を拡張する。

## 実際に存在する入力形式

以下は既存の `generate_rung(logic, output)` に渡す2つの引数を、
1つのJSON例にまとめたものです。新ツールの公開API仕様として確定したものではありません。

```json
{
  "logic": {
    "and": [
      {"device": "X0"},
      {"or": [{"device": "X1"}, {"device": "X2"}]}
    ]
  },
  "output": {"type": "coil", "device": "Y0"}
}
```

logic は and / or / not / 2項 xor / device / contact=a,b を受け取る。
output は通常デバイスについて coil / set / rst / pls を生成できる。
1回の呼び出しにつき出力は1つ。ラベルは既存の _lid/... 参照を使う仕組みで、
独立ツールのユーザー向け名前・スコープ定義とは分離が必要。

既存の主な経路:

```text
論理JSON
  → generate_rung()
  → GX形式の回路文字列 V1:...cb{fg=fg{...}}
  → LadderRow（メモリ上。プロジェクトDB不要）
  → rung_layout()
  → elements / wires / verticals / folds を持つ配置JSON
  → layouts_to_svg()
  → SVG
```

生成した LadderRow は、既存の条件解析にも渡せる。
現状はGX内部文字列への変換と再解読を介しており、
最終構成では中立な回路要素・接続関係から配置JSONへ直接変換したい。

## 流用候補

| 部分 | 既存実装 | 判定 |
|---|---|---|
| 論理入力と基本回路生成 | [gx3_intermediate_tool.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_intermediate_tool.py): to_nnf / dnf / generate_rung | 基本回路の土台として流用 |
| 合成回路例 | [gx3_synthetic_project.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_synthetic_project.py): DEMO_PROGRAMS / _station_sections | 入力例・回帰テスト素材として流用 |
| 接点・コイル・命令・コメントの描画 | [gx3_ladder_layout.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_ladder_layout.py): layouts_to_svg / _svg_rung 等 | 独立させて流用。ただし母線の修正が必要 |
| 記号・命令表示・オペランド | [gx3_ladder_print.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_ladder_print.py) / [gx3_operand_display.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_operand_display.py) | 描画共通部を抽出。印刷全体は不要 |
| 接続グラフと条件解析 | [gx3_ladder_logic.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_ladder_logic.py): FlowElement / TopologyGraph / RowLogicAnalysis | 構造・計算を参考に流用。入力はGX形式に結合 |
| コメント・デバイス名 | [gx3_comment_store.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_comment_store.py) / [gx3_device_name.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_device_name.py) | GX入力アダプターと中立部に分ける |
| 元回路から生成用ASTへの変換 | [gx3_roundtrip.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/gx3cli/gx3_roundtrip.py): logic_to_ast | 接点・AND・ORの部分集合。全命令の変換には使えない |
| 検証 | tests の生成・配置・記号・roundtrip テスト | 回帰テストとして流用。独立した意味・配線検証が必要 |
| xref DB、MCP、GX再梱包・書込み | 各既存モジュール | 最初の作成→SVG経路には不要 |

layouts_to_svg は辞書だけで動くが、モジュールの import はGX読取りや印刷処理を参照する。
ファイルを丸ごとコピーして独立化するより、描画・モデル・GX入力アダプターで境界を分ける。

## 実行による確認

8ケースを生成: 単接点、直列+b接点、並列、入れ子AND/OR、XOR、SET、RST、PLS。
全ケースでSVG XML生成とコメントの受渡しに成功。
これはXMLとしての成立を確認したもので、SVG全体の配線の正しさを保証する結果ではありません。
各ケースで X0/X1/X2 の全8組合せを照合し、計64組の出力実行条件が一致した。
これは出力実行条件の確認で、SET/RSTの保持・PLSのスキャン動作の検証ではない。

既存の以下4テストファイルも成功:

- [test_gx3_intermediate_tool_regression.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/tests/test_gx3_intermediate_tool_regression.py)
- [test_gx3_ladder_layout.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/tests/test_gx3_ladder_layout.py)
- [test_gx3_ladder_layout_svg.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/tests/test_gx3_ladder_layout_svg.py)
- [test_gx3_roundtrip.py](https://github.com/purinzan/gx3-cli-mcp/blob/ef843a3c898432189d27fb04bf1838cccc9708d0/tests/test_gx3_roundtrip.py)

製品コードを変更していないため、全テストスイートは今回実行していない。

調査用スクリプトと生成物はローカルで保持し、この文書には確認方法と結果を記載する。
上のJSON例は設計説明用で、プロジェクトから抽出したデータではない。

## そのまま移さない点

1. **分岐構造の保持**
   X0 AND (X1 OR X2) は (X0 AND X1) OR (X0 AND X2) に展開され、
   X0接点が2個になる。生成は成功するが、元の共有構造は保持しない。
   7組の2択並列を直列にすると128枝に増え、既定の64枝上限で拒否された。
   上限判定は展開後なので、入力の大きさ・深さを事前に制限する必要もある。

2. **命令の生成範囲**
   timer / mov / call / plf を通常デバイスの output.type に指定すると拒否された。
   既存SVGが命令箱を描けることと、JSONからその命令を生成できることは別。
   タイマーの設定値、比較命令、複数出力、エッジ接点などを明示できるモデルが必要。

3. **入力検証**
   JSON Schemaによる厳密な生成入力検証は今回の経路にはない。
   未知フィールドは無視され、空のANDは接点なし回路として受理された。
   空ANDを許すかも含め、仕様・エラー位置・対応命令を明示する。
   validate_intermediate はGXプロジェクトの再構築確認用で、この代用にはならない。

4. **SVGの母線**
   2段の並列回路で左母線の終端 y=108 に対して下段の配線中心は y=151。
   母線が最下段に届かない。生成SVGの座標とプレビューで確認した。
   XML生成・文字列存在テストだけでは検出できず、接続端点の幾何検証が必要。

5. **描画時の配線補完**
   現状は座標の隙間から横線を補う。
   任意の作成JSONを受け取る描画器として使うなら、
   明示した接続だけを描く契約と、それを検証する仕組みが必要。

6. **論理等価の検証**
   roundtrip の非同一データの判定は使用デバイス・役割・アクセスの集合比較。
   X0 AND X1 と X0 OR X1 でもこの集合は一致した。
   その成功だけで論理等価とは扱わず、対応する組合せ回路には真理値表などを使用する。
   時間依存命令は別の検証が必要。

7. **中立性・構造の保持**
   配置JSONにはスキーマ版、安定した要素ID、接続ポート、解析状態の標準欄がない。
   座標は12セル幅への折返し後で、元の座標とは分離されていない。
   元データと表示配置、論理条件を別の情報として保持する。

## 中核にする形式と責務

中核は「人の要求からAIが作成し、機械で検証できるラダー回路データ」とする。
既存GX3の抽出は入力経路の一つであり、新しい回路の作成にGX3は必須としない。

```text
人の要求 → AIが作る回路JSON → 入力・構造検証 → 中核の回路データ
既存GX3 → 解読・変換 ────────────────────────┘
                                                 ├→ 自動配置 → 配置JSON → SVG
                                                 └→ 条件解析 → 条件式・解析制約
```

以下は全体の実装方針。基本範囲の実装状況と未対応範囲は上記と入力形式文書を参照。

| 層 | 保持・処理する内容 |
|---|---|
| 作成入力 | 既存の and/or/not/device と出力指定を入口として活用。未知項目と未対応命令は明示的に拒否 |
| 中核の回路データ | スキーマ版、回路・要素の安定ID、接点種別、命令、順序付きオペランド、出力、接続ポートと接続先、コメント |
| 元データの情報 | GX3から取り込む場合の元位置・ラベルscope・読取り制約。AIが新規作成する場合にはGX由来の位置を要求しない |
| 配置 | 中核の接続関係から表示座標と折返しを計算。元座標とは分離 |
| 描画 | 配置済み要素と明示された接続からSVGを作成 |
| 条件解析 | 同じ中核データから導出。タイマー・保持・エッジ等は単純な真偽式に潰さず制約や状態依存を残す |

条件式と接続関係をそれぞれ独立に手入力させず、中核の回路データを基準にする。
X0 AND (X1 OR X2) の共有接点や分岐を保持し、表示のための積和形展開は必須としない。
接続グラフを持つだけで全命令の意味が定義できるわけではないため、
命令順序・実行制御・状態依存の仕様は対応範囲ごとに定義する。

## 実装順と完了条件

1. **基本形式と入力検証**
   a/b接点、直列・並列、単一OUT、コメントを最初の対応範囲とする。
   既存JSONを入口に使い、型・必須項目・接続先・入力の深さと大きさを検証する。
   不正入力は項目の位置と理由付きで拒否できること。

2. **既存描画の抽出**
   接点・コイル・コメント等の描画をGX読取りから分離する。
   母線の長さを修正し、空白から勝手に接続を補わない描画へ整える。
   全接続の端点、並列枝と母線の接続、共有接点の保持を検証する。

3. **作成から出力までの接続**
   回路JSONからSVGと条件式を出せる小さなAPI/CLIを用意する。
   GX3やプロジェクトDBを持たずに、合成した基本回路を生成できること。
   組合せ回路は真理値表等で入力の条件と生成した構造を比較する。

4. **命令とGX3入力の拡張**
   複数出力、タイマー、比較、データ命令、ラベルscopeを必要な順に追加する。
   未対応は明示する。GX3の解読は追加アダプターとして実装し、
   要求からの回路作成と同じ中核データへ変換する。
   時間依存命令は、描画できることと実行時動作の検証を分ける。

既存の生成器を使う短期の試作ではGX形式文字列の経由を許容するが、
それを新ツールの公開中間形式とはしない。型付きの回路要素と接続関係へ段階的に分離する。
