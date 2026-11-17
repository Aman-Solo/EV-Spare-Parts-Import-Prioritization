# Limitations

Finding that information is unavailable is a valid result in this study. The gaps below are reported as they are; none of them was filled with guesses.

## 1. Ethiopian spare-part evidence is thin and listing-level only
* Only **Jiji** and **Adey Market** could be searched for parts (first results page per query). Gezat, Golden Car Market and Mekina.net list vehicles, not parts, or have no server-side parts search.
* **ETB prices** are single displayed prices from individual listings (e.g. Jiji: Seagull brake pad ETB 28,000; ID.4 front bumper ETB 180,000-250,000). They were not verified with sellers, may be negotiable or out of date, and are never averaged.
* **Stock was not verified.** A listing is not proof that a part is in stock.
* **No platform states a seller count** for part searches.
* **Telegram and Facebook sellers**, where much Ethiopian EV-parts trade happens, were not inspected directly. Adey indexes some Telegram channels, but its coverage is unknown.
* "Not found" means *not found on the sources inspected*. It is scored **neutral (0.5)** and never treated as scarcity.

## 2. Fitment is model-level at best
* No record is confirmed by **VIN**, model year, trim or drivetrain. "Catalogue model context" (e.g. Landin's label "SEAGULL 2020-") is kept separate from confirmed fitment.
* Seagull and Yuan Up have several battery and trim variants (e.g. Seagull 30.08 / 38.88 kWh). Part numbers may differ by variant, and this was not checked.

## 3. Part-record coverage
* 18 of 30 rows have a specific part record, 2 have a related part only (ID.4 fender flare, ID.4 strut mount), 2 have category context only (ID.4 tail light, side mirror), and 8 have nothing found (Seagull cabin filter; Yuan Up cabin filter, wiper, side mirror; ID.4 brake disc, cabin filter, headlight, bumper).
* **Cabin air filters** were not found for any vehicle in the sources inspected.
* **Three URLs blocked automated access (HTTP 403):** autodoc24.fr, autodoc.co.uk and parts.vw.com. One exist.ae "ID.4" page showed BMW parts and was excluded.
* **AUTODOC wiper price pairing** (Bosch 3 397 006 839 vs 3 397 006 831, EUR 18.49 / 15.49) is **still unconfirmed**. Neither the automated check nor the manual browser check confirmed it, so the pairing follows the order in the raw record.
* International prices are in their original currencies (CNY, EUR, USD, AED) and were **not converted**. They exclude shipping, duty and VAT, and are not Ethiopian prices.

## 4. Failure data covers the ID.4 only
* NHTSA complaints are **US**, self-reported and unverified. They are not failure rates.
* NHTSA components are coarse (SERVICE BRAKES covers pads and discs together, STRUCTURE covers bumper and fender together) and are flagged as shared. Keyword counts are a secondary signal.
* **No BYD failure data** could be obtained. No substitute vehicle was used.

## 5. Scoring limitations (final run, scoring rules v4)
* **Demand is a proxy.** It combines vehicle listing counts (visibility, not sales) with a **stated assumption** about part replacement frequency (consumable > collision-exposed > durable wear). The assumption is not measured.
* **The scarcity rule was changed once.** In the first run, "not found" scored 0.75 and 4 of the top 5 depended on it. It now scores neutral 0.5. This was an honest correction, not tuning, and the weights were not changed. See `decision_log.md` #10.
* **Vehicle-part scores are tightly clustered.** Ranks 1-10 span 0.784 to 0.700. **Rank 5 is a three-way exact tie** (Seagull bumper, fender, headlight: 0.7181), decided only by the alphabetical tie-break.
* **Only one vehicle-part item is robust:** Seagull brake pad (top 5 in 11/11 scenarios and 100% of ±20% weight perturbations). The other four are borderline (top 5 in 6-8 of 11 scenarios, 52-77% of perturbations). Two (Seagull wiper, Seagull tail light) leave the top 5 when the Ethiopian factor is removed. Mean top-5 overlap across scenarios is 3.45 of 5.
* **The category ranking is more stable** (mean overlap 4.64 of 5). Brake pad, fender/body panel and tail light are robust; headlight and bumper are borderline. It does depend on the listing-count weights: the unweighted mean shares only 3 of 5 top categories (wiper blade is #2 unweighted but #8 weighted).
* **Seagull dominates the vehicle-part top 10**, partly because its part numbers are better documented (two catalogues agree), not only because of higher need.
* **Thin evidence among the top items:** Seagull wiper has no supplier price, and its Ethiopian factor is "not found". Every Yuan Up row leading a top category has no supplier price.
* The weights are a reviewed proposal, not an optimised result.

## 6. Data collection
* Batches 05-07 were fetched by plain HTTP (Firecrawl was unavailable) and the raw responses are saved under `raw/`. Everything was collected on 2026-11-16. Listings and prices change daily.
