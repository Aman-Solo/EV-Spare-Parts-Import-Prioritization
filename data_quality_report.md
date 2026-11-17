# Data Quality Report (v3: Batches 01-07)

Build: 2026-11-16 20:11 UTC - Python 3.12.10 - `build_dataset.py`. No web research, scoring, ranking, recommendation or currency conversion was performed. Raw batch files were read, never written.

## 1. Result at a glance
**59 PASSED - 0 FAILED - 4 NOT VERIFIED - 0 WARNING.** The dataset is structurally valid and traceable; the NOT VERIFIED items below are limits of what could be checked here, not hidden failures. All checks ran against the generated files on disk (see `validation_results.json`).

## 2. Validation checks
| ID | Check | Status | Detail |
|---|---|---|---|
| A1 | Exactly 3 vehicles | **PASSED** | id4, seagull, yuan_up |
| A2 | Exactly 10 categories, each present for every vehicle | **PASSED** | 10 categories; rows per vehicle {'seagull': 10, 'yuan_up': 10, 'id4': 10} |
| A3 | 30 unique vehicle-category combinations; none missing, none duplicated | **PASSED** | 30 combinations |
| A4 | Row counts: raw CSV / cleaned CSV / cleaned JSON / Batch 04 raw | **PASSED** | 30 / 30 / 30 / 30 |
| B1 | record_id unique (cleaned) | **PASSED** |  |
| B2 | observation_id unique (product observations) | **PASSED** | 5 observations |
| B3 | market_record_id unique (vehicle market) | **PASSED** | 27 rows |
| B4 | Raw CSV and cleaned CSV share the same 30 record_ids | **PASSED** |  |
| B5 | cleaned CSV == cleaned JSON (all fields, typed) | **PASSED** | 0 mismatching cells |
| B6 | product observations CSV == JSON | **PASSED** | 0 mismatching cells |
| B7 | vehicle market CSV == JSON | **PASSED** | 0 mismatching cells |
| C1 | Every cleaned record resolves to its raw Batch 04/05 record (vehicle, category, URL, date identical) | **PASSED** | 0 failures |
| C2 | Every record with a source carries source_url and collection_date | **PASSED** | 22 sourced records |
| C3 | Every sourced part record maps to a source_log row (source_id) | **PASSED** | all mapped |
| C4 | Every vehicle-market record maps to a source_log row | **PASSED** | all mapped |
| C5 | source_log: all 29 original rows and original column values preserved (additions appended after them) | **PASSED** | 136 rows |
| C6 | Raw batch files byte-identical to the version used for the earlier datasets | **NOT VERIFIED** | No hash manifest existed before this build, so equality with the earlier version cannot be proven. Files were byte-copied from the supplied uploads (verified with cmp) and are hashed in raw_file_hashes.csv. |
| C6b | Raw batch files unchanged since baseline hashes were first recorded | **PASSED** | SHA-256 of all 5 raw files compared with raw_file_hashes_baseline.csv |
| C6c | Batches 05-07 unchanged since their baseline | **PASSED** | SHA-256 of 3 new raw batch files compared with raw_file_hashes_baseline_b05_b07.csv |
| D1 | No part number exists that is not in the raw batches (04, 05) | **PASSED** | 0 unknown numbers |
| D2 | Every price equals a price stated in the raw batch (no invented prices) | **PASSED** | 0 unmatched |
| D3 | No price is zero, and every price has a currency | **PASSED** |  |
| D4 | Prices are numeric (typed float) in CSV and JSON | **PASSED** |  |
| D5 | No currency conversion performed (all currencies original) | **PASSED** | part prices in original USD/EUR/CNY/AED only; no ETB conversion of part prices; Ethiopian ETB prices live only in et_displayed_prices_etb |
| D6 | Confidence changes are exactly the documented set and each has a note | **PASSED** | changes: [('id4__fender_body_panel', 'medium', 'low')] |
| D7 | No confidence level was raised | **PASSED** |  |
| D8 | ethiopian_availability uses only allowed values and agrees with Batch 06 listing counts (exact-model listings <=> listing_observed_exact_model) | **PASSED** | {'listing_observed_exact_model': 14, 'not_found_on_sources_inspected': 12, 'listing_observed_brand_only': 4} |
| D9 | Missing values stay null: rows without a source have no part number, price or description | **PASSED** |  |
| D10 | Dimensions not conflated: no 'New' mapped to stock; condition separate from sourcing | **PASSED** |  |
| D11 | Rows without a part record have sourcing_availability = no_part_record | **PASSED** |  |
| E1 | ID.4 fender flare: related_part_found, low, flare note, not a complete panel | **PASSED** |  |
| E2 | ID.4 tail light & side mirror: category_context_only, low, no part number/price | **PASSED** |  |
| E3 | ID.4 brake pad: low, supplier_unavailable, found record, USD 60.95 kept, not orderable | **PASSED** |  |
| E4 | ID.4 wipers: 2 separate observations, own sizes/part numbers/EUR prices, no average | **PASSED** |  |
| E5 | ID.4 wiper model_year not asserted from catalogue context | **PASSED** |  |
| E6 | All 7 Yuan Up found records are catalogue_model_context_only (no individual fitment confirmation) | **PASSED** |  |
| E7 | Fender flare: single price not assigned to either product | **PASSED** |  |
| E7b | Cleaned wiper and fender-flare rows carry no primary price and point to the child table | **PASSED** |  |
| E8 | No empty calculated/converted price columns exist | **PASSED** |  |
| F1 | Vehicle model labels normalised (one label per vehicle_id) | **PASSED** | {'Yuan Up': 5, 'bZ series (grouped: bZ4X, bZ3, bZ3X, bZ5)': 2, 'Seagull': 5, 'bZ4X': 5, 'ID.4': 4, 'BenBen E-Star': 6} |
| F2 | Category counts present as numbers: Seagull 764, Yuan Up 1362, ID.4 102, BenBen 279 | **PASSED** |  |
| F3 | Pages available vs inspected recorded separately (32/57/5/12 vs 1) | **PASSED** |  |
| F4 | Grouped Toyota bZ-series 1,021 is flagged grouped and not attributed to bZ4X | **PASSED** |  |
| F5 | Platform-reported typical price kept distinct; no calculated averages/medians | **PASSED** |  |
| F6 | Only the 3 study vehicles are flagged selected_vehicle | **PASSED** |  |
| F7 | UAE/international catalogue rows are not labelled as Ethiopian evidence | **PASSED** |  |
| G1 | URL syntax: http(s), host present, no whitespace, no backslashes (all part, product, market and source-log URLs) | **PASSED** | 132 distinct URLs checked; invalid: [] |
| G2 | No backslash escaping in any output file (https\:// or www\.) | **PASSED** | 0 hits in 8 files |
| G3 | Outputs are UTF-8 without BOM; JSON loads with plain utf-8 json.load | **PASSED** | no BOM; json.load OK |
| G4 | URL accessibility (pages reachable now) | **NOT VERIFIED** | Syntax only in this build (no network). A 12-URL spot-check on 2026-11-16 found 9 x HTTP 200 and 3 x 403 (AUTODOC FR/UK, parts.vw.com); see verification_stage4.md. |
| G5 | Product-level wiper pairing vs the live AUTODOC page | **NOT VERIFIED** | Pairing follows listing order inside the raw record (price_pairing_status = order_inferred_from_raw_record). Re-check attempted 2026-11-16: AUTODOC returned HTTP 403 (bot protection); the user's manual browser check did not confirm the pairing either, so it stays order-inferred. |
| G6 | Source-provided evidence IDs for Batch 04 records | **NOT VERIFIED** | Batch 04 supplies none (record_id is the derived key). Not applicable rather than failed. |
| G7 | No duplicate source URL within the same batch in source_log (re-visits in a later batch are logged as new rows) | **PASSED** | 136 rows, 130 distinct URLs, 136 distinct (url, batch) pairs |
| I1 | Batch 05 addresses exactly the 16 target rows, each with the URLs checked | **PASSED** | 16 rows; overlaid: 6 |
| I2 | Batch 05 not_found rows carry no part number, price or description | **PASSED** |  |
| I3 | Every Batch 05 price has its original currency and verbatim price text | **PASSED** |  |
| I4 | Batch 06 covers all 30 combinations on Jiji (one query each) | **PASSED** | 30 Jiji records |
| I5 | No NHTSA data attached to Seagull or Yuan Up | **PASSED** |  |
| I6 | ID.4 NHTSA fields present for all 10 categories (null only where no NHTSA component maps) | **PASSED** |  |
| I7 | No scarcity claim in batches 05-07 (0 found = not found on sources inspected) | **PASSED** | files: [] |
| I8 | ETB never appears as a part-supplier price currency (Ethiopian prices kept separately, unconverted) | **PASSED** |  |
| G8 | Batch 04 source reconciliation | **PASSED** | 7 log rows with a -04 suffix / 6 source_findings in Batch 04 / 6 distinct domains in the 7 rows; the 7th row is ADEY-BZ4X-04 |
| H1 | Every column of every output file is documented in data_dictionary.md, and file headers match the schema | **PASSED** | undocumented: []; header mismatches: [] |

## 3. Files
Generated: `raw_file_hashes_b05_b07.csv`, `raw_file_hashes_baseline_b05_b07.csv`, `raw_vehicle_part_evidence.csv`, `cleaned_vehicle_part_evidence.csv/.json`, `product_observations.csv/.json`, `vehicle_market_evidence.csv/.json`, `source_log.csv`, `data_dictionary.md`, `data_quality_report.md`, `validation_results.json`, `raw_file_hashes.csv`, `raw_file_hashes_baseline.csv`, `build_dataset.py`.
Preserved untouched: `raw/vehicle_visibility_batch_01.json`, `raw/vehicle_model_evidence_batch_02.json`, `raw/vehicle_selection_investigation_batch_03.json`, `raw/vehicle_part_evidence_batch_04.json`, `raw/source_log_original.csv`.
Superseded: `prepare_audit.ps1` (kept only for history; it hard-codes a local path, hard-codes the wiper rows, and writes a BOM).

## 4. Correction register
| ID | Correction | Reason | Affects |
|---|---|---|---|
| CN-01 | `New` is now `item_condition`; it is no longer converted to a stock claim (`listed_new_stock_claim` retired). `sourcing_availability` = `not_established` for those rows. | Condition is not availability. | id4 wiper, id4 fender flare, product observations (`availability_status` renamed `item_condition`) |
| CN-02 | Rows that cover several products no longer carry a primary price; prices live in `product_observations` with `price_pairing_status`. The fender-flare row previously kept EUR 33.49 for two products; now null with the figure in `price_set_in_raw_batch`. | A single price must not appear to apply to two products. | id4 wiper, id4 fender flare |
| CN-03 | ID.4 fender flare: confidence medium -> low; `category_scope_note` states it is not a complete fender/body panel. (Carried over from the earlier pass.) | A flare accessory is not a fender. | id4 fender |
| CN-04 | `model_year` "2020" removed from the ID.4 wiper row (still visible in the raw CSV). `model_year_in_listing_text` records 2021 for the 1A brake pad. | The AUTODOC record states no year; the only 2020 in the raw batches is the Batch 02 EXIST (UAE) catalogue page. Catalogue year context is not product fitment. | id4 wiper, id4 brake pad |
| CN-05 | `missing_or_unverifiable` is now verbatim raw text. The earlier build appended audit remarks to it; those remarks now sit in `correction_notes`. | Raw text must not be altered silently. | 3 ID.4 rows |
| CN-06 | Outputs are UTF-8 **without BOM**. | The earlier files made `json.load()` fail with "Unexpected UTF-8 BOM". | all outputs |
| CN-07 | Part-number hygiene: remark "additional brackets/trims listed" moved to `part_number_note`; `part_number_count` added. Multi-value fields remain `; `-separated lists. | Number fields should hold numbers only. | yuan_up bumper |
| CN-08 | Removed redundant/empty columns: `ethiopian_market_evidence` (identical to `ethiopian_availability`), all-null `evidence_id`, double-encoded `product_observations_json` string. | Redundant, or encoded twice. | cleaned tables |
| CN-09 | Missing-value vocabulary unified (see dictionary section 5). | Four near-synonyms (`unknown`, `not_available`, `not_verified_or_not_found`) mixed 'not found' with 'not verified'. | cleaned table |
| CN-10 | Source log: original rows/values untouched; columns `batch`, `source_scope`, `pages_available`, `cited_by_part_records`, `cited_by_market_records`, `log_note` appended. Batch 04 count reconciled (section 7). | Traceability and reconciliation. | source_log |
| CN-11 | Vehicle market table rebuilt from Batches 01-03: stable ids, `vehicle_id` join key, `selected_vehicle` flag, one label per vehicle, numeric `listing_count`/`seller_count`/`pages_available`/`pages_inspected`/typical price, exact vs grouped flag. Six raw records that the earlier table omitted are now included: Toyota catalogue, EXIST ID.4 (UAE), AutoCango (blocked), and the three Batch 03 `grouped_evidence` entries. | The earlier table kept counts only as free text, had 6 spellings for 2 models, truncated ids, and no join key. | market table |
| CN-12 | Pipeline replaced by `build_dataset.py` (relative paths, hash baseline, validation JSON). | Reproducibility. | pipeline |
| CN-13 | Dictionary generated from the schema; confidence definitions added. | Documentation cannot drift from the files. | docs |
| CN-14 | Batch 05 part records overlay the Batch 04 row for 6 rows (seagull__brake_pad, seagull__brake_disc, seagull__wiper_blade, seagull__tail_light, seagull__side_mirror, id4__shock_absorber); `part_record_batch` = 05, `raw_pointer` points to Batch 05, `compatibility_confidence_original` = Batch 05 value. Not-found rows keep Batch 04 values plus the URLs checked. | New evidence, kept traceable; nothing from Batch 04 deleted (still in raw CSV). | 16 rows |
| CN-15 | `ethiopian_availability` now derived from Batch 06 listing searches (new allowed values); ETB prices kept verbatim in `et_displayed_prices_etb`. | Batch 06 collected Ethiopian part-listing evidence. | 30 rows |
| CN-16 | NHTSA columns from Batch 07 (ID.4 only); Seagull/Yuan Up = `no NHTSA data - not sold in US`. | Failure evidence; no substitute vehicle. | 30 rows |
| CN-18 | Final rerun: AUTODOC wiper pairing re-checked by the user in a browser and NOT confirmed, so `price_pairing_status` stays `order_inferred_from_raw_record` (G5 NOT VERIFIED). Scoring rules v4 (outside this build, in `make_scoring_input.py` / `data/scoring_rules.csv`): Ethiopian 'not found' scores neutral 0.5 (was 0.75), brand-only 0.375, evidence confidence -0.05 when the Ethiopian factor rests only on 'not found'. No evidence value changed. | User decisions after the sensitivity test. | scoring only |
| CN-17 | Source log: 107 rows appended from `source_log_additions_b05_b07.csv`, incl. back-fill `ADEY-ID4-ITEM-03` for market row B03-id4-adey-02 (resolves the old C4 WARNING). G7 now checks duplicates per (url, batch). D5 allows CNY/AED. | Provenance for every new URL. | source_log |

## 5. Confidence distribution
| Confidence | Original (Batch 04) | Cleaned |
|---|---:|---:|
| high | 4 | 4 |
| medium | 14 | 13 |
| low | 4 | 5 |
| insufficient | 8 | 8 |
| **Total** | 30 | 30 |

One change only: `id4__fender_body_panel` medium -> low (CN-03). No level was raised. Earlier text that listed the fender flare under *Medium* and said tail-light/side-mirror were "changed to low" was wrong: those two were already low in the raw batch.

## 6. Evidence coverage (vehicle x category)
| Vehicle | Specific part record | Related component | Category context only | Not found |
|---|---:|---:|---:|---:|
| seagull | 9 | 0 | 0 | 1 |
| yuan_up | 7 | 0 | 0 | 3 |
| id4 | 2 | 2 | 2 | 4 |

Not found in the extracted item list (not proof of non-existence):
* **Seagull:** cabin-air filters
* **Yuan Up:** cabin-air filters, wiper blades, side mirrors
* **ID.4:** brake discs, cabin-air filters, headlights, bumpers

Part records are international supplier/catalogue evidence (China, Albania, France, US, UAE); none is Ethiopian. Batch 05 Seagull rows have two catalogues agreeing on the part number. Ethiopian part-listing evidence (Batch 06): listing_observed_exact_model 14, not_found_on_sources_inspected 12, listing_observed_brand_only 4.

## 7. Source-log reconciliation (the "7 vs 6" question)
* `source_log.csv` has 136 rows. Rows whose id ends in `-04`: **7** (`ADEY-BZ4X-04, CONNECT-SEAGULL-04, CQS-SEAGULL-04, CONNECT-YUAN-04, AUTODOC-ID4-04, 1AAUTO-ID4-04, VW-STORE-ID4-04`).
* Batch 04's own `source_findings` lists **6** sources.
* The difference is exactly one row: **`ADEY-BZ4X-04`**. It is an individual Toyota bZ4X Adey listing (expired), which is Batch 03-style vehicle-selection evidence for a vehicle that was not selected. It is not in Batch 04's findings and no part record cites it. It is flagged in `log_note`, **not renamed or deleted**.
* An earlier explanation ("Connect Drive appears twice") was incorrect: that accounts for 7 rows vs 6 *domains*, not for 7 vs 6 findings.
* `CQS-SEAGULL-04` is in Batch 04's findings but cited by no cleaned record (not used as high-confidence evidence).
* Earlier batches are summarised, not re-labelled: pages **available** vs **inspected** are separate columns (`pages_available` populated for the four Adey category pages: Seagull 32, Yuan Up 57, ID.4 5, BenBen 12; one page inspected each).

## 8. Duplicates and missing values
* Duplicate record ids: 0. Duplicate combinations: 0. Duplicate source URLs in the log: 0. Duplicate market ids: 0.
* Multiple part numbers in one row (left/right, front/rear) are one category record, not duplicates.
* Nulls among the 22 rows that have some evidence: model_year 22, generation 22, variant 22, oem_part_number 6, aftermarket_part_number 18, displayed_price_amount 16, compatibility_evidence 0. `model_year`, `generation`, `variant` are null for all 30 rows because no product source states them; this is a finding, not a defect.
* No price was filled with 0; no part number, price, fitment, stock or Ethiopian availability was inferred.

## 9. Product observations
5 observations: 1 brake pad (USD 60.95, supplier *Unavailable*), 2 wipers (EUR 18.49 / EUR 15.49), 2 fender flares (price not attributable). **Wiper pairing is `order_inferred_from_raw_record`**: Batch 04 says "one price 18.49 EUR and another 15.49 EUR" and "second product price 15.49 EUR" and lists the two products in the same order; it does not tie prices to part numbers explicitly. Treat product-level wiper prices as provisional until checked against the live AUTODOC page. Never average the two.

## 10. Remaining limitations and unresolved issues
1. **Ethiopian spare-part evidence is listing-level only** (Batch 06: Jiji + Adey, first page per query): listing_observed_exact_model 14, not_found_on_sources_inspected 12, listing_observed_brand_only 4. No stock, seller count or sales is established; Telegram/Facebook sellers were not inspected directly; Gezat, Golden Car Market and Mekina.net have no parts search. "0 found" means not found on the sources inspected, not scarcity.
2. **Fitment is model-level at best**, single-source, and never year/trim/VIN-confirmed. The high-confidence Seagull rows come from one supplier page.
3. **Part-record coverage after Batch 05:** 18 specific, 2 related, 2 category-context only, 8 not found. This reflects the sources inspected, not the market. AUTODOC and parts.vw.com returned HTTP 403 in the Stage 4 re-check.
4. **Wiper price pairing** is order-inferred (section 9).
5. **Fender flare price** (EUR 33.49) cannot be assigned to VT540-S or VT540-L.
6. **NOT VERIFIED:** URL accessibility; raw files vs the version used for the earlier datasets (no earlier manifest existed; baseline hashes were first recorded at this build); the wiper price pairing against the live page; source-provided evidence ids (none exist).
7. `ADEY-BZ4X-04` carries a misleading batch suffix (kept, flagged).
8. Yuan Up Adey maximum displayed price (52,000,003 ETB) is a platform figure and an outlier; do not treat the min/max as a distribution.
9. Market-table rows without a `source_id` (if any) correspond to URLs that were collected but never logged; see check C4.
10. Seller names are copied as displayed (one is Amharic); no identity resolution was attempted.
11. **Failure data exists for the ID.4 only** (NHTSA, US complaints: self-reported, unverified, US conditions). BYD Seagull and Yuan Up have no comparable public failure dataset in this study.
