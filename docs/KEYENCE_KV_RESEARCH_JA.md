# KEYENCE KV版の命令・デバイス調査

調査日: 2026-09-12

## 結論

KEYENCE KV版は、GX Works3向けSVGの文字と色だけを切り替えて作ることはできない。
接点と通常コイルの論理構造は流用できるが、命令名、オペランド、時間単位、保持・リセット条件、
デバイス体系、プログラム構造をKEYENCE用に変換する必要がある。

実装の中核は、メーカーに依存しない意味を保持する中間形式と、次の情報を持つ
`keyence-kv-x`プロファイルである。

- 命令名とオペランド形式
- 対応CPUシリーズと命令の利用可否
- デバイス種別、範囲、保持性、ローカル指定、間接指定
- タイマの時間基準とカウンタのリセット方式
- KV STUDIOに合わせた記号、セル寸法、線、文字、コメント表示

`data/keyence_kv/`には、確認済みの差分と出典を機械可読JSONで保存した。
`tools/build_keyence_reference_db.py`で検索用SQLiteを再生成できる。公式PDFそのものは著作物かつ
登録情報を必要とするためGitには含めない。

## 対象範囲

最初の出力対象は現行のKV-Xシリーズとし、KV-8000/7000/5000/3000/1000およびKV Nanoとの
共通命令を互換性調査の範囲に含める。Visual KVは旧命令の由来と意味の確認だけに使う。

命令調査は、次の分類を漏れなく扱う。

| 分類 | 例 | 現在の状態 |
|---|---|---|
| 接点・論理結合 | LD、LDB、ANP、LDPB、BLD | 中核差分を登録済み |
| 出力・状態保持 | OUT、SET、RES、DIFU、DIFD、ALT | 中核差分を登録済み |
| タイマ・カウンタ | TMR、TMH、TMS、C、OUTC、UDC、UDT | 意味差分を登録済み |
| データ転送 | MOV、BMOV、FMOV | 基本対応を登録済み |
| 比較 | LD=、LD<>、CMPと型サフィックス | 基本対応を登録済み |
| 算術・論理演算 | CAL+、CAL-、CAL*、CAL/、CAL& | 基本対応を登録済み |
| 変換 | TBIN、TBCD | 基本対応を登録済み |
| シフト・テーブル | SFR、SORTN、RAMP | 公式命令表の取得後に全件化 |
| フロー制御 | MC/MCR、STG/JMP/ENDS、FOR/NEXT | 主要構造を登録済み |
| サブルーチン・FB | CALL/SBN/RET、ECALL、FBSTRT/FBCALL | 構造差分を登録済み |
| 割込み・高速処理 | INT/RETI、HSP、CTH、FCNT、RCNT | 分類と旧世代資料を確認済み |
| 位置決め・パルス | PLSOUT、PLSX/Y、JOGX/Y、ORGX/Y | 分類と旧世代資料を確認済み |
| PID・モーション | PID、PIDATなど | 公式命令表の取得後に全件化 |
| 通信・ネットワーク | EtherNet/IP、MC、ソケット関連 | 公式命令表の取得後に全件化 |
| ファイル・メモリカード | MWRIT、MREADなど | 分類と旧世代資料を確認済み |
| センサ・ユニット | SPWR、SPRD、SSVCなど | 分類と旧世代資料を確認済み |
| ST・構造化プログラム | 演算子、関数、型、変換 | 専用マニュアル取得後に全件化 |

ここで「登録済み」は、SVG生成に必要な意味差分をデータベースへ入れた状態を表す。
現行KV-Xの全命令・全サフィックス・CPU別制限の確定には、登録制の公式コマンドリファレンスを
取得して照合する必要がある。

## 取得したマニュアル群

| 資料 | 世代 | 入手状態 | 用途 |
|---|---|---|---|
| KV-Xシリーズ コマンドリファレンスマニュアル | KV-X | 公式ページと資産ID確認済み、PDF取得待ち | 現行命令の正本 |
| KV-X500シリーズ ユーザーズマニュアル | KV-X500 | 公式ページと資産ID確認済み、PDF取得待ち | CPU・デバイス・実行仕様 |
| KV STUDIO Ver.12 for KV-Xシリーズ | KV-X | 公式ページと資産ID確認済み、PDF取得待ち | 入力書式と画面表記 |
| KV-8000→KV-X置き換えガイド | KV-8000/KV-X | 公式ページと資産ID確認済み、PDF取得待ち | 世代差 |
| 共通命令編 | KV-8000～KV Nano | 公式ページと資産ID確認済み、PDF取得待ち | 共通命令の正本 |
| KV-8000シリーズ ユーザーズマニュアル | KV-8000 | 公式ページと資産ID確認済み、PDF取得待ち | CPU・デバイス・実行仕様 |
| KV-5500/5000/3000 User's Manual | KV-5500～3000 | 公開ミラーをローカル保存 | 実行仕様と旧世代照合 |
| Visual KV Programming | Visual KV | 公開ミラーをローカル保存 | 旧命令80種の照合 |
| KEYENCE Ethernet device map | KV-700～KV-X | Pro-face資料をローカル保存 | デバイス・通信アドレス照合 |

資料のURL、資産ID、公開日、言語、ローカルファイル名は
`data/keyence_kv/manuals.json`に保存している。ローカルPDFが存在するときは、SQLite生成時に
SHA-256も記録するため、後の更新や差し替えを検出できる。

## GX Works3とKVの主要差分

### 接点と出力

| 意味 | MELSEC/GX Works3 | KEYENCE KV | 実装上の扱い |
|---|---|---|---|
| a接点 | LD / AND / OR | LD / AND / OR | 共通論理を流用 |
| b接点 | LDI / ANI / ORI | LDB / ANB / ORB | KV出力時に命令名変換 |
| 立ち上がり接点 | LDP / ANDP / ORP | LDP / ANP / ORP | 直列命令名が異なる |
| 立ち下がり接点 | LDF / ANDF / ORF | LDF / ANF / ORF | 直列命令名が異なる |
| エッジb接点 | CPU・表現依存 | LDPB等の専用系列 | 中間形式に極性とエッジを別々に保持 |
| 通常出力 | OUT | OUT | 対象デバイス制約を切替 |
| セット | SET | SET | 名前は同じだが対象範囲を切替 |
| リセット | RST | RES | 必ず命令名変換 |
| 立ち上がり1スキャン出力 | PLS | DIFU | 状態を持つ出力として変換 |
| 立ち下がり1スキャン出力 | PLF | DIFD | 状態を持つ出力として変換 |

KV固有のLDPB/LDFB、ANPB/ANFB、ORPB/ORFBは「b接点」と「立ち上がり・立ち下がり」を
一つの文字列として保持せず、`contact.polarity`と`contact.edge`に分ける。これにより、
メーカーごとの命令系列へ安全に展開できる。

### タイマとカウンタ

MELSECで一般的な`OUT T0 K10`に対して、KVは時間基準を命令名で表す。

- `TMR`: 100 ms単位
- `TMH`: 10 ms単位
- `TMS`: 1 ms単位

したがって中間形式は命令文字列を保存せず、`duration_ms`を正規値として持つ。
KVへ出力するときに、値を正確に表せる命令と設定値を選ぶ。丸めが必要なら暗黙に変換せず
検証エラーにする。

カウンタも同名対応ではない。KVの`C`は実行条件OFFでリセットされ、`OUTC`は`RES`まで保持する。
`UDC`はリセット入力を命令構造に含む。中間形式には少なくとも方向、プリセット値、
保持方式、リセット条件を明示する必要がある。

### 演算・比較・型

現代のKVでは四則演算に`CAL+`、`CAL-`、`CAL*`、`CAL/`を使い、データ幅と型は
`.D`、`.L`、`.F`などのサフィックスで表す。MELSECの`ADD`等と名前だけで対応付けると、
符号、幅、浮動小数点、オーバーフローの意味を失う。

比較接点の`LD=`等は名前が近いが、KVの`.U/.S/.D/.L/.F/.DF`と自動変換形式を含め、
中間形式に符号、ビット幅、数値型を保持する。BCD/BIN変換もMELSECの`BCD`/`BIN`に対して
KVは`TBCD`/`TBIN`となる。

### プログラム構造

KVのサブルーチンは`CALL`だけでは表現できず、入口`SBN`と復帰`RET`を含む。
別モジュール呼出しの`ECALL`も区別する。`MC/MCR`、`STG/JMP/ENDS`、`FOR/NEXT`は
対応する範囲を構造として保持し、離れた命令を単独ノードへ平坦化しない。

KV-8000のFBは`FBSTRT`/`FBCALL`とインスタンス、ENOを持つ。通常の命令セルとは別の
FBノードとして扱う。

## デバイス体系

| KVデバイス | 主用途 | MELSECから見た注意点 |
|---|---|---|
| R | 入出力・内部リレー | 表示設定によりX/Y/M表記もあり、物理I/Oと内部用途を属性で区別する |
| B | リンクリレー | ネットワーク割付を伴う |
| MR | 内部補助リレー | Mの主な移行候補だが単純な文字置換にはしない |
| LR | ラッチリレー | 保持範囲設定を確認する |
| CR | コントロールリレー | CPU状態用で自由な内部リレーとして割り当てない |
| T / C | タイマ / カウンタ | 命令とリセット方式を一緒に保持する |
| DM | データメモリ | Dの主な移行候補。ユニット割付との競合を確認する |
| EM | 拡張データメモリ | CPUごとの範囲確認が必要 |
| FM / ZF | ファイルレジスタ | バンク方式と連番方式を区別する |
| W | リンクレジスタ | 通信領域としての割付を保持する |
| TM | テンポラリメモリ | 演算補助用途を含み、永続データに使わない |
| Z | インデックスレジスタ | 添字と間接指定を意味として分離する |
| CM | コントロールメモリ | CPU制御・状態用。通常領域として自動割当しない |

KVでは`@`がプログラムローカルデバイス、`*`が間接指定を表す。例えば`@DM`と`*DM`は
見た目が似ていても意味が異なる。中間形式では`scope: local`と`addressing: indirect`を
独立した属性にする。

## 推奨する中間形式

現在の回路JSONを破壊せず、`target`と意味属性を追加する。

```json
{
  "schema_version": 2,
  "target": {"vendor": "keyence", "series": "kv-x"},
  "rungs": [
    {
      "logic": {
        "and": [
          {"device": "R000", "contact": "normal"},
          {"device": "MR100", "contact": "falling", "polarity": "bar"}
        ]
      },
      "output": {"type": "reset", "device": "C0"}
    }
  ]
}
```

`reset`を中立的な意味として保持し、GX Works3では`RST`、KV STUDIOでは`RES`を描く。
同様に`pulse_rise`はGXでは`PLS`、KVでは`DIFU`へ展開する。

タイマは次のように時間を正規化する。

```json
{
  "output": {
    "type": "timer_on_delay",
    "device": "T0",
    "duration_ms": 1000,
    "retentive": false
  }
}
```

この形式なら、KV向けに`TMR T0 #10`を選べる。CPUや命令で表現できない時間は出力前に検出できる。

## 実装順序

1. 既存JSON v1を読み続けられるv2パーサを追加する。
2. 中立的な接点極性・エッジ・出力意味へ正規化する。
3. `melsec-iq-f`と`keyence-kv-x`のメーカー別プロファイルを追加する。
4. KEYENCEのR/MR/LR/CR/T/C/DM/EM/FM/ZF/W/TM/Z/CMを検証する。
5. RES、DIFU/DIFD、立ち下がり、エッジb接点、TMR/TMH/TMS、C/OUTC/UDCを実装する。
6. CALL/SBN/RET、MC/MCR、FBを範囲・入口・出口付きの構造として追加する。
7. KV STUDIOの画面を計測し、KEYENCE描画テーマを追加する。
8. 現行KV-Xコマンドリファレンスを取り込み、全命令、型サフィックス、CPU制限を登録する。
9. 合成回路でSVGと構造JSONを検証し、実機投入形式への変換は別機能として扱う。

## データベースの使い方

```powershell
python tools/build_keyence_reference_db.py
```

差分だけを表示する例:

```powershell
sqlite3 reference/keyence/kv_reference.sqlite3 `
  "SELECT concept_ja, gx3_json, kv_json, relation FROM instruction_mappings WHERE relation <> 'same';"
```

根拠資料まで追う例:

```sql
SELECT m.concept_ja, m.kv_json, s.title, s.url
FROM instruction_mappings AS m
JOIN instruction_sources AS x ON x.mapping_id = m.id
JOIN sources AS s ON s.id = x.source_id
WHERE m.id = 'reset';
```

## 調査の限界と完了条件

現在のデータは、SVG生成の最初の対象となる基本回路、時間・状態依存命令、制御構造、
デバイス体系を優先した「確認済み中核」である。現行KV-Xの全命令名、全オペランド、
全型サフィックス、CPU機能バージョン別制限までを網羅した状態ではない。

完了条件は、登録制の現行公式PDFを取得し、各命令について次を1行ずつ登録して、
公式資料の版とページへ結び付けることである。

- 命令名、別名、分類、説明
- オペランド数、順序、許可デバイス、定数表記
- データ型、幅、サフィックス
- 実行条件とスキャン間状態
- 対応CPU、機能バージョン、使用禁止領域
- GX Works3側の同等命令、近似命令、対応なし
- SVG記号と必要な構造ノード

## 出典

1. [KEYENCE: KV-Xシリーズ マニュアル一覧](https://www.keyence.co.jp/support/user/controls/kv-x/manual/)
2. [KEYENCE: KVシリーズ（ビルディングタイプ）マニュアル一覧](https://www.keyence.co.jp/support/user/controls/plc/manual/building/)
3. [KEYENCE: KV-8000 CPUユニット仕様](https://www.keyence.co.jp/products/controls/plc-building/kv-8000/models/kv-8000)
4. [KEYENCE: ワードデバイスの使い分け](https://www.keyence.co.jp/support/user/controls/faq/answer.jsp?faq_id=92432)
5. [KEYENCE: FBSTRT/FBCALLに関するFAQ](https://www.keyence.com/support/user/controls/faq/answer.jsp?faq_id=93499)
6. [PLC-RUN!: PLC基本命令 各社対応表](https://plc-run.com/archives/8)
7. [PLC-RUN!: LD/LDB/AND/ANB/OR/ORB](https://plc-run.com/archives/49)
8. [PLC-RUN!: エッジ接点命令](https://plc-run.com/archives/69)
9. [PLC-RUN!: エッジb接点命令](https://plc-run.com/archives/90)
10. [PLC-RUN!: ワード内ビット接点命令](https://plc-run.com/archives/109)
11. [PLC-RUN!: 比較接点と型サフィックス](https://plc-run.com/archives/136)

二次資料で確認した行はデータベースの`confidence`に明示している。コード生成を有効にする前に、
登録制の現行公式コマンドリファレンスで再確認する。
