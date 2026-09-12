# 流用元と変更点

Copyright (c) 2026 purinzan. All rights reserved.

本プロジェクトには [gx3-cli-mcp](https://github.com/purinzan/gx3-cli-mcp/tree/ef843a3c898432189d27fb04bf1838cccc9708d0)
から流用したコードが含まれます。参照コミットは
ef843a3c898432189d27fb04bf1838cccc9708d0 です。
元リポジトリの LICENSE.txt を保持しています。

- gx3_ladder_export/device.py は gx3_device_name.py を流用。
  その汎用パーサーの外側で、作成用の対応デバイス・表記を厳密に検証します。
- SVGの接点線・b接点の斜線・コイル楕円・コメント表記は
  gx3_ladder_layout.py / gx3_ladder_print.py の描画を基にしています。
  記号の端点と接続経路を一致させ、母線を最下段まで伸ばしています。
  出力コイルは楕円から真円へ変更しています。
- and/or/not/device/contact と出力指定の語彙は
  gx3_intermediate_tool.py の generate_rung/to_nnf を基にしています。
  積和形への変換とGX独自文字列の生成は移植せず、木構造から直接接続と配置を計算します。

入力検証、構造モデル、分岐を保持する配置、接続データ、API/CLIは
独立用途に合わせて追加・実装しています。既存のGX読取り・DB・xref・MCPには依存しません。
