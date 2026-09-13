# Agent entry point

These instructions apply to the entire repository.

Before generating, editing, reviewing, or rendering a ladder circuit, read
`README.md` in full. Its “AST・命令リファレンス（正本）”, “AIの作成手順”, and
“対応範囲” sections are the authoritative authoring contract.

- Author source circuit JSON only; never hand-author SVG, coordinates, wires,
  or the derived render-bundle JSON.
- Use only documented AST forms, output types, targets, and devices. Never
  approximate an unsupported instruction with `coil` or another opcode.
- Run `ladder-fabricator INPUT --validate-only`, then
  `ladder-fabricator rung-text INPUT --comments`, before rendering SVG or PNG.
- Distinguish structural validation from PLC behavior and machine-safety
  validation in every result.
- When changing the parser, schema vocabulary, supported devices, CLI, or
  output semantics, update `README.md`, `docs/FORMAT_JA.md`, examples, and tests
  in the same change.
