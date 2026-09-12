# 回路JSON v1 / v2

CLIは入力JSONを検証して、メモリ上の共通ASTを作ります。rung-text、描画・参照用JSON、
SVGはこのASTから導出します。SVGは描画用JSONの明示的な接続を描き、空白から配線を
推測して付け加えません。保存用の正規化AST JSONは生成しません。

```text
依頼文 → メモリ上の共通AST → メーカー別命令 → 接続・配置 → SVG
                         └→ rung-text --comments（任意）
```

## 入力

| 項目 | 必須 | 内容 |
|---|---|---|
| schema_version | はい | `1`（MELSEC固定）または`2`（メーカー指定） |
| target | v2では必須 | `vendor`と`series`。現在はMELSEC iQ-FとKEYENCE KV-X |
| title | いいえ | 文書名、160文字以内。SVGのtitleに格納 |
| comments | いいえ | デバイス名→コメント。各2048文字以内、最大512件 |
| rungs | はい | 1〜64回路の配列 |

各回路:

| 項目 | 必須 | 内容 |
|---|---|---|
| id | はい | 文書内で一意。英字開始、英数字・_・-、48文字以内 |
| title | いいえ | 図に表示する回路名、160文字以内 |
| logic | はい | 下記の条件構造 |
| output | はい | device必須。typeはcoil（省略時）、set、rst、pls、plf |

条件の例:

```json
{"device": "X0", "contact": "a"}
```

`"X0"` は上記の省略形。`contact: "b"` はb接点。
`contact: "rising"` はOFFからONへ変わった1スキャンだけ成立する立ち上がり接点、
`contact: "falling"` はONからOFFへ変わった1スキャンだけ成立する立ち下がり接点。
`{"not": "X0"}` でもb接点を表します。
`{"and": ["X0", "X1"]}` は直列、
`{"or": ["X0", "X1"]}` は並列で、各2項以上。入れ子にできます。
`{"inv": {"and": ["X0", "X1"]}}` は条件を評価した後にINV命令で演算結果を反転します。
INVは`logic`の最外側だけで使用できます。途中に置くとPLCの演算順序に依存するため拒否します。

v1およびMELSEC iQ-Fモードでは、接点にX/Y/M/L/B、OUT/SET/PLSの対象にY/M/L/Bを使えます。
RSTは直接デバイスのX/Y/M/L/SM/F/B/SB/S/T/ST/C/D/W/SD/SW/R/Z/LC/LZを対象にできます。
GX Works3と同じく、ビットデバイスはOFF、タイマ・カウンタは現在値を0かつ接点をOFF、
ワードデバイスとインデックスレジスタは値を0にする指定として扱います。
小文字・ゼロ埋めは正規化します（`x01a` → `X1A`）。
X/Y/B/SB/W/SWは16進、その他の対応デバイスは10進の表記です。CPUごとの範囲判定は行いません。
ラベル、ビット指定、桁指定、添字・間接指定はv1では拒否します。

`not` は接点まで降ろしてa/bを反転し、必要ならAND/ORを入れ替えます。
積和形へ展開しないので、共有接点の数は増えません。
立ち上がり・立ち下がり接点を`not`で反転することはできません。INVは`not`へ変換せず、明示命令として保持します。

### KEYENCE KV-Xモード

KEYENCE用入力はv2で対象を指定する。

```json
{
  "schema_version": 2,
  "target": {"vendor": "keyence", "series": "kv-x"},
  "rungs": [
    {
      "id": "reset",
      "logic": {"device": "R0", "contact": "falling"},
      "output": {"type": "rst", "device": "C0"}
    }
  ]
}
```

接点にはR/B/MR/LR/CR/T/C、OUT/SET/DIFU/DIFDの対象にはR/B/MR/LRを使える。
RST相当の`rst`はR/B/MR/LR/T/C/DM/EM/FM/ZF/W/TMを対象にでき、出力時には
KEYENCEの`RES`になる。`pls`は`DIFU`、`plf`は`DIFD`、`inv`は`CON`として出力する。

R/MR/LRはリレーのビット番号（00～15）を検査し、B/Wは16進として正規化する。
`@R`、`@MR`、`@LR`、`@T`、`@C`、`@DM`、`@EM`、`@FM`、`@TM`のローカル指定も
保持する。CR/CMはCPU制御・状態用なので出力先として受け付けない。間接指定`*`、
インデックス修飾、CPUごとの上限判定はまだ入力対象外である。

CLIの`--target keyence-kv-x`で対象を上書きできる。保存・再利用する中間ファイルには、
上書きに頼らずv2の`target`を書くことを推奨する。

出力の`type`は次のとおりです。

| type | MELSEC action | KEYENCE action | 意味 |
|---|---|---|---|
| coil | OUT | OUT | 条件結果を出力 |
| set | SET | SET | 条件成立時にデバイスを保持ON |
| rst | RST | RES | 条件成立時に対象デバイスをリセット |
| pls | PLS | DIFU | 条件の不成立→成立時に1スキャン出力 |
| plf | PLF | DIFD | 条件の成立→不成立時に1スキャン出力 |

未知項目、空のAND/OR、重複回路ID、正規化後に重複するコメントキー、
XMLに含められない制御文字は拒否します。
実CLIは重複JSONキーも拒否し、入力ファイルを上書きする出力先は許可しません。

入力ファイルはUTF-8（BOM可）、最大1 MiB。
文書全体の条件ノード数は512以内、深さは24以内（最上位条件の深さを0とする）。
`and/or/not` もノード数に含みます。上限を超えた場合、部分結果は出力しません。

## Pythonで扱う中核

`parse_circuit(payload)` は検証・正規化した不変の `Circuit` を返します。
`Expr` の木が直列・並列・接点の接続構造を保持し、座標は含みません。
出力コイルは回路ごとに別のフィールドです。

要素IDは回路IDと条件の位置から決まり、同じ入力なら同じIDになります。
条件の追加・並べ替え後にもIDが不変であることは保証しません。
条件構造から接続グラフと描画座標を作り、両者を別々に手入力させません。

## rung-text

`ladder-fabricator rung-text circuit.json --comments`は同じASTから、回路ごとに
`条件 -> 出力`を1行で出力します。コメント付きでは、その条件と出力が実際に参照する
デバイスコメントだけを付加します。三菱電機・KEYENCEの命令名は選択したtargetから決まり、
SVGとは別に論理を解析し直しません。rung-textは確認用で、SVG生成経路には含まれません。

## 出力JSON

`--format json` または `build_bundle(circuit)` の結果:

- `schema: "gx3-ladder-export/render-bundle"` と `schema_version: 1`
- `target`（メーカー別プロファイルID、vendor、series）
- 文書のタイトル・描画サイズ
- 回路ごとの `nodes`（接点・コイル・SET/RST・INV・分岐/合流・母線）
- `connections`（ID、送信元outポート、接続先inポート）
- `output_condition`（出力ID、OUT/SET/RST/PLSのaction、対象デバイスtarget、導出した条件構造）
- `layout`（ノード座標、接続ごとの折れ線、母線の範囲）
- 現在の対応範囲に関する `limitations`

分岐/合流ノードと母線のin/outポートは同じ位置です。
接点のin/out間は、接点条件で導通する要素であり、単なる配線ではありません。

これは導出結果で、現時点ではCLIへの再入力形式ではありません。
再生成には作成用JSONを使ってください。
`render_svg(bundle)` は `build_bundle` の出力専用で、任意に編集された描画JSONを検証しません。

SVGの各接続に `data-connection`、接点・出力に `data-node` を付け、
JSONとの対応を保持します。長いコメントは図上で省略記号付きで短縮し、
SVGのtitleとJSONには全文を保持します。
SET/RST/PLS/PLFまたはSET/RES/DIFU/DIFDは、命令セルとオペランドセルを分割した同じ命令枠に表示します。
対象デバイスのコメントはオペランドセル内に表示します。

## 判定の意味

`--validate-only` はこの形式の構造検証です。
論理的な運転条件の妥当性、PLCの実行、SET/RSTの保持状態、PLSの前回演算結果、現在値の判定ではありません。
立ち上がり接点の構造は保持しますが、実際の成立判定にはPLCの前回スキャン値が必要です。
未対応命令を単純なOUTとして表示することはせず、入力エラーとして返します。

## GX Works3表記とRST対象の根拠

- 三菱電機「[MELSEC iQ-F Series Basic Course (for GX Works3)](https://dl.mitsubishielectric.com/dl/fa/document/schooltext/school_text/jy997d69701/jy997d69701a.pdf)」4.3.2のラダー表示に合わせ、
  SET/RSTは命令と対象デバイスを同じ命令枠へ表示します。
- 三菱電機「[MELSEC iQ-F FX5 Programming Manual (Instructions, Standard Functions/Function Blocks)](https://dl.mitsubishielectric.com/dl/fa/document/manual/plcf/jy997d55801/jy997d55801z.pdf)」
  のRST命令に合わせ、直接指定できるビット、タイマ、カウンタ、ワード、インデックスデバイスを区別します。

CPUやファームウェアによる実デバイス範囲は、この形式の検証対象外です。
