"""Build a searchable SQLite database from the reviewed KEYENCE reference JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "keyence_kv"
DEFAULT_OUTPUT = ROOT / "reference" / "keyence" / "kv_reference.sqlite3"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_database(data_dir: Path = DEFAULT_DATA, output: Path = DEFAULT_OUTPUT) -> dict[str, int]:
    manuals = load_json(data_dir / "manuals.json")
    differences = load_json(data_dir / "instruction_differences.json")
    if manuals.get("schema_version") != 1 or differences.get("schema_version") != 1:
        raise ValueError("unsupported KEYENCE reference schema")

    sources = {row["id"]: row for row in manuals["sources"]}
    for mapping in differences["mappings"]:
        missing = set(mapping["sources"]) - sources.keys()
        if missing:
            raise ValueError(f'{mapping["id"]}: unknown sources {sorted(missing)}')
    for device in differences["devices"]:
        if device["source"] not in sources:
            raise ValueError(f'{device["code"]}: unknown source {device["source"]}')

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    connection = sqlite3.connect(output)
    try:
        connection.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE sources (
                id TEXT PRIMARY KEY, publisher TEXT NOT NULL, title TEXT NOT NULL,
                series_json TEXT NOT NULL, language TEXT NOT NULL,
                publication_date TEXT, url TEXT NOT NULL, asset_id TEXT,
                access TEXT NOT NULL, local_filename TEXT, local_sha256 TEXT
            );
            CREATE TABLE instruction_mappings (
                id TEXT PRIMARY KEY, category TEXT NOT NULL, concept_ja TEXT NOT NULL,
                gx3_json TEXT NOT NULL, kv_json TEXT NOT NULL, relation TEXT NOT NULL,
                confidence TEXT NOT NULL, rendering_impact TEXT NOT NULL, notes TEXT NOT NULL
            );
            CREATE TABLE instruction_families (
                id TEXT PRIMARY KEY, name_ja TEXT NOT NULL, status TEXT NOT NULL,
                examples_json TEXT NOT NULL
            );
            CREATE TABLE instruction_sources (
                mapping_id TEXT NOT NULL REFERENCES instruction_mappings(id),
                source_id TEXT NOT NULL REFERENCES sources(id),
                PRIMARY KEY (mapping_id, source_id)
            );
            CREATE TABLE devices (
                vendor TEXT NOT NULL, code TEXT NOT NULL, name_ja TEXT NOT NULL,
                bit_width INTEGER NOT NULL, scope TEXT NOT NULL, notes TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES sources(id),
                PRIMARY KEY (vendor, code, scope)
            );
            CREATE INDEX instruction_category_idx ON instruction_mappings(category);
            CREATE INDEX instruction_relation_idx ON instruction_mappings(relation);
            CREATE INDEX instruction_confidence_idx ON instruction_mappings(confidence);
        """)
        connection.executemany("INSERT INTO metadata VALUES (?, ?)", [
            ("manuals_as_of", manuals["as_of"]),
            ("scope", differences["scope"]),
            ("coverage", json.dumps(differences["coverage"], ensure_ascii=False)),
        ])
        manual_dir = ROOT / "reference" / "keyence" / "manuals"
        for row in sources.values():
            local = manual_dir / row["local_filename"] if row["local_filename"] else None
            connection.execute(
                "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["id"], row["publisher"], row["title"],
                 json.dumps(row["series"], ensure_ascii=False), row["language"],
                 row["publication_date"], row["url"], row["asset_id"], row["access"],
                 row["local_filename"], file_hash(local) if local else None),
            )
        for row in differences["mappings"]:
            connection.execute(
                "INSERT INTO instruction_mappings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row["id"], row["category"], row["concept_ja"],
                 json.dumps(row["gx3"], ensure_ascii=False),
                 json.dumps(row["kv"], ensure_ascii=False), row["relation"],
                 row["confidence"], row["rendering_impact"], row["notes"]),
            )
            connection.executemany(
                "INSERT INTO instruction_sources VALUES (?, ?)",
                [(row["id"], source_id) for source_id in row["sources"]],
            )
        connection.executemany(
            "INSERT INTO instruction_families VALUES (?, ?, ?, ?)",
            [(row["id"], row["name_ja"], row["status"],
              json.dumps(row["examples"], ensure_ascii=False))
             for row in differences["families"]],
        )
        connection.executemany(
            "INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(row["vendor"], row["code"], row["name_ja"], row["bit_width"],
              row["scope"], row["notes"], row["source"])
             for row in differences["devices"]],
        )
        connection.commit()
    finally:
        connection.close()
    return {"sources": len(sources), "families": len(differences["families"]),
            "mappings": len(differences["mappings"]), "devices": len(differences["devices"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    counts = build_database(args.data_dir, args.output)
    print(f'written: {args.output} ({counts["sources"]} sources, '
          f'{counts["families"]} families, {counts["mappings"]} mappings, '
          f'{counts["devices"]} devices)')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
