"""Append-only source logging for batches 05-07.
Usage: python collection_scripts/log_sources.py rows.json
Each row (dict) is appended to BOTH source_log.csv and source_log_additions_b05_b07.csv
(the additions file is what build_dataset.py re-ingests, so a rebuild cannot drop these rows).
Rows whose source_id already exists in the additions file are skipped (idempotent)."""
import csv, json, sys, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
COLS = ["source_id", "source_name", "source_url", "collection_date", "firecrawl_status", "http_status", "pages_inspected",
        "relevant_records_extracted", "fields_available", "fields_unavailable", "notes", "batch", "source_scope",
        "pages_available", "cited_by_part_records", "cited_by_market_records", "log_note"]
ADD = BASE / "source_log_additions_b05_b07.csv"


def existing_ids(p):
    if not p.exists():
        return set()
    with open(p, encoding="utf-8", newline="") as f:
        return {r["source_id"] for r in csv.DictReader(f)}


def main(path):
    rows = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    seen = existing_ids(ADD)
    new = [r for r in rows if r["source_id"] not in seen]
    for r in new:
        r.setdefault("collection_date", "2026-11-16")
        unknown = set(r) - set(COLS)
        assert not unknown, unknown
    write_header = not ADD.exists()
    with open(ADD, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        if write_header:
            w.writeheader()
        w.writerows(new)
    with open(BASE / "source_log.csv", "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=COLS, lineterminator="\n").writerows(new)
    print(f"appended {len(new)} rows (skipped {len(rows) - len(new)} already logged)")


if __name__ == "__main__":
    main(sys.argv[1])
