"""make_scoring_input.py - turns the cleaned evidence tables into data/scoring_input.csv (30 rows, 5 factors in 0-1).

Run after build_dataset.py:   python make_scoring_input.py
Reads : cleaned_vehicle_part_evidence.csv, vehicle_market_evidence.csv, product_observations.csv
Writes: data/scoring_input.csv, data/scoring_rules.csv, data/weights_proposed.csv, and copies the three input
        tables into data/ so analysis.ipynb can run from data/ alone (no network, no API keys).

Every factor has a written rule (data/scoring_rules.csv). A factor that cannot be computed is left EMPTY (NaN)
with factor_missing_reason; it is never silently turned into 0. Explicit zeros (e.g. "no part identified") are
documented in the row's *_basis column. Listing counts are listing counts: not sales, registrations or demand
on their own."""
import csv, math, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)


def read(fn):
    with open(BASE / fn, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ("", None) else None


clean = read("cleaned_vehicle_part_evidence.csv")
mkt = read("vehicle_market_evidence.csv")
prod = read("product_observations.csv")

# ---------------------------------------------------------------- factor rules (text is written to data/scoring_rules.csv)
PART_CLASS = {  # documented assumption, not data: how often a part is typically replaced
    "brake_pad": ("routine_consumable", 1.0), "wiper_blade": ("routine_consumable", 1.0), "cabin_air_filter": ("routine_consumable", 1.0),
    "bumper": ("collision_exposed", 0.6), "headlight": ("collision_exposed", 0.6), "side_mirror": ("collision_exposed", 0.6),
    "fender_body_panel": ("collision_exposed", 0.6), "tail_light": ("collision_exposed", 0.6),
    "brake_disc": ("durable_wear", 0.4), "shock_absorber": ("durable_wear", 0.4),
}
COMPAT = {"high": 1.0, "medium": 0.7, "low": 0.35, "insufficient": 0.0}
# v4 (user decision 2026-11-16): "not found" is NOT evidence of scarcity -> neutral 0.5 (was 0.75).
# Brand-only = 0.375: midpoint between exact-model (0.25) and neutral (0.5); no data justifies an off-centre value.
SCARCITY = {"listing_observed_exact_model": 0.25, "listing_observed_brand_only": 0.375, "not_found_on_sources_inspected": 0.5}
NOT_FOUND_EC_PENALTY = 0.05  # evidence-confidence points removed when scarcity rests only on "not found" (same size as the unverified-price penalty)

RULES = [
    ("demand_evidence",
     "Weighted mean of up to 3 sub-scores: V (weight 0.4) = ln(1+n)/ln(1+n_max), where n = the Adey exact-model category LISTING COUNT for the vehicle "
     "(Seagull 764, Yuan Up 1362, ID.4 102; a visibility proxy for how many of these cars are in use, not sales or registrations); "
     "C (weight 0.4) = part replacement class (routine consumable 1.0: brake pad, wiper, cabin filter; collision-exposed 0.6: bumper, headlight, "
     "side mirror, fender, tail light; durable wear 0.4: brake disc, shock absorber; EV regenerative braking lowers disc wear). C is a stated "
     "assumption, not collected data; F (weight 0.2) = NHTSA complaints whose text mentions the part / max over ID.4 categories (ID.4 only).",
     "F is missing for Seagull and Yuan Up (no NHTSA data: not sold in the US). The mean is taken over the available sub-scores with their "
     "weights re-normalised (0.4/0.4 -> 0.5/0.5). F is never set to 0 for BYD. If V were missing, the factor would be left empty."),
    ("scarcity_evidence",
     "Local supply-gap evidence from Batch 06 (Jiji + Adey, first results page): exact-model listing for this part observed -> 0.25; "
     "only brand-level listings -> 0.375 (midpoint between exact-model and neutral); nothing found on the sources inspected -> 0.50 = NEUTRAL, "
     "because 'not found on the first page of 2 platforms' is not evidence of scarcity (Telegram/Facebook sellers and shops were not inspected). "
     "Changed in v4 from 0.75 after the sensitivity test showed the top 5 rested on this weakest signal.",
     "If the row was not searched (ethiopian_availability = not_established) the factor is left empty and the composite is re-weighted over the "
     "remaining factors (flag scarcity_missing). In this build all 30 rows were searched."),
    ("compatibility",
     "From compatibility_confidence: high 1.0, medium 0.7, low 0.35, insufficient 0.0. No level means year/trim/VIN-confirmed fitment.",
     "'insufficient' is an assessed level (no part identified in the sources inspected), so it is an explicit, documented 0, "
     "not missing data. The basis column says so."),
    ("sourcing_practicality",
     "Can an importer act on the international supplier evidence? Specific part record with a displayed price (row or product_observations) and not "
     "marked unavailable -> 1.0; specific record, price on request / request-a-quote -> 0.75; specific record, no price and no status -> 0.6; "
     "specific record but supplier shows Unavailable -> 0.3; related part or category context only -> 0.2; no part record -> 0.0.",
     "'No part record' is an observed result of the search (explicit 0, documented in the basis column), not missing data."),
    ("evidence_confidence",
     "How much evidence stands behind the row (points, then divided by the 0.95 maximum): part number identified +0.30; number corroborated by a "
     "second catalogue +0.10; supplier price displayed +0.10; fitment confidence high +0.20 / medium +0.10; Ethiopian exact-model listing +0.15; "
     "NHTSA failure data available +0.10; price pairing unverified (ID.4 wipers) -0.05; Ethiopian factor rests only on 'not found' -0.05 (v4).",
     "Every component is a yes/no observed in the data, so this factor is never missing. Rows with little evidence get a low value; "
     "that is the purpose of the factor."),
]

WEIGHTS = [
    ("demand_evidence", 0.30, "Main driver of import value: parts for cars that are visible in the market and parts that wear out or get damaged."),
    ("compatibility", 0.20, "Importing the wrong part is a direct loss; fitment certainty decides whether a part can be stocked at all."),
    ("sourcing_practicality", 0.20, "A part is only a candidate if a supplier, part number and price exist to act on."),
    ("scarcity_evidence", 0.15, "Lowered on purpose: the Ethiopian evidence is the weakest data (first page of 2 platforms, no stock data)."),
    ("evidence_confidence", 0.15, "Lets well-documented rows outrank rows that look good only because data is thin."),
]

# ---------------------------------------------------------------- inputs per vehicle
vis = {m["vehicle_id"]: int(m["listing_count"]) for m in mkt
       if m["evidence_class"] == "category_listing_count" and m["exact_vs_grouped"] == "exact_model"
       and m["source_batch"] != "vehicle_visibility_batch_01" and m["vehicle_id"] in ("seagull", "yuan_up", "id4")}
n_max = max(vis.values())
id4_kw_max = max(int(c["nhtsa_complaints_keyword"]) for c in clean if c["vehicle_id"] == "id4")
prod_price = {p["parent_record_id"] for p in prod if p["price_amount"]}

rows = []
for c in clean:
    rid, vid, cat = c["record_id"], c["vehicle_id"], c["part_category"]
    r = {"record_id": rid, "vehicle_id": vid, "vehicle_model": c["vehicle_model"], "part_category": cat}

    # demand
    V = math.log1p(vis[vid]) / math.log1p(n_max)
    cls, C = PART_CLASS[cat]
    subs = [(V, 0.4), (C, 0.4)]
    if c["nhtsa_data_status"] == "available":
        F = int(c["nhtsa_complaints_keyword"]) / id4_kw_max
        subs.append((F, 0.2)); fb = f"F={F:.2f} ({c['nhtsa_complaints_keyword']} NHTSA complaints mention the part)"
    else:
        fb = "F missing (no NHTSA data - not sold in US), weights re-normalised"
    r["f_demand_evidence"] = round(sum(v * w for v, w in subs) / sum(w for _, w in subs), 4)
    r["demand_basis"] = f"V={V:.2f} ({vis[vid]} Adey listings of the vehicle - listing count); C={C} ({cls}); {fb}"
    r["demand_vehicle_listing_count"] = vis[vid]

    # scarcity
    ea = c["ethiopian_availability"]
    if ea in SCARCITY:
        r["f_scarcity_evidence"] = SCARCITY[ea]
        r["scarcity_basis"] = (f"{ea}; Jiji states {c['et_jiji_listing_count_stated']} ads for the query; {c['et_exact_model_part_listings']} exact-model "
                               f"part listings, {c['et_brand_only_part_listings']} brand-only (first page, {c['et_platforms_inspected']})")
    else:
        r["f_scarcity_evidence"] = None
        r["scarcity_basis"] = "MISSING: row not searched on Ethiopian platforms"

    # compatibility
    cc = c["compatibility_confidence"]
    r["f_compatibility"] = COMPAT[cc]
    r["compatibility_basis"] = f"{cc} ({c['fitment_evidence_status']})" + ("; explicit 0: no part identified in sources inspected" if cc == "insufficient" else "")

    # sourcing practicality
    ev, sa = c["evidence_availability"], c["sourcing_availability"]
    priced = bool(c["displayed_price_amount"]) or rid in prod_price
    if ev == "specific_part_record_found":
        if sa == "supplier_unavailable":
            s, why = 0.3, "record found but supplier shows Unavailable"
        elif priced:
            s, why = 1.0, f"record with displayed price ({c['displayed_price_amount'] or 'see product_observations'} {c['displayed_price_currency'] or ''})".strip()
        elif sa == "request_quote_stock_unknown":
            s, why = 0.75, "record found; price on request / request a quote"
        else:
            s, why = 0.6, "record found; no price or stock statement"
    elif ev in ("related_part_found", "category_context_only"):
        s, why = 0.2, ev
    else:
        s, why = 0.0, "explicit 0: no part record found in sources inspected"
    r["f_sourcing_practicality"] = s
    r["sourcing_basis"] = f"{why}; supplier {c['supplier'] or '-'} ({c['supplier_country'] or '-'})"

    # evidence confidence
    pts, parts = 0.0, []
    if int(c["part_number_count"] or 0) > 0:
        pts += 0.30; parts.append("part no. +0.30")
    if int(c["cited_source_count"] or 0) >= 2:
        pts += 0.10; parts.append("2nd catalogue +0.10")
    if priced:
        pts += 0.10; parts.append("price +0.10")
    if cc == "high":
        pts += 0.20; parts.append("fitment high +0.20")
    elif cc == "medium":
        pts += 0.10; parts.append("fitment medium +0.10")
    if ea == "listing_observed_exact_model":
        pts += 0.15; parts.append("ET exact listing +0.15")
    if c["nhtsa_data_status"] == "available":
        pts += 0.10; parts.append("NHTSA +0.10")
    if rid == "id4__wiper_blade":
        pts -= 0.05; parts.append("price pairing unverified -0.05")
    if ea == "not_found_on_sources_inspected":
        pts -= NOT_FOUND_EC_PENALTY; parts.append(f"ET factor only 'not found' -{NOT_FOUND_EC_PENALTY:.2f}")
    r["f_evidence_confidence"] = round(max(0.0, min(1.0, pts / 0.95)), 4)
    r["evidence_confidence_basis"] = ", ".join(parts) or "no evidence components"

    missing = [k for k in ("f_demand_evidence", "f_scarcity_evidence", "f_compatibility", "f_sourcing_practicality", "f_evidence_confidence") if r[k] is None]
    r["factors_missing"] = "; ".join(missing) or None
    # weak-evidence flags (used in the final checklist)
    flags = []
    if c["evidence_availability"] != "specific_part_record_found":
        flags.append("no specific part record")
    if cc in ("low", "insufficient"):
        flags.append(f"fitment {cc}")
    if c["nhtsa_data_status"] != "available":
        flags.append("no failure data")
    if int(c["cited_source_count"] or 0) < 2 and c["evidence_availability"] == "specific_part_record_found":
        flags.append("single part source")
    if not priced:
        flags.append("no supplier price")
    r["weak_evidence_flags"] = "; ".join(flags) or None
    r["ethiopian_availability"] = ea
    r["et_displayed_prices_etb"] = c["et_displayed_prices_etb"] or None
    r["supplier_price"] = (f"{c['displayed_price_amount']} {c['displayed_price_currency']}" if c["displayed_price_amount"] else
                           ("see product_observations" if rid in prod_price else None))
    r["part_numbers"] = "; ".join(x for x in (c["oem_part_number"], c["aftermarket_part_number"]) if x) or None
    rows.append(r)

for k in ("f_demand_evidence", "f_scarcity_evidence", "f_compatibility", "f_sourcing_practicality", "f_evidence_confidence"):
    assert all(r[k] is None or 0.0 <= r[k] <= 1.0 for r in rows), k
assert len(rows) == 30 and len({r["record_id"] for r in rows}) == 30
assert abs(sum(w for _, w, _ in WEIGHTS) - 1.0) < 1e-9

cols = list(rows[0].keys())
with open(DATA / "scoring_input.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
with open(DATA / "scoring_rules.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["factor", "rule", "missing_data_rule"]); w.writerows(RULES)
with open(DATA / "weights_proposed.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["factor", "weight", "reason"]); w.writerows(WEIGHTS)
for fn in ("cleaned_vehicle_part_evidence.csv", "vehicle_market_evidence.csv", "product_observations.csv", "nhtsa_component_mapping.csv"):
    shutil.copyfile(BASE / fn, DATA / fn)
print("scoring_input.csv:", len(rows), "rows; missing factors:", sum(1 for r in rows if r["factors_missing"]))
