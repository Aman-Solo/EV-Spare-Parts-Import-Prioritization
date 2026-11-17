"""Writes raw/vehicle_part_evidence_batch_05.json from evidence extracted on 2026-11-16.
Values were copied from saved page text (landinparts.com/byd product cards; cqswautoparts.com
Seagull part-number article; exist.ae ID.4 pages; 1aauto.com ID.4 page).
Nothing is inferred: missing = null with a reason."""
import json, pathlib
from collections import Counter

D = "2026-11-16"
LANDIN = "https://landinparts.com/byd"
CQSW = "https://www.cqswautoparts.com/part-numbers-for-byd-seagull-spare-parts"
CD_YU = "https://connectdrive.al/pjese-kembimi-byd/byd-yuan-up?lang=en"
CQSW_YU = "https://www.cqswautoparts.com/part-numbers-for-byd-yuan-up-spare-parts"
A1 = "https://www.1aauto.com/volkswagen-id.4-parts/mo/3148"
EX = "https://exist.ae/catalog/cars/volkswagen/id-4"
EXF = "https://exist.ae/search?q=filter&vehicle=Volkswagen+ID.4"
EXB = "https://exist.ae/search?q=brake&vehicle=Volkswagen+ID.4"
LANDIN_NOTE = ("landinparts.com/byd product card: name / 'Part No' (supplier SKU) / 'OE' / model label / price. "
               "Model label is the supplier's catalogue model context ('SEAGULL 2020-'), not fitment confirmation. "
               "Per-item condition not stated on the card; page header states '677 Total Parts, 526 In Stock' (site-wide, not per item).")
CQSW_NOTE = ("cqswautoparts.com article 'Part numbers for BYD Seagull Spare Parts' lists BYD numeric part number, EQEA/EM2E code and "
             "description; no prices, no model year, no per-item fitment text.")


def rec(v, mfr, cat, **k):
    base = dict(vehicle_manufacturer=mfr, vehicle_model=v, model_year=None, generation=None, variant=None,
                part_category=cat, row_status=None, part_description=None, oem_part_number=None,
                oem_part_number_secondary=None, aftermarket_part_number=None, supplier_sku=None,
                compatibility_evidence=None, catalogue_model_context=None, fitment_text=None,
                compatibility_confidence="insufficient", source_name=None, source_url=None,
                corroborating_source_name=None, corroborating_source_url=None, collection_date=D,
                displayed_price=None, original_currency=None, price_text_verbatim=None,
                condition=None, availability_text=None, supplier=None, supplier_country=None,
                urls_checked=[], supporting_evidence=None, missing_or_unverifiable=None)
    base.update(k)
    return base


def seagull(cat, desc, oe_code, byd_no, sku, price, ptxt, extra=""):
    return rec("Seagull", "BYD", cat, row_status="found", part_description=desc,
               oem_part_number=byd_no, oem_part_number_secondary=oe_code, supplier_sku=sku,
               compatibility_evidence=("Listed under supplier model label 'SEAGULL 2020-' on landinparts.com/byd with OE code " + oe_code +
                                       "; the same code and BYD number " + byd_no + " appear in cqswautoparts.com's BYD Seagull part-number list. "
                                       "Two catalogues agree on the number; neither states year/variant/VIN fitment."),
               catalogue_model_context="SEAGULL 2020- (landinparts model label); 'BYD Seagull' (cqsw article title)",
               fitment_text=None, compatibility_confidence="medium",
               source_name="Landin Parts", source_url=LANDIN,
               corroborating_source_name="CQS Auto Parts (Chongqing Shiwei)", corroborating_source_url=CQSW,
               displayed_price=({"amount": price, "currency": "CNY"} if price is not None else None),
               original_currency=("CNY" if price is not None else None), price_text_verbatim=ptxt,
               condition=None, availability_text=None, supplier="Landin Parts", supplier_country="China",
               urls_checked=[LANDIN, CQSW], supporting_evidence=LANDIN_NOTE + " " + CQSW_NOTE + extra,
               missing_or_unverifiable=("Per-item condition (OEM vs aftermarket), stock, model year, variant and VIN fitment not shown. "
                                        "Price is the displayed catalogue price; the page shows '¥ ... RMB', recorded as CNY."))


R = [
    seagull("brake pads", "Brake Pads (front) / 'front brake pad'", "EQEA-3501500CH", "14758996-00", "BYD0042260F1P", 64, "¥64 RMB",
            " Landin also lists SKU BYD0042260F1 with OE EQEA-3501500CH at ¥64 RMB. Rear pad: SKU BYD0042260R1P, OE EQEA-3502140SS / "
            "14753311-00, ¥64 RMB (cqsw: 'rear brake pad')."),
    seagull("brake discs", "Brake Disc (front) / 'front brake disc'", "EM2E-3501011", "13423467-00", "BYD0041960F1", 108, "¥108 RMB",
            " Rear disc: SKU BYD0041960R1, OE EM2E-3502111 / 13423445-00, ¥94 RMB (cqsw: 'rear brake disc'). Caveat: Landin also shows "
            "OE EM2E-3501011 under a card titled 'Right Parking Brake' (SKU BYD0042210F1, ¥108 RMB) - supplier labelling inconsistency."),
    rec("Seagull", "BYD", "cabin air filters", row_status="not_found", urls_checked=[LANDIN, CQSW],
        missing_or_unverifiable=("No Seagull cabin/air-conditioner filter on landinparts.com/byd (its 'Air Conditioner Filter' cards are "
                                 "labelled 'BYD destroyer 22-25') and none in the cqsw Seagull part-number list. Not found in sources "
                                 "inspected; this does not mean the part is unavailable.")),
    seagull("wiper blades", "Wiper L / 'front wiper pad--L'", "EQEA-5205110", "13567800-00", "BYD0040831F1", None, "Price on request",
            " cqsw describes EQEA-5205110 as 'front wiper pad--L' (the wiper arm has a separate number, EQEA-5205120). Only the left "
            "blade was listed."),
    seagull("tail lights", "Tail Lamps L / 'tail lamp--L'", "EQEA-4133010", "13541787-00", "BYD0040171", 198, "¥198 RMB",
            " Right: SKU BYD0040172, OE EQEA-4133020 / 13541790-00, ¥198 RMB. Middle: SKU BYD0040170M2, OE EQEA-4107300 / "
            "13541780-00, ¥528 RMB."),
    seagull("side mirrors", "Side Mirrors L / 'rearview mirror--L'", "EQEA-8202100", "13568569-00", "BYD0040271", 429, "¥429 RMB",
            " Right: SKU BYD0040272, OE EQEA-8202109 / 13568572-00, ¥264 RMB."),
]
for cat in ["cabin air filters", "wiper blades", "side mirrors"]:
    R.append(rec("Yuan Up", "BYD", cat, row_status="not_found", urls_checked=[CD_YU, CQSW_YU],
                 missing_or_unverifiable=("Connect Drive Yuan UP page (72 product links) has no " + cat + " item; the cqsw Yuan Up "
                                          "part-number URL returned HTTP 404. landinparts.com/byd model selector has no Yuan Up. "
                                          "Not found in sources inspected.")))
EXNOTE = ("exist.ae (UAE) ID.4 page showed only 2 'popular parts' (strut mount, stabiliser link), each 'May fit - check by VIN'. "
          "Its sibling page /id-4-e21-e61-e81 listed BMW E60/E61 parts (fuel pump, ignition coil) under 'Volkswagen ID.4' - treated as "
          "catalogue misattribution and not used. 1aauto.com ID.4 page listed only wiper blades, ABS sensors and brake pads; its "
          "headlight/tail-light/shock links are site-wide navigation, not ID.4-filtered.")
for cat, extra_urls, note in [
        ("brake discs", [EXB], " exist.ae brake search with ID.4 context returned Ford/Toyota/Aisin items ('Results are not filtered by confirmed fitment')."),
        ("cabin air filters", [EXF], " exist.ae filter search with ID.4 context returned 85 generic offers (Mahle/Mann items) with no ID.4 fitment statement."),
        ("headlights", [], ""), ("tail lights", [], ""), ("side mirrors", [], ""), ("bumpers", [], "")]:
    R.append(rec("ID.4", "Volkswagen", cat, row_status="not_found", urls_checked=[A1, EX] + extra_urls,
                 missing_or_unverifiable="No ID.4 item-level record for this category. " + EXNOTE + note))
R.append(rec("ID.4", "Volkswagen", "shock absorbers", row_status="related_part_only",
             part_description="BRYMAN 1EA412331B STRUT MOUNTING FRONT Q4/VW/ID4 1EA4331B (strut mount, not a shock absorber)",
             aftermarket_part_number="1EA412331B",
             compatibility_evidence="exist.ae ID.4 page lists the item with 'May fit - check by VIN'; the title text names Q4/VW/ID4.",
             catalogue_model_context="exist.ae 'Volkswagen ID.4' (Years: 2020)", fitment_text="May fit — check by VIN",
             compatibility_confidence="low", source_name="EXIST.AE", source_url=EX,
             displayed_price={"amount": 94.07, "currency": "AED"}, original_currency="AED",
             price_text_verbatim="from AED 94.07 incl. VAT",
             supplier="EXIST.AE", supplier_country="United Arab Emirates", urls_checked=[A1, EX],
             supporting_evidence="Related suspension part only. 'from' price, incl. VAT. UAE supplier: international evidence, not Ethiopian.",
             missing_or_unverifiable=("No shock absorber/strut item found for ID.4. Whether 1EA412331B is a VW OE number is not stated by "
                                      "the page; recorded as the displayed article number.")))

out = {"collection_date": D, "batch": "vehicle_part_evidence_05",
       "purpose": "Fill the 16 vehicle-category rows that had no part record after Batch 04.",
       "method": ("Pages fetched with curl (Firecrawl MCP was not connected in this session), saved to disk, converted to text and "
                  "read line by line. Max 2 model pages per row; extra search pages are listed in urls_checked."),
       "confidence_definition": "Same as Batch 04. 'medium' here = vehicle-specific catalogue + part number, no year/variant/VIN fitment.",
       "row_status_definition": {"found": "item-level record with a part number", "related_part_only": "only an adjacent part was found",
                                 "not_found": "no record in the sources inspected (URLs in urls_checked)"},
       "records": R,
       "important_limitations": [
           "All suppliers are international (China, UAE). No record is Ethiopian evidence.",
           "Prices are displayed catalogue prices in original currency (CNY, AED); no conversion.",
           "Catalogue model context is not confirmed fitment.",
           "'not_found' means not found in the sources inspected."]}

p = pathlib.Path(__file__).resolve().parents[1] / "raw" / "vehicle_part_evidence_batch_05.json"
assert not p.exists(), "refusing to overwrite existing raw batch"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(R), Counter((r["vehicle_model"], r["row_status"]) for r in R))
