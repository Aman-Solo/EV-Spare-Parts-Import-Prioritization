# EV Spare-Parts Evidence Dataset (v3: Batches 01-07)

Evidence preparation only: no scoring, ranking or recommendation.

1. `raw/` holds the research batches 01-07, saved API/search responses and the original source log. **Never edit them.**
   New source rows go into `source_log_additions_b05_b07.csv` via `collection_scripts/log_sources.py` (append-only).
2. `python build_dataset.py` regenerates every other file from `raw/` and re-runs 50+ checks
   (needs only Python 3.9+, no packages; the scoring notebook in `../data/` + `analysis.ipynb` needs pandas). Exit code 1 if any check FAILS.
3. Read `data_quality_report.md` first, then `data_dictionary.md`.
4. In Colab: `pd.read_csv("cleaned_vehicle_part_evidence.csv")`; join to
   `vehicle_market_evidence.csv` on `vehicle_id` and to `product_observations.csv` on `record_id`.
   Do not mix market rows into the part table. Listing counts are visibility proxies,
   not registrations or sales.
