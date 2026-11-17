"""Stage 2: parses saved Ethiopian marketplace search responses (raw/ethiopia_search_2026-11-16/) into
raw/vehicle_part_evidence_batch_06.json. Counts are ONLY what the platform states; everything else is
labelled as derived from the inspected first page. Prices are copied as displayed (ETB), never converted.
Listing counts are listing counts: not sales, not registrations, not demand. '0 found' means not found
on the sources inspected; it is not a scarcity claim."""
import json, re, html, math, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
RAWD = BASE / "raw" / "ethiopia_search_2026-11-16"
MODEL_RX = {"seagull": r"sea ?gull|dolphin ?mini|\batto ?1\b", "yuan_up": r"yuan ?up|\batto ?2\b", "id4": r"\bid\.? ?4\b|\bid4\b"}
BRAND_RX = {"seagull": r"\bbyd\b|ቢዋይዲ|በይድ", "yuan_up": r"\bbyd\b|ቢዋይዲ|በይድ", "id4": r"volkswagen|\bvw\b|ቮልስ"}
PART_RX = {"brake_pad": r"pad|ሸራ", "brake_disc": r"dis[ck]|rotor|ዲስክ", "cabin_air_filter": r"cabin|a/?c filter|air filter|ፊልተር",
           "wiper_blade": r"wiper|ዋይፐር|ጠራጊ", "headlight": r"head ?l(ight|amp)|ፊት መብራት|የፊት መብራት",
           "tail_light": r"tail|rear (light|lamp)|back ?light|የኋላ መብራት", "side_mirror": r"mirror|ስፖኪዮ|ስፖክዮ",
           "bumper": r"bumper|bunper|bamper|ባምፐር|ፓራውልት|ፓራወልት", "fender_body_panel": r"fender|ፌንደር|quarter panel",
           "shock_absorber": r"shock|absorber|strut|ሾክ|ሞርቲጉ"}
OTHER_PLATFORMS = {
    "Gezat": ("https://gezat.et/", "Not searchable for parts: site is a vehicle marketplace (EV listings at ev.gezat.et); "
              "no spare-parts category or parts search found on the home page. Not inspected per combination."),
    "Golden Car Market": ("https://www.goldencarmarket.net/", "JavaScript single-page app (6 KB HTML shell); listings are vehicle "
                          "listings; no server-rendered parts search. Not inspected per combination."),
    "Mekina.net": ("https://www.mekina.net/", "Car listings with a car search (/cars/search); parts appear only as a business "
                   "directory (/directory/auto-parts-accessories), not as part listings with prices. Not inspected per combination."),
}


def cls(title, vid, cat):
    t = title or ""
    model = bool(re.search(MODEL_RX[vid], t, re.I))
    brand = bool(re.search(BRAND_RX[vid], t, re.I))
    part = bool(re.search(PART_RX[cat], t, re.I))
    return ("exact_model" if model else "brand_only" if brand else "neither"), part


def parse_jiji(p, vid, cat):
    h = p.read_text(encoding="utf-8")
    if "couldn't find ads matching" in h or "couldn&#x27;t find ads matching" in h or "couldn&#39;t find ads matching" in h:
        stated = 0
        items = []  # any 'similar ads' shown on a no-match page are not counted
    else:
        m = re.search(r"Found ([0-9,]+) ads", h)
        stated = int(m.group(1).replace(",", "")) if m else None
        titles = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in
                  re.findall(r'qa-advert-title[^"]*"[^>]*>(.*?)</div>', h, re.S)]
        prices = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in
                  re.findall(r'class="qa-advert-price"[^>]*>(.*?)</div>', h, re.S)]
        items = [{"title": t, "price_text": (prices[i] if i < len(prices) and len(prices) == len(titles) else None)} for i, t in enumerate(titles)]
    return stated, items, h


def parse_adey(p, vid, cat):
    j = json.loads(p.read_text(encoding="utf-8"))
    items = []
    for it in j.get("items", []):
        is_part = (it.get("category") == "vehicle_parts") or ((it.get("type") or "").startswith("car_") and it.get("category") != "cars")
        items.append({"title": (it.get("title") or "")[:70], "price": it.get("price"), "currency": it.get("currency"),
                      "section": it.get("section"), "type": it.get("type"), "category": it.get("category"),
                      "shop": it.get("shop"), "platform": it.get("platform"), "is_part_listing": is_part, "record_id": it.get("record_id")})
    return j, items


def main():
    man = json.loads((RAWD / "manifest.json").read_text(encoding="utf-8"))
    recs = []
    for m in man:
        vid, cat, site = m["vehicle_id"], m["category"], m["site"]
        p = RAWD / m["file"]
        base = {"vehicle_id": vid, "part_category": cat, "platform": "Jiji Ethiopia" if site == "jiji" else "Adey Market",
                "query": m["query"], "source_url": m["url"], "http_status": m["http_status"], "collection_date": "2026-11-16",
                "pages_inspected": 1, "raw_file": f"raw/ethiopia_search_2026-11-16/{m['file']}"}
        if m["http_status"] != 200:
            recs.append({**base, "result_status": "fetch_failed", "listing_count_stated": None,
                         "note": f"HTTP {m['http_status']}; see source_log"})
            continue
        if site == "jiji":
            stated, items, _ = parse_jiji(p, vid, cat)
            rel = []
            for it in items:
                scope, part = cls(it["title"], vid, cat)
                rel.append({**it, "model_scope": scope, "names_part": part})
            exact = [r for r in rel if r["model_scope"] == "exact_model" and r["names_part"]]
            brand = [r for r in rel if r["model_scope"] == "brand_only" and r["names_part"]]
            recs.append({**base,
                         "result_status": "0_found" if stated == 0 else ("results_listed" if stated else "count_not_stated"),
                         "listing_count_stated": stated, "listing_count_label": "Jiji 'Found N ads' for the query (search hits, any model)",
                         "pages_available": (math.ceil(stated / max(len(items), 1)) if stated and items else (0 if stated == 0 else None)),
                         "pages_available_note": "derived: stated count / ads shown on page 1" if stated else None,
                         "seller_count_stated": None, "seller_count_note": "Jiji search page does not state a seller count",
                         "items_on_inspected_page": len(rel),
                         "items_naming_exact_model_and_part": len(exact), "items_naming_brand_only_and_part": len(brand),
                         "displayed_prices_exact_model": [r["price_text"] for r in exact if r["price_text"]],
                         "displayed_prices_brand_only": [r["price_text"] for r in brand if r["price_text"]],
                         "price_currency": "ETB (as displayed)",
                         "listings": rel[:25]})
        else:
            j, items = parse_adey(p, vid, cat)
            rel = []
            for it in items:
                scope, part = cls(it["title"], vid, cat)
                rel.append({**it, "model_scope": scope, "names_part": part})
            parts = [r for r in rel if r["is_part_listing"]]
            exact = [r for r in parts if r["model_scope"] == "exact_model" and r["names_part"]]
            brand = [r for r in parts if r["model_scope"] == "brand_only" and r["names_part"]]
            stated_total, counts = j.get("total"), j.get("counts") or {}
            recs.append({**base,
                         "result_status": "results_listed" if parts else "0_part_listings_on_inspected_page",
                         "listing_count_stated": stated_total,
                         "listing_count_label": "Adey 'total' search hits for the query - includes whole-car listings; NOT a parts count",
                         "adey_counts_stated": counts, "adey_query_understood_as": j.get("understood"),
                         "pages_available": math.ceil(stated_total / (j.get("page_size") or 24)) if stated_total else 0,
                         "pages_available_note": "derived: stated total / stated page_size",
                         "seller_count_stated": None, "seller_count_note": "not stated; distinct shops below are derived from page 1 part listings",
                         "distinct_shops_part_listings_page1": len({r["shop"] for r in parts if r["shop"]}),
                         "items_on_inspected_page": len(rel), "part_listings_on_inspected_page": len(parts),
                         "items_naming_exact_model_and_part_listing": len(exact), "items_naming_brand_only_and_part_listing": len(brand),
                         "displayed_prices_exact_model": [f"{r['price']:.0f} {r['currency']}" for r in exact if r["price"] is not None],
                         "displayed_prices_brand_only": [f"{r['price']:.0f} {r['currency']}" for r in brand if r["price"] is not None],
                         "price_currency": "ETB (as returned)",
                         "listings": [r for r in rel if r["is_part_listing"]][:25]})
    # Adey brand-level pass: '<brand> <part>' queries; each returned part listing is classified per vehicle.
    bp = RAWD / "manifest_brand_pass.json"
    if bp.exists():
        for m in json.loads(bp.read_text(encoding="utf-8")):
            j, items = parse_adey(RAWD / m["file"], "seagull", m["category"])
            vids = ["seagull", "yuan_up"] if m["brand"] == "BYD" else ["id4"]
            for vid in vids:
                rel = []
                for it in items:
                    scope, part = cls(it["title"], vid, m["category"])
                    rel.append({**it, "model_scope": scope, "names_part": part})
                parts = [r for r in rel if r["is_part_listing"]]
                exact = [r for r in parts if r["model_scope"] == "exact_model" and r["names_part"]]
                brand = [r for r in parts if r["model_scope"] == "brand_only" and r["names_part"]]
                recs.append({"vehicle_id": vid, "part_category": m["category"], "platform": "Adey Market (brand-level query)",
                             "query": m["query"], "source_url": m["url"], "http_status": m["http_status"],
                             "collection_date": "2026-11-16", "pages_inspected": 1,
                             "raw_file": f"raw/ethiopia_search_2026-11-16/{m['file']}",
                             "result_status": "results_listed" if parts else "0_part_listings_on_inspected_page",
                             "listing_count_stated": j.get("total"),
                             "listing_count_label": "Adey 'total' hits for the brand-level query (all models of the brand; may include cars)",
                             "adey_counts_stated": j.get("counts"), "adey_query_understood_as": j.get("understood"),
                             "pages_available": math.ceil((j.get("total") or 0) / (j.get("page_size") or 24)),
                             "pages_available_note": "derived: stated total / stated page_size",
                             "seller_count_stated": None,
                             "seller_count_note": "not stated; distinct shops below are derived from page 1 part listings",
                             "distinct_shops_part_listings_page1": len({r["shop"] for r in parts if r["shop"]}),
                             "items_on_inspected_page": len(rel), "part_listings_on_inspected_page": len(parts),
                             "items_naming_exact_model_and_part_listing": len(exact),
                             "items_naming_brand_only_and_part_listing": len(brand),
                             "displayed_prices_exact_model": [f"{r['price']:.0f} {r['currency']}" for r in exact if r["price"] is not None],
                             "displayed_prices_brand_only": [f"{r['price']:.0f} {r['currency']}" for r in brand if r["price"] is not None],
                             "price_currency": "ETB (as returned)", "listings": exact[:25]})
    for name, (url, note) in OTHER_PLATFORMS.items():
        recs.append({"vehicle_id": "all", "part_category": "all", "platform": name, "query": None, "source_url": url,
                     "collection_date": "2026-11-16", "pages_inspected": 1, "result_status": "not_searchable_for_parts",
                     "listing_count_stated": None, "note": note})
    out = {"collection_date": "2026-11-16", "batch": "vehicle_part_evidence_06",
           "purpose": "Ethiopian spare-parts availability evidence for 30 vehicle x category combinations.",
           "rules": __doc__, "records": recs}
    p = BASE / "raw" / "vehicle_part_evidence_batch_06.json"
    assert not p.exists(), "refusing to overwrite existing raw batch"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    # compact console summary
    for r in recs:
        if r["platform"] in ("Jiji Ethiopia",):
            print(f"{r['vehicle_id']:8} {r['part_category']:18} jiji stated={r['listing_count_stated']} exact={r.get('items_naming_exact_model_and_part')} brand={r.get('items_naming_brand_only_and_part')} prices={r.get('displayed_prices_exact_model')}")
    for r in recs:
        if r["platform"].startswith("Adey Market (brand"):
            print(f"{r['vehicle_id']:8} {r['part_category']:18} adey total={r['listing_count_stated']} counts={r.get('adey_counts_stated')} parts={r.get('part_listings_on_inspected_page')} exact={r.get('items_naming_exact_model_and_part_listing')} prices={r.get('displayed_prices_exact_model')}")


if __name__ == "__main__":
    main()
