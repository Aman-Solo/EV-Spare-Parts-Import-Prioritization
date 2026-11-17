# PROGRESS (EV spare-parts project, collection date 2026-11-16)

## Stage 1 - Part records: DONE
- Done: 16 empty rows checked. Seagull 5/6 found (brake pad, brake disc, wiper, tail light, side mirror; CNY prices from Landin, OE codes corroborated by CQSW list; confidence medium). Yuan Up 0/3 found. ID.4 0/7 found (1 related part: strut mount, AED). Firecrawl MCP not connected here, so pages were fetched with curl and parsed locally.
- Files: raw/vehicle_part_evidence_batch_05.json, collection_scripts/write_batch_05.py, collection_scripts/log_sources.py, source_log.csv (+11 rows), source_log_additions_b05_b07.csv
- Open: AUTODOC blocked (403) for curl; exist.ae ID.4 sibling page shows BMW parts (logged as unreliable).

## Stage 2 - Ethiopian availability: DONE
- Done: 30 combos x Jiji (stated counts + ETB prices), 30 x Adey full-model queries (all returned whole cars only -> 0 part listings), 20 Adey brand-level queries (titles classified per model; exact model AND part name required). Gezat, Golden Car Market, Mekina.net logged as not searchable for parts. Jiji exact-model+part listings found for 16 combos; 6 combos 0 found on Jiji (all cabin filters & wipers + ID.4 shock).
- Files: raw/vehicle_part_evidence_batch_06.json, raw/ethiopia_search_2026-11-16/ (80 responses + 2 manifests), collection_scripts/fetch_ethiopia_b06.py, build_batch_06.py, source_log.csv (+83 rows)
- Open: one Jiji fetch failed first time (network) and was re-fetched. Seller counts are not stated by any platform. Telegram/Facebook sellers not inspected directly (Adey indexes some Telegram channels).

## Stage 3 - Failure evidence (NHTSA): DONE
- Done: ID.4 MY2021-2026: 1,040 unique complaints, 26 recall campaigns. Component->category mapping saved (shared counts flagged; cabin filter has no NHTSA component). Seagull/Yuan Up = "no NHTSA data - not sold in US".
- Files: raw/nhtsa_api_2026-11-16/*.json (12), raw/vehicle_failure_evidence_batch_07.json, nhtsa_component_mapping.csv, collection_scripts/build_batch_07.py, source_log.csv (+12 rows)
- Open: none

## Stage 4 - Verification: DONE (1 item blocked, 4 proposals pending approval)
- Done: B03-id4-adey-02 source row added (ADEY-ID4-ITEM-03). 12 key URLs checked (9 x 200, 3 x 403: AUTODOC FR/UK, parts.vw.com). Adey category counts drifted slightly (recorded as proposal, not applied).
- Files: verification_stage4.md, source_log.csv (+1 row)
- Open: AUTODOC wiper price pairing (3 397 006 839 vs 831) NOT VERIFIED - page blocked (403); manual check needed. Proposals P1-P4 await approval.

## Stage 5 - Rebuild: DONE
- Done: build_dataset.py extended (v3) to ingest batches 05-07 + source_log additions; rebuilt cleaned CSV/JSON (30 rows, 0 duplicates); validation 59 PASSED / 0 FAILED / 0 WARNING / 4 NOT VERIFIED (C6 no pre-baseline, G4 URL reachability, G5 AUTODOC wiper pairing, G6 n/a). Old C4 WARNING gone. Raw batches 01-04 hash check C6b PASSED; new batches baselined (C6c).
- Files: build_dataset.py, cleaned_vehicle_part_evidence.csv/.json, source_log.csv (136 rows), data_dictionary.md, data_quality_report.md, validation_results.json, raw_file_hashes_b05_b07.csv (+baseline), README.md; v2 copies in _v2_backup/
- Open: top-level copies in ../ (outside collection/) are the stale v2 files - use collection/ as the source of truth.

## Stage 6 - Scoring and notebook: DONE (weights await your review)
- Done: 5 factors per row (0-1) with written rules + missing-data rules (no silent zeros; explicit zeros documented in *_basis). Proposed weights 0.30 demand / 0.20 compatibility / 0.20 sourcing / 0.15 scarcity / 0.15 evidence confidence. Notebook runs top-to-bottom from data/ (executed: 0 errors, no network, no absolute paths, Colab upload/Drive first cell). Sensitivity: 11 named scenarios (6 alt weights + drop-one x5) + 2,000 random perturbations.
- Files: make_scoring_input.py, data/scoring_input.csv, data/scoring_rules.csv, data/weights_proposed.csv, data/ (4 copied inputs), analysis.ipynb (with outputs), collection_scripts/make_notebook.py
- Open: Base top 5 = seagull brake_pad, seagull wiper_blade, id4 wiper_blade, seagull brake_disc, seagull tail_light; scores clustered (rank 5-6 gap 0.010). 4 of 5 drop out when the scarcity (Ethiopian) factor is removed -> reported, decision needed.

## Stage 7 - Written deliverables: DONE
- Done: vehicle selection rationale (listing counts labelled as listing counts), limitations (incl. top-5 sensitivity to the scarcity factor), reuse note (GitHub table left blank), 7-minute outline + 5 trainer Q&A.
- Files: vehicle_selection_rationale.md, limitations.md, reuse_note.md, presentation_outline.md
- Open: user to fill the GitHub reuse table (only repos actually used); user to review weights and decide on the scarcity-factor issue; AUTODOC wiper pairing manual check.

## Post-check - Checker PDF cross-check: DONE
- Done: all checker sections run (pre_colab_verification_results.md). Live spot-check of 5 new records: values match; found the misspelling "Bunper" missed by the Batch 06 matcher -> regex fixed, batch_06 regenerated, b05-b07 hash baseline re-created (files generated in this session, not user raw files), dataset/scoring/notebook rebuilt. Top 5 unchanged; 59 PASSED / 0 FAILED.
- Files: pre_colab_verification_results.md, raw/vehicle_part_evidence_batch_06.json (regenerated), raw_file_hashes_baseline_b05_b07.csv (re-created)
- Open: scarcity-factor dependency of top 5 (decision), Colab run, AUTODOC wiper check, P1-P4 approvals, weights review.

# FINAL RERUN (Aman prompt, 2026-11-16 23:06) - working folder: "copii final/copii/collection"

## F-Stage 1 - Decisions: DONE
- Done: scarcity not_found 0.75 -> 0.50 (neutral); exact-model stays 0.25; brand-only 0.50 -> 0.375 (midpoint). Evidence confidence -0.05 points when the Ethiopian factor rests only on "not found" (shown in evidence_confidence_basis). Weights unchanged 0.30/0.20/0.20/0.15/0.15. AUTODOC wiper pairing NOT confirmed (prompt left the prices blank) -> stays order_inferred_from_raw_record; G5 text updated.
- Files: make_scoring_input.py, build_dataset.py (G5 text only); scoring_rules.csv regenerated in F-Stage 2
- Open: if the AUTODOC prices were in fact confirmed, supply the two EUR values.

## F-Stage 2 - Rebuild: DONE
- Done: pipeline rerun: 59 PASSED / 0 FAILED / 0 WARNING / 4 NOT VERIFIED; 30 rows, 0 duplicate pairs; C6b (raw 01-04 hashes) and C6c PASSED. scoring_input.csv rebuilt (scarcity: 14 x 0.25, 4 x 0.375, 12 x 0.5).
- Files: cleaned_vehicle_part_evidence.csv/.json, validation_results.json, data_quality_report.md (CN-18), data_dictionary.md (section 4b), data/scoring_input.csv, data/scoring_rules.csv
- Open: none

## F-Stage 3 - Notebook: DONE
- Done: category ranking added (listing-count weights Yuan Up 1362 / Seagull 764 / ID.4 102 = 0.611/0.343/0.046, unweighted mean cross-check), side-by-side table, sensitivity for both (11 named scenarios + 2,000 perturbations), robust/borderline/weak tiers, tie report. Fresh-kernel run via nbconvert: 0 errors, outputs saved, no network/abs paths, Colab cell intact.
- Files: analysis.ipynb (with outputs), collection_scripts/make_notebook.py
- Open: vehicle-part rank 5 is a 3-way exact tie (Seagull bumper/fender/headlight 0.7181); category weighted vs unweighted top 5 overlap 3 of 5 (wiper_blade #2 unweighted, #8 weighted).

## F-Stage 4 - Reference repos: DONE
- Done: 3 repos read (README/LICENSE/tree/schema only; all MIT, FAPI data evaluation-only). Similarity check: 0 identical 5+-line blocks; only generic overlaps (main; brand, part_number, vehicle_id - all pre-existing in v2). None of 7 tested part numbers in the repos. Reuse = nothing for all three; [CONFIRM] markers for schema-idea and tools disclosure.
- Files: reuse_note.md, collection_scripts/similarity_check.py, similarity_check_results.json
- Open: user to resolve 3 [CONFIRM] markers. Repos are outside collection/ -> not in build/validation/zip.

## F-Stage 5 - Decision log: DONE
- Done: 15 decisions logged (vehicles, bZ4X/BenBen rejection, categories, no conversion, NHTSA ID.4 only, weights, missing-data rule, scarcity 0.75->0.5, category ranking, AUTODOC, 403 URLs, exist.ae exclusion, repos).
- Files: decision_log.md
- Open: none

## F-Stage 6 - Limitations + outline: DONE
- Done: limitations.md rewritten with final numbers (scarcity change, 3-way tie at rank 5, robust/borderline/weak tiers, category vs unweighted overlap, AUTODOC unconfirmed). 7-minute outline: 8 slides with timings mapped to evidence / dataset & missing data / assumptions & weights; 5 trainer Q&A.
- Files: limitations.md, presentation_outline.md
- Open: none

## F-Stage 7 - Study guide: DONE
- Done: plain-language guide: purpose of every file, 5 factors with a hand-worked example (Seagull brake pad = 0.784; brake-pad category = 0.724), final tiers, 15 mentor Q&A (incl. all 7 required topics).
- Files: study_guide.md
- Open: none
