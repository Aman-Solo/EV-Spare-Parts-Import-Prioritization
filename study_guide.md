# Study guide: EV spare-parts import prioritisation

## 1. What each file is for

| File / folder | Purpose in one line |
|---|---|
| `raw/` | The original evidence, never edited: research batches 01-07, saved web/API responses, original source log. |
| `build_dataset.py` | Turns `raw/` into the clean tables and runs 63 checks (59 passed, 0 failed, 4 "not verified" because they need a browser or have no earlier baseline). |
| `cleaned_vehicle_part_evidence.csv/.json` | **The main table:** 30 rows (3 vehicles x 10 parts) with part numbers, prices, fitment level, Ethiopian listings and NHTSA counts. |
| `product_observations.csv/.json` | Individual products where one row covers several (e.g. two ID.4 wiper sizes). |
| `vehicle_market_evidence.csv/.json` | Evidence that the *cars* are present in Ethiopia (listing counts, catalogues). Kept apart from part evidence. |
| `source_log.csv` | Every URL used, with date, status and which rows cite it (136 rows). |
| `data_dictionary.md` | What every column means and its allowed values. |
| `data_quality_report.md` | The check results and the list of corrections (CN-01 to CN-18). |
| `validation_results.json` | The same check results in machine-readable form. |
| `nhtsa_component_mapping.csv` | How NHTSA's component names map to the 10 part categories. |
| `make_scoring_input.py` | Turns the main table into five 0-1 factor scores per row, using written rules. |
| `data/` | Everything the notebook needs: `scoring_input.csv`, `scoring_rules.csv`, `weights_proposed.csv`, and copies of the main tables. |
| `analysis.ipynb` | Loads `data/`, scores, ranks (vehicle-part and category), and runs the sensitivity tests. Works in Colab. |
| `decision_log.md` | Every key decision, the alternatives considered, and why. |
| `limitations.md` | What we could not find or verify. |
| `vehicle_selection_rationale.md` | Why these 3 vehicles. |
| `reuse_note.md` | What the GitHub repos contributed (nothing copied) and the tools used. |
| `presentation_outline.md` | 7-minute talk plan. |
| `verification_stage4.md`, `pre_colab_verification_results.md` | URL spot-checks and the checker-PDF results. |
| `collection_scripts/` | The scripts that collected batches 05-07, built the notebook and ran the similarity check. |
| `PROGRESS.md` | Stage-by-stage work log. |

## 2. The five factors, each with a worked example

Score = 0.30 x demand + 0.20 x compatibility + 0.20 x sourcing + 0.15 x scarcity + 0.15 x evidence confidence. Every factor is between 0 and 1.

The worked example is **Seagull brake pad** (rank 1).

**Demand evidence (0.30).** "Is there likely to be a need for this part?"
* V (vehicle visibility) = ln(1 + listings) / ln(1 + largest listings) = ln(765) / ln(1363) = 6.640 / 7.217 = **0.92**. The 764 Seagull listings on Adey are a listing count, not sales.
* C (part type) = **1.0**, because brake pads are a routine consumable. This is a stated assumption: consumable 1.0, collision-exposed 0.6, durable wear 0.4.
* F (US failure complaints) is **missing**, because the Seagull is not sold in the US. Its weight is removed, not set to zero.
* Demand = (0.4 x 0.92 + 0.4 x 1.0) / (0.4 + 0.4) = **0.96**.

**Compatibility (0.20).** "How sure are we that the part fits?" The level is medium (two catalogues list it under the Seagull, but there is no VIN or year confirmation), and medium = **0.70**. The scale is high 1.0, medium 0.7, low 0.35, insufficient 0.

**Sourcing practicality (0.20).** "Can an importer act on it?" A part record with a displayed price (Landin Parts, 64 CNY) = **1.0**. The scale: price on request 0.75, no price 0.6, supplier unavailable 0.3, related part only 0.2, no record 0.

**Scarcity evidence (0.15).** "Is the part missing from the local market?" A Seagull brake pad listing was found on Jiji (ETB 28,000), so local supply is observed = **0.25**. The scale: brand-only listing 0.375, nothing found = neutral 0.5.

**Evidence confidence (0.15).** "How much evidence stands behind this row?" Part number +0.30, second catalogue +0.10, price +0.10, medium fitment +0.10, Ethiopian exact listing +0.15 = 0.75, then divided by the 0.95 maximum = **0.79**.

**Total:** 0.30 x 0.96 + 0.20 x 0.70 + 0.20 x 1.0 + 0.15 x 0.25 + 0.15 x 0.79 = 0.288 + 0.140 + 0.200 + 0.038 + 0.118 = **0.784**.

**Category example (brake pad).** Vehicle scores: Yuan Up 0.709, Seagull 0.784, ID.4 0.478. The weights are listing shares: 1,362/2,228 = 0.611, 764/2,228 = 0.343, 102/2,228 = 0.046.
0.611 x 0.709 + 0.343 x 0.784 + 0.046 x 0.478 = 0.433 + 0.269 + 0.022 = **0.724**, which is category rank 1. The unweighted cross-check is (0.784 + 0.709 + 0.478) / 3 = 0.657.

**A contrast case: ID.4 headlight (low rank).** The US data shows 17 headlight complaints, the most of any ID.4 part, so demand is reasonably high (0.70). But no part was identified in the sources inspected: compatibility 0, sourcing 0, evidence confidence 0.05. Failure data alone cannot make a part importable.

## 3. Final results

| Tier | Vehicle-part top 5 | Category top 5 (listing-weighted) |
|---|---|---|
| Robust (top 5 in all 11 scenarios and in at least 95% of random weight changes) | Seagull brake pad (0.784) | brake pad (0.724), fender/body panel (0.665), tail light (0.659) |
| Borderline | Seagull wiper (0.724), Seagull side mirror (0.724), Seagull tail light (0.719), Seagull bumper (0.718; **3-way tie** with fender and headlight) | headlight (0.660), bumper (0.658) |
| Weak evidence (a flag on top of the tier) | Seagull wiper: no supplier price, Ethiopian factor only "not found"; Seagull bumper: no supplier price | All five: the Yuan Up row (largest listing weight) has no supplier price |

## 4. Fifteen likely mentor questions

1. **Why is "not found" scored neutral (0.5) and not high?** Because we searched only the first page of two websites. Not finding a part there says nothing reliable about whether it is scarce, so it scores the same as "unknown". The first version scored it 0.75; the sensitivity test showed that this weakest signal was holding up 4 of the top 5, so we corrected it without changing the weights.
2. **Why does the Seagull dominate?** 8 of the top 10 vehicle-part rows are Seagull. It is visible in the market (764 listings) and has the best-documented parts: two independent catalogues agree on the part numbers, and Landin shows prices. Part of this is documentation quality, not only need, and the limitations say so.
3. **Why is compatibility nearly flat at 0.70?** 13 of 30 rows are "medium": a catalogue lists the part under the model with a part number, but no source confirms year, trim or VIN. Only 4 Seagull rows are "high" (the source states compatibility explicitly). Nothing scores above "high", because no source gives VIN-level fitment.
4. **Why does the Seagull wiper rank 2 with thin evidence?** Wipers are a routine consumable (C = 1.0) on a high-visibility car, and two catalogues agree on the number EQEA-5205110. But there is no supplier price and no Ethiopian listing, so its evidence confidence is low (0.47) and it is tiered borderline and weak-evidence.
5. **Why these weights?** Demand (0.30) is what creates import value. Compatibility and sourcing (0.20 each) decide whether a part can be imported at all. Scarcity (0.15) is lowest because the Ethiopian data is the weakest. Evidence confidence (0.15) stops thinly documented rows from winning.
6. **Why no ETB conversion?** Converting needs an exchange rate plus shipping, duty and margin, which we could not verify. We rank *which* parts; landed cost needs real quotes.
7. **What did the GitHub repos contribute?** Nothing was copied. The similarity check found no shared code blocks. The repos assume year-level fitment or sales history that we do not have, and the cross-reference data is licensed for evaluation only and contains none of our part numbers.
8. **Are listing counts demand?** No. They show how visible a car is in the market. One car can be listed several times, and dealers re-post.
9. **Why is NHTSA used for the ID.4 only?** It is US data and only the ID.4 is sold in the US. Borrowing another car's failures for BYD would be invented evidence.
10. **How did you handle missing data?** A missing value is left empty and the remaining weights are re-normalised. A real "nothing found" is an explicit 0, written in the basis column.
11. **How robust is the top 5?** Only the Seagull brake pad is robust at vehicle-part level. The category ranking is steadier (3 robust of 5). Rank 5 is an exact tie.
12. **Why a category ranking?** An importer stocks a part type for the whole fleet. Weighting by listing counts gives more weight to cars that are more visible. The unweighted mean is shown so the effect of that weighting is visible (it changes 2 of the top 5).
13. **What about the AUTODOC wiper prices?** They are still unconfirmed: the site blocked automated checks and the manual check did not confirm them. The pairing is labelled order-inferred.
14. **What would you do next?** Confirm part numbers by VIN with suppliers, get Yuan Up prices, call or visit 5 Addis parts sellers for ETB prices and stock, and check Telegram seller channels.
15. **How do I know the data was not invented?** Every value traces to a saved raw file and a logged URL. Check D1 confirms that no part number exists outside the raw batches, and a 5-record live spot-check matched.
