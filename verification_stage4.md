# Stage 4: Verification (2026-11-16)

## 1. Missing source_log row: FIXED
`B03-id4-adey-02` (Adey item 1714288, VW ID.4 Pro 2023, 6,200,000 ETB) had no source_log row (check C4 WARNING).
Appended as `ADEY-ID4-ITEM-03`. The URL still returns HTTP 200. No evidence value was changed.

## 2. AUTODOC ID.4 wiper price pairing: NOT VERIFIED (blocked)
- `https://www.autodoc24.fr/spares/vw/id-4` returned **HTTP 403** to curl and to the web-fetch tool. The UK mirror (autodoc.co.uk) also returned 403. The browser extension was not connected, and Firecrawl was not available in this session.
- So it is still unconfirmed which price (18.49 EUR or 15.49 EUR) belongs to Bosch **3 397 006 839** (AP 28 U, 700 mm) and which to **3 397 006 831** (AP 18 U, 450 mm).
- Current dataset state (unchanged): `price_pairing_status = order_inferred_from_raw_record`. Check G5 stays NOT VERIFIED.
- **You need to do this by hand:** open the page in a normal browser, find both Bosch cards, and note the price inside each card.

## 3. URL status spot-check (12 URLs)

| Status | URL | Used by |
|---|---|---|
| 403 | autodoc24.fr/spares/vw/id-4 | ID.4 wiper, fender (B04) |
| 403 | autodoc.co.uk wiper ID.4 (alternative) | none (attempted re-check) |
| 403 | parts.vw.com/Volkswagen__ID4/Body.html | ID.4 tail light, mirror (B04) |
| 200 | adey-market.com/item/1714288-… | B03-id4-adey-02 |
| 200 | adey-market.com/categories/cars/volkswagen-id-4 | ID.4 market count |
| 200 | adey-market.com/categories/cars/byd-seagull-dolphin-mini-atto-1 | Seagull market count |
| 200 | adey-market.com/categories/cars/byd-yuan-up-atto-2 | Yuan Up market count |
| 200 | connectdrive.al … byd-seagull | Seagull parts (B04) |
| 200 | connectdrive.al … byd-yuan-up | Yuan Up parts (B04) |
| 200 | 1aauto.com/volkswagen-id.4-parts/mo/3148 | ID.4 brake pad (B04) |
| 200 | landinparts.com/byd | Seagull parts (B05) |
| 200 | ev.gezat.et/byd/seagull | Seagull market (B02) |

A 403 means bot protection blocked the request. It does not mean the page is gone.

## 4. Proposed changes: AWAITING YOUR APPROVAL (none applied)

| # | Proposal | Why | Effect if approved |
|---|---|---|---|
| P1 | Record the Adey category counts re-observed today as **new observations** (keep the originals): ID.4 105 listings / 60 sellers (dataset: 102/59); Seagull 759 / 180 (dataset: 764/177); Yuan Up 1,361 / 284 (dataset: 1,362/283). | Counts drift daily. Overwriting would hide the original observation. | Adds 3 rows to a new batch; scoring would keep using the original values unless you choose otherwise. |
| P2 | Mark the AUTODOC and parts.vw.com rows `url_status_2026-11-16 = 403_blocked`. | Honest status. | Metadata only. |
| P3 | Keep the ID.4 wiper `compatibility_confidence` at **medium**, but flag the price as "pairing unverified" in scoring (lower evidence confidence). | The pairing could not be checked. | Already done in the scoring rules (Stage 6); no data value changes. |
| P4 | Leave the exist.ae page `/id-4-e21-e61-e81` (shows BMW E60 parts under "ID.4") out of every record. | Catalogue misattribution. | Already logged as unreliable; nothing cites it. |
