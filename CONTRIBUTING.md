# Contributing to Ladder Fabricator

Bug reports, documentation corrections, reproducible vendor-notation findings,
and focused implementation changes are welcome.

## Before opening a pull request

1. Read `AGENTS.md` and the authoritative AST reference in `README.md`.
2. Keep source circuit JSON separate from derived SVG, PNG, and connection JSON.
3. Do not approximate unsupported PLC instructions.
4. Add or update tests for every behavior change.
5. Run `python run_tests.py`.
6. If the parser, schema vocabulary, supported devices, CLI, or output semantics
   change, update the README, `docs/FORMAT_JA.md`, examples, JSON Schema, and
   tests in the same pull request.

## Safety reports

Do not include confidential factory data, production PLC projects, credentials,
or personal information in an issue. Ladder Fabricator performs structural
validation only; reports must not describe generated output as safety-certified.

By contributing, you agree that your contribution is licensed under the MIT
License used by this repository.
