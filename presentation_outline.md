# Presentation outline (7 minutes)

Each slide maps to one of three themes: **[E]** evidence, **[D]** dataset fields and missing data, **[A]** assumptions and weights.

| # | Time | Slide | Theme | Key points (say, don't read) |
|---|---|---|---|---|
| 1 | 0:00-0:35 | **Question and scope** | - | Which EV spare parts should be imported first? 3 vehicles x 10 categories = 30 rows. Evidence prioritisation, not a sales forecast. |
| 2 | 0:35-1:25 | **Why these 3 vehicles** | [E] | Adey **listing counts** (not sales): Yuan Up 1,362, Seagull 764, ID.4 102. bZ4X rejected (grouped count only); BenBen rejected (weak parts traceability). ID.4 is the contrast case with NHTSA data. |
| 3 | 1:25-2:20 | **Evidence collected** | [E] | 7 batches, 136 logged sources. International part records (prices in original CNY/EUR/USD/AED). Ethiopian part listings on Jiji/Adey (ETB as displayed). NHTSA for ID.4: 1,040 complaints, 26 recalls. 3 sites blocked (403), logged, not bypassed. |
| 4 | 2:20-3:05 | **Dataset and missing data** | [D] | One row per vehicle x category. Five separate dimensions: record found / fitment / source quality / supplier availability / Ethiopian listing. 18 specific, 2 related, 2 context-only, 8 not found. No cabin filters anywhere. No BYD failure data. Missing = empty and re-weighted, never 0. Validation: 59 passed, 0 failed. |
| 5 | 3:05-4:00 | **Assumptions and weights** | [A] | Demand 0.30, compatibility 0.20, sourcing 0.20, scarcity 0.15, evidence confidence 0.15. Demand = listing-count visibility + stated replacement assumption (+ NHTSA for ID.4). **Iteration:** "not found" changed 0.75 -> neutral 0.5 after the sensitivity test showed the top 5 rested on it. |
| 6 | 4:00-5:00 | **Two rankings (side by side)** | [E][A] | Vehicle-part top 5: Seagull brake pad 0.784, Seagull wiper 0.724, Seagull side mirror 0.724, Seagull tail light 0.719, Seagull bumper 0.718 (**3-way tie** with fender and headlight). Category top 5 (listing-weighted): brake pad 0.724, fender/body panel 0.665, headlight 0.660, tail light 0.659, bumper 0.658. |
| 7 | 5:00-6:05 | **How robust?** | [A] | **Robust:** Seagull brake pad; categories brake pad, fender/body panel, tail light. **Borderline:** Seagull wiper, side mirror, tail light, bumper; categories headlight, bumper. **Weak evidence:** Seagull wiper (no supplier price, Ethiopian factor only "not found"); Yuan Up rows in the top categories have no supplier price. Category ranking is more stable (4.6 of 5 overlap) than vehicle-part (3.5 of 5). |
| 8 | 6:05-7:00 | **Recommendation and next steps** | - | Start with brake pads (robust on both levels: OE EQEA-3501500CH / 14758996-00 for Seagull; ETB 28,000 seen on Jiji). Then collision parts (fender, tail light). Before ordering: VIN-confirm with suppliers, get Yuan Up prices, and phone 5 Addis sellers for ETB prices and stock. |

## 5 likely trainer questions (with short answers)

1. **"Listing counts are not sales. How do you know there is demand?"**
   We don't measure demand directly. Listing counts are a visibility proxy for the fleet, and the replacement assumption is stated. That is why demand is 30% of the score and is named in the limitations.

2. **"Why did you change the scarcity rule? Isn't that tuning?"**
   The first sensitivity test showed the top 5 rested on "not found on 2 platforms" being scored as scarcity. Not finding something is not evidence it is scarce, so it is now neutral. The weights stayed the same, and the change is in the decision log.

3. **"How do you know the Seagull brake pad fits?"**
   Two independent catalogues list the same OE number under Seagull. That is model-level only: VIN and battery variant must be confirmed with the supplier.

4. **"Why is rank 5 a tie, and does it matter?"**
   Bumper, fender and headlight for the Seagull score exactly the same, so the order between them is arbitrary. That is why they are labelled borderline, and why the category ranking, which is more stable, is shown next to it.

5. **"Why no ETB conversion?"**
   It would add exchange-rate, shipping and duty assumptions we cannot verify. The task is to rank *which* parts. Landed cost needs real quotes.
