# Pre-Colab verification: results against the checker PDF (2026-11-16)

> **Superseded in part by the final rerun (scoring rules v4).** Sections 1-3 and 5 still hold. The section 4 scoring results below are from the earlier 0.75 scarcity rule. For the final ranking, tiers and the Ethiopian-factor check, see `analysis.ipynb` section 6, `limitations.md` section 5 and `PROGRESS.md` (F-stages).

| Checker item | Result |
|---|---|
| **1. Data integrity** | |
| validation_results.json: 0 FAILED, old WARNING gone | PASS: 59 PASSED, 0 FAILED, 0 WARNING, 4 NOT VERIFIED (C6 no pre-baseline, G4 URL reachability, G5 AUTODOC wiper pairing, G6 n/a). C4 now PASSED. |
| Cleaned CSV: exactly 30 rows, no duplicate vehicle-category pairs | PASS: 30 rows, 0 duplicates |
| Raw batches 01-04 unchanged (hash check) | PASS: C6b |
| **2. Live spot-check of 5 new records** (one per batch, one per vehicle) | |
| B05 Seagull side mirror: Landin SKU BYD0040271, OE EQEA-8202100, ¥429 RMB, "SEAGULL 2020-" | PASS: matches live page |
| B05 ID.4 strut mount (related part): BRYMAN 1EA412331B, from AED 94.07 incl. VAT, "May fit - check by VIN" | PASS: matches live page |
| B06 Yuan Up bumper, Jiji: "Found 6 ads"; ETB 169,999 / 168,000 / 200,000 | PASS on prices. The check found a missed misspelled listing ("Bunper", ETB 185,000); the matcher was fixed and the count corrected to 4 |
| B06 ID.4 bumper, Jiji: "Found 4 ads"; ETB 250,000 / 245,000 | PASS on prices. Same misspelling issue ("Bunper", ETB 180,000); count corrected to 3 |
| B07 ID.4 headlight recall 21V413000, EXTERIOR LIGHTING:HEADLIGHTS | PASS: matches live NHTSA API |
| Result | No wrong price, currency, part number or fitment text. 2 of 5 undercounted listings from one misspelling, fixed across the whole batch; no other misses found when every model-matched title was re-scanned. |
| **3. Honesty checks** | |
| Price without currency / currency converted to ETB | PASS: none (check D5, I8) |
| Fitment "confirmed" from catalogue context only | PASS: none; catalogue context is kept in a separate field |
| Listing count described as demand, sales or registrations | PASS: always labelled as a listing count |
| NHTSA data on Seagull / Yuan Up | PASS: none (check I5) |
| "Scarce" claim from "0 found" | PASS: none (check I7) |
| Part number not in a source file (D1) | PASS |
| **4. Scoring sanity** | |
| Every factor 0-1, no silent zeros | PASS: 0 missing; explicit zeros are documented in the *_basis columns |
| Weights sum to 100% | PASS (proposal: 30/20/20/15/15, awaiting review) |
| Sensitivity: top 5 changes completely? | Partly. Mean overlap 3.7 of 5 across 11 scenarios. Stated in limitations.md |
| No top-5 part depends only on Ethiopian availability | **FAIL (reported)**: 4 of 5 drop out when the scarcity factor is removed. Needs a decision (keep the rule, or score "not found" as neutral 0.5) |
| **5. Notebook readiness** | |
| Runs top to bottom without errors (fresh kernel via nbconvert) | PASS |
| Reads only data/; no network, API keys or absolute paths | PASS |
| First cell handles Colab (upload or Drive mount) | PASS |
| **6. Colab run** | TO DO (user): upload data/ + analysis.ipynb, Run all, compare the top 5 |
| **Final readiness** | Raw data, cleaned data, notebook, source log, scoring formula + justification, top 5, limitations: all present. Limitations name ETB prices, VIN fitment, stock, Telegram/Facebook, BYD failure data. Reuse note: GitHub table left blank. |
