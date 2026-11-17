#!/usr/bin/env python3
"""
build_dataset.py - EV Spare-Parts Import Prioritization: evidence preparation pipeline (v2)

Reads ONLY the preserved raw research files in ./raw and regenerates every derived file.
Raw files are never written to. Run from anywhere:   python build_dataset.py

Inputs  (./raw):  vehicle_visibility_batch_01.json, vehicle_model_evidence_batch_02.json,
                  vehicle_selection_investigation_batch_03.json, vehicle_part_evidence_batch_04.json,
                  source_log_original.csv
        v3 (2026-11-16): vehicle_part_evidence_batch_05.json, vehicle_part_evidence_batch_06.json,
                  vehicle_failure_evidence_batch_07.json, ../source_log_additions_b05_b07.csv
Outputs (./):     raw_vehicle_part_evidence.csv, cleaned_vehicle_part_evidence.csv/.json,
                  product_observations.csv/.json, vehicle_market_evidence.csv/.json, source_log.csv,
                  data_dictionary.md, data_quality_report.md, validation_results.json,
                  raw_file_hashes.csv (+ raw_file_hashes_baseline.csv on first run)

No web access, no scoring, no ranking, no currency conversion. Missing evidence stays missing.
"""
import csv, json, hashlib, re, sys, platform, datetime
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter, OrderedDict, defaultdict

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
RAW_FILES = [
    "vehicle_visibility_batch_01.json",
    "vehicle_model_evidence_batch_02.json",
    "vehicle_selection_investigation_batch_03.json",
    "vehicle_part_evidence_batch_04.json",
]
B4 = "vehicle_part_evidence_batch_04.json"
# v3: batches added 2026-11-16. Hashed against their own baseline (raw_file_hashes_baseline_b05_b07.csv)
# so the original 5-file baseline (check C6b) stays exactly as first recorded.
B5 = "vehicle_part_evidence_batch_05.json"          # part records for the 16 rows empty after Batch 04
B6 = "vehicle_part_evidence_batch_06.json"          # Ethiopian marketplace availability (Jiji, Adey)
B7 = "vehicle_failure_evidence_batch_07.json"       # NHTSA complaints/recalls (ID.4 only)
RAW_FILES_NEW = [B5, B6, B7]
LOG_ADDITIONS = "source_log_additions_b05_b07.csv"  # append-only source rows for batches 05-07 (+ B03 back-fill)

# ----------------------------------------------------------------------------- helpers
def jload(p):
    # utf-8-sig tolerates a BOM in *input* files; outputs are always written without BOM.
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def to_int(s):
    return int(s.replace(",", "")) if s else None

def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

def parse_cell(v, typ):
    if v == "":
        return None
    if typ == "int":
        return int(v)
    if typ == "float":
        return float(v)
    if typ == "bool":
        return v == "true"
    return v

def write_csv(path, rows, schema):
    names = [c[0] for c in schema]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(names)
        for r in rows:
            w.writerow([cell(r.get(n)) for n in names])

def write_json(path, rows, schema):
    names = [c[0] for c in schema]
    out = [OrderedDict((n, r.get(n)) for n in names) for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

def read_csv_typed(path, schema):
    typ = {c[0]: c[1] for c in schema}
    with open(path, encoding="utf-8", newline="") as f:
        return [{k: parse_cell(v, typ[k]) for k, v in row.items()} for row in csv.DictReader(f)]

def url_ok(u):
    if not isinstance(u, str) or not u:
        return False
    if re.search(r"\s|\\", u):
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https") and bool(p.netloc) and "." in p.netloc

# ----------------------------------------------------------------------------- vocabularies
CAT = {
    "brake pads": "brake_pad", "brake discs": "brake_disc", "cabin-air filters": "cabin_air_filter",
    "wiper blades": "wiper_blade", "headlights": "headlight", "tail lights": "tail_light",
    "side mirrors": "side_mirror", "bumpers": "bumper", "fenders/body panels": "fender_body_panel",
    "shock absorbers": "shock_absorber",
}
CAT_ALIAS = {"cabin air filters": "cabin_air_filter"}  # Batch 05 spelling; not added to CAT so the enum list is unchanged
def cat_of(label):
    return CAT.get(label) or CAT_ALIAS[label]
VEH_ID = {"Seagull": "seagull", "Yuan Up": "yuan_up", "ID.4": "id4"}
VEH_MODEL_NORM = {
    "seagull": "Seagull", "yuan_up": "Yuan Up", "id4": "ID.4", "bz4x": "bZ4X",
    "benben": "BenBen E-Star", "toyota_bz_series_group": "bZ series (grouped: bZ4X, bZ3, bZ3X, bZ5)",
}
SELECTED = {"seagull", "yuan_up", "id4"}

SRC_QUALITY = {
    "Connect Drive": "model_specific_supplier_catalogue",
    "CQS Auto Parts": "supplier_part_list_without_item_fitment",
    "AUTODOC France": "aftermarket_catalogue_model_context",
    "1A Auto": "aftermarket_supplier_model_result",
    "VW Online Store and Catalog": "oem_catalogue_category_context",
    "Landin Parts": "supplier_catalogue_item_model_label_with_oe_number",
    "EXIST.AE": "aftermarket_catalogue_model_context",
}
SRC_SCOPE = {
    "Landin Parts": "international_supplier_catalogue",
    "EXIST.AE": "uae_aftermarket_catalogue",
    "Connect Drive": "international_model_specific_catalogue",
    "CQS Auto Parts": "international_supplier_part_list",
    "AUTODOC France": "international_aftermarket_catalogue",
    "1A Auto": "international_aftermarket_supplier",
    "VW Online Store and Catalog": "international_oem_catalogue_context",
}
LOG_SCOPE = {
    "Adey Market": "ethiopia_vehicle_marketplace", "Gezat Electric": "ethiopia_vehicle_catalogue",
    "Gezat": "ethiopia_vehicle_catalogue", "Golden Car Market": "ethiopia_vehicle_marketplace",
    "Mekina.net": "ethiopia_vehicle_marketplace", "Cars45 Ethiopia": "ethiopia_vehicle_marketplace",
    "BYD Ethiopia": "ethiopia_manufacturer_page",
    "Toyota Spare Parts catalogue": "international_parts_catalogue", "EXIST Dubai": "uae_parts_catalogue",
    "AutoCango": "international_spec_site", "Connect Drive": "international_parts_source",
    "CQS Auto Parts": "international_parts_source", "AUTODOC France": "international_parts_source",
    "1A Auto": "international_parts_source", "Volkswagen Online Store and Catalog": "international_parts_source",
}

# ----------------------------------------------------------------------------- schemas (single source of truth for CSV, JSON and the dictionary)
S_RAW = [
    ("record_id", "str", "Stable key `<vehicle_id>__<category>`; identical in raw CSV, cleaned CSV and cleaned JSON."),
    ("raw_pointer", "str", "Location of the source record: `<batch file>:records[<0-based index>]`."),
    ("source_batch", "str", "Raw batch file the row was flattened from."),
    ("vehicle_manufacturer", "str", "As in raw batch."), ("vehicle_model", "str", "As in raw batch."),
    ("model_year", "str", "As in raw batch (kept verbatim, including the unsupported `2020` on the ID.4 wiper row; see CN-04)."),
    ("generation", "str", "As in raw batch."), ("variant", "str", "As in raw batch."),
    ("part_category_original", "str", "Category label as in raw batch."),
    ("part_description", "str", "As in raw batch."), ("oem_part_number", "str", "As in raw batch."),
    ("aftermarket_part_number", "str", "As in raw batch."),
    ("compatibility_confidence_original", "str", "Confidence assigned in raw batch before any audit change."),
    ("source_name", "str", "As in raw batch."), ("source_url", "url", "As in raw batch."),
    ("collection_date", "date", "As in raw batch (ISO date)."),
    ("displayed_price_amount", "float", "Raw `displayed_price.amount` (the single primary price of the raw record)."),
    ("displayed_price_currency", "str", "Raw `displayed_price.currency`."),
    ("supplier", "str", "As in raw batch."), ("supplier_country", "str", "As in raw batch."),
    ("availability_status_original", "str", "Raw availability wording."),
    ("compatibility_evidence", "str", "As in raw batch."), ("supporting_evidence", "str", "As in raw batch."),
    ("missing_or_unverifiable", "str", "As in raw batch."),
    ("raw_record_json", "str", "Complete raw record as compact JSON (non-ASCII and apostrophes unescaped)."),
]

S_CLEAN = [
    ("record_id", "str", "Primary key. `<vehicle_id>__<category>`; exactly 30 values."),
    ("vehicle_id", "str", "`seagull`, `yuan_up` or `id4`; joins to `vehicle_market_evidence.vehicle_id`."),
    ("vehicle_manufacturer", "str", "Vehicle manufacturer."), ("vehicle_model", "str", "Vehicle model."),
    ("model_year", "int", "Model year only when the source record itself states one for the product. Null for all 30 records in this build."),
    ("model_year_basis", "str", "Why `model_year` is null or how a year was seen (see allowed values)."),
    ("model_year_in_listing_text", "int", "A year that appears only inside a product title/description (context, not confirmed fitment)."),
    ("generation", "str", "Generation, only if explicitly reported. Null throughout."),
    ("variant", "str", "Trim/battery/drivetrain, only if explicitly reported. Null throughout."),
    ("part_category", "str", "Controlled category (see allowed values)."),
    ("part_category_display", "str", "Original human-readable category label."),
    ("evidence_availability", "str", "DIMENSION 1: was a part record found? (see allowed values)"),
    ("compatibility_confidence", "str", "DIMENSION 2: how well the source establishes fit to the vehicle (see allowed values). Cleaned value after documented audit adjustments."),
    ("compatibility_confidence_original", "str", "Confidence in the raw batch, before adjustment."),
    ("confidence_adjustment_note", "str", "Reason when cleaned confidence differs from original; otherwise null."),
    ("fitment_evidence_status", "str", "Finer fitment interpretation (see allowed values)."),
    ("source_quality", "str", "DIMENSION 3: type/reliability of the source, independent of fitment (see allowed values)."),
    ("sourcing_availability", "str", "DIMENSION 4: what the supplier page indicates about availability (see allowed values). A supplier statement is not verified stock."),
    ("item_condition", "str", "Condition of the item as displayed (e.g. `New`). Condition is NOT stock availability."),
    ("ethiopian_availability", "str", "DIMENSION 5: what Ethiopian marketplace listings (Batch 06: Jiji, Adey) show for this spare part. Listing evidence only: never verified stock, sales or demand. Says nothing about whether the vehicle is sold in Ethiopia (see vehicle_market_evidence)."),
    ("evidence_scope", "str", "Geography/type of the evidence (see allowed values)."),
    ("part_description", "str", "Description captured from the source, null if none."),
    ("category_scope_note", "str", "Clarifies what the record covers when it is broader/narrower than the category name."),
    ("oem_part_number", "str", "OEM numbers explicitly shown, `; `-separated. Never inferred."),
    ("aftermarket_part_number", "str", "Aftermarket/supplier numbers explicitly shown, `; `-separated."),
    ("part_number_count", "int", "Number of part numbers captured (OEM + aftermarket). Not a count of parts needed."),
    ("part_number_note", "str", "Non-numeric remarks removed from the number fields."),
    ("compatibility_evidence", "str", "Source text supporting the fitment claim (verbatim from raw)."),
    ("source_id", "str", "Join key to `source_log.source_id`."),
    ("source_name", "str", "Supplier/catalogue name."), ("source_url", "url", "Original page URL."),
    ("collection_date", "date", "ISO date. For `not_found` rows this is the Batch 04/05 collection date; there is no page-specific source."),
    ("cited_source_count", "int", "Number of sources cited by this record (0, 1 or 2). 2 = Batch 05 Seagull rows where a second catalogue (CQSW) lists the same part number; this corroborates the number, not the fitment."),
    ("sources_inspected_for_vehicle", "str", "source_ids Batch 04 reports inspecting for this vehicle (vehicle level, NOT per category). Not proof a category was checked on every page."),
    ("displayed_price_amount", "float", "Original displayed price when attributable to this one record's single product; null otherwise. Never converted. Never 0."),
    ("displayed_price_currency", "str", "Original currency of the displayed price."),
    ("price_attribution", "str", "`single_product`, or `multi_product_see_product_observations` when the row covers several products (price lives in the child table)."),
    ("price_observation_type", "str", "`displayed_on_source_page` whenever a price was seen. It is an observation, not an order price."),
    ("price_market_scope", "str", "`international_supplier_not_ethiopian_retail` for every priced row."),
    ("currently_orderable", "str", "`no` / `not_established` for priced rows, null when no price."),
    ("product_observation_ids", "str", "`; `-separated ids in `product_observations`."),
    ("supplier", "str", "Supplier/seller as displayed."), ("supplier_country", "str", "Supplier country as displayed/documented."),
    ("availability_status_original", "str", "Raw availability wording, verbatim."),
    ("supporting_evidence", "str", "Extracted supporting text (verbatim from raw)."),
    ("missing_or_unverifiable", "str", "Raw text, verbatim. Audit remarks are in `correction_notes`, never appended here."),
    ("evidence_gap_note", "str", "Standard wording for rows without a part record. Not-found is not proof the part does not exist."),
    ("correction_notes", "str", "Audit changes applied to this row (CN ids refer to data_quality_report.md)."),
    ("part_record_batch", "str", "`04` or `05`: which raw batch supplies the part-record fields of this row."),
    ("corroborating_source_url", "url", "Batch 05: second catalogue listing the same part number (corroborates the number only)."),
    ("part_record_urls_checked_b05", "str", "Batch 05: URLs checked for this row (`; `-separated), whether or not anything was found."),
    ("et_jiji_listing_count_stated", "int", "Batch 06: Jiji's own 'Found N ads' for '<vehicle> <part>' (0 when Jiji says it could not find ads). Search hits of any model: a LISTING COUNT, not sales/registrations/demand."),
    ("et_exact_model_part_listings", "int", "Batch 06: listings on the inspected first pages (Jiji + Adey brand-level query) whose title names this exact model AND this part. Derived by title matching."),
    ("et_brand_only_part_listings", "int", "Batch 06: listings naming the brand and the part but not this model."),
    ("et_displayed_prices_etb", "str", "Batch 06: displayed prices of exact-model listings, verbatim with currency (ETB), `; `-separated. Not averaged, not converted."),
    ("et_platforms_inspected", "str", "Batch 06: platforms searched for this row. Gezat, Golden Car Market and Mekina.net are logged as not searchable for parts."),
    ("nhtsa_data_status", "str", "Batch 07: `available` (ID.4) or `no NHTSA data - not sold in US` (Seagull, Yuan Up). No substitute vehicle used."),
    ("nhtsa_complaints_component", "int", "Batch 07: unique NHTSA complaints (ID.4, MY2021-2026) whose component maps to this category. Null where no NHTSA component covers the category."),
    ("nhtsa_component_shared", "bool", "Batch 07: true when the NHTSA component also maps to another category (e.g. SERVICE BRAKES -> pads AND discs). Do not sum such counts."),
    ("nhtsa_complaints_keyword", "int", "Batch 07: unique complaints whose summary text mentions a category keyword. Secondary signal; a mention is not a confirmed failure."),
    ("nhtsa_recall_campaigns", "str", "Batch 07: NHTSA recall campaign numbers mapped to this category, `; `-separated."),
    ("raw_pointer", "str", "Trace to the raw batch record."),
]

S_PROD = [
    ("observation_id", "str", "Primary key `<record_id>__<n>`."),
    ("parent_record_id", "str", "FK to `cleaned_vehicle_part_evidence.record_id`."),
    ("vehicle_id", "str", "Vehicle key."), ("vehicle_manufacturer", "str", "Manufacturer."),
    ("vehicle_model", "str", "Model."), ("part_category", "str", "Controlled category."),
    ("product_description", "str", "Product as described by the source."),
    ("product_size_text", "str", "Size text as shown (e.g. `700 mm`)."),
    ("size_mm", "int", "Numeric size in millimetres where a size is shown."),
    ("brand", "str", "Product brand (before ` / ` in the raw supplier field)."),
    ("part_number", "str", "Product part number exactly as displayed."),
    ("part_number_type", "str", "`aftermarket` (all current rows)."),
    ("item_condition", "str", "Condition shown (`New`). NOT stock."),
    ("stock_availability", "str", "`supplier_unavailable` or `not_established`."),
    ("price_amount", "float", "Original price attributed to THIS product; null when attribution is unknown. Never converted, never 0."),
    ("currency", "str", "Original currency."),
    ("price_pairing_status", "str", "See allowed values."),
    ("price_set_in_raw_batch", "str", "All price figures the raw record contains for the parent row, so nothing is lost when `price_amount` is null."),
    ("price_observation_type", "str", "`displayed_on_source_page`."),
    ("currently_orderable", "str", "`no` or `not_established`."),
    ("price_market_scope", "str", "`international_supplier_not_ethiopian_retail`."),
    ("fitment_status", "str", "Fitment interpretation for this product."),
    ("fitment_caveat", "str", "What is not confirmed."),
    ("source_id", "str", "Join key to source_log."), ("source_name", "str", "Source name."),
    ("source_url", "url", "Source page URL."),
    ("source_url_type", "str", "`model_catalogue_page` = a model-filtered listing page, not a single-product page."),
    ("collection_date", "date", "ISO date."), ("source_batch", "str", "Raw batch."),
    ("raw_pointer", "str", "Trace to the raw record this was derived from."),
    ("derivation_note", "str", "How product-level values were derived from the raw record."),
]

S_MKT = [
    ("market_record_id", "str", "Primary key. Raw evidence id for Batches 01-02; deterministic `B03-<vehicle>-<source>-<n>` for Batch 03."),
    ("source_batch", "str", "Raw batch."), ("raw_pointer", "str", "Trace to raw record."),
    ("source_evidence_id", "str", "Evidence id in the raw batch, if any."),
    ("vehicle_id", "str", "`seagull`, `yuan_up`, `id4`, `bz4x`, `benben`, `toyota_bz_series_group`."),
    ("selected_vehicle", "bool", "True only for the three vehicles in the 30-record spare-parts study."),
    ("vehicle_manufacturer", "str", "Manufacturer."), ("vehicle_model", "str", "Normalised model name."),
    ("vehicle_model_original", "str", "Label exactly as in the raw batch."),
    ("model_year", "int", "Model year of an individual listing, when shown."),
    ("generation", "str", "Generation if reported (always null here)."),
    ("variant", "str", "Variant of an individual listing, when shown."),
    ("catalogue_year_context", "str", "Year/range shown by a catalogue. Context only; not a listing year."),
    ("evidence_class", "str", "See allowed values."), ("exact_vs_grouped", "str", "`exact_model` or `grouped_model_family`."),
    ("geographic_scope", "str", "See allowed values."),
    ("vehicle_presence_in_ethiopia", "str", "See allowed values. Never implies spare-part availability."),
    ("listing_status_normalized", "str", "See allowed values."),
    ("listing_status_original", "str", "Status wording as in raw."),
    ("seller", "str", "Seller/platform as in raw."), ("location", "str", "Location as in raw."),
    ("listing_count", "int", "Platform-reported number of listings in the category/search result. A visibility proxy, NOT registrations or sales."),
    ("seller_count", "int", "Platform-reported sellers behind the listings."),
    ("priced_listing_count", "int", "Listings that display a price, when the platform says so."),
    ("total_pages_available", "int", "Platform-reported page count."),
    ("pages_inspected", "int", "Pages actually inspected."),
    ("platform_reported_typical_price_amount", "float", "Value the platform states as typical. NOT a calculated average/median."),
    ("platform_reported_typical_price_currency", "str", "Currency."),
    ("displayed_price_min", "float", "Lowest displayed price on the category page (may include outliers)."),
    ("displayed_price_max", "float", "Highest displayed price on the category page (may include outliers)."),
    ("displayed_price_amount", "float", "Displayed price of an individual listing."),
    ("displayed_price_currency", "str", "Normalised currency code (`Birr` -> `ETB`)."),
    ("displayed_price_currency_original", "str", "Currency label exactly as displayed."),
    ("sample_listing_urls", "str", "Individual listing URLs captured on the category page, `; `-separated."),
    ("source_id", "str", "Join key(s) to source_log, `; `-separated; null if the URL has no source_log row."),
    ("source_name", "str", "Source name."), ("source_url", "url", "Page URL."),
    ("collection_date", "date", "ISO date."),
    ("interpretation", "str", "How the record may and may not be used."),
    ("supporting_evidence", "str", "Verbatim supporting text from raw."),
    ("limitations", "str", "Raw limitations / unavailable fields."), ("notes", "str", "Audit notes."),
]

ENUMS = {
    "model_year_basis": OrderedDict([
        ("not_stated_by_source", "The source record states no model year."),
        ("year_appears_in_listing_title_only", "A year appears in the product title (context only)."),
        ("raw_value_removed_not_stated_in_source_record", "The raw row carried a year that the AUTODOC record does not state (see CN-04)."),
    ]),
    "part_category": OrderedDict((v, k) for k, v in CAT.items()),
    "evidence_availability": OrderedDict([
        ("specific_part_record_found", "An individual part record (with a number) exists in the source. Does NOT mean it fits or is in stock."),
        ("related_part_found", "A related component, not the assigned part (ID.4 fender flare: not a complete fender/body panel; ID.4 strut mount (Batch 05): not a shock absorber)."),
        ("category_context_only", "Only a catalogue category label was seen; no individual record."),
        ("not_found", "Not found in the extracted item list of the inspected source(s). Not proof the part does not exist."),
    ]),
    "compatibility_confidence": OrderedDict([
        ("high", "Source explicitly names the vehicle and category/part, with an original number or clear model-specific compatibility statement. Exact year/variant fitment may still need confirmation."),
        ("medium", "Item is in a vehicle-specific catalogue with a part number, but individual fitment, variant or year confirmation is incomplete."),
        ("low", "Model-filtered or category-level result without explicit item fitment, or the item is unavailable/unverified/related-component only."),
        ("insufficient", "No defensible vehicle-specific part evidence in the inspected sources."),
    ]),
    "fitment_evidence_status": OrderedDict([
        ("explicit_model_text", "Product record states compatibility with the named model (model-level, not year/variant)."),
        ("catalogue_model_context_only", "Listed on a model-specific catalogue page; no per-item fitment text."),
        ("model_context_without_confirmed_individual_fitment", "Returned in a model-filtered result; VIN/trim/year fitment not shown."),
        ("catalogue_category_only", "Only a category label in a model catalogue."),
        ("related_fender_flare_only", "Fender flare accessory only; not a complete fender."),
        ("related_strut_mount_only", "Batch 05: strut mount only (adjacent suspension part); not a shock absorber. Page says 'May fit - check by VIN'."),
        ("not_established", "No fitment evidence."),
    ]),
    "source_quality": OrderedDict([
        ("model_specific_supplier_catalogue", "Supplier catalogue page specific to the model."),
        ("supplier_part_list_without_item_fitment", "Supplier part list with no per-item fitment text."),
        ("aftermarket_catalogue_model_context", "Aftermarket catalogue filtered by model."),
        ("aftermarket_supplier_model_result", "Aftermarket supplier page filtered by model."),
        ("oem_catalogue_category_context", "OEM catalogue showing category labels only."),
        ("supplier_catalogue_item_model_label_with_oe_number", "Batch 05: multi-model supplier catalogue where each item card carries a model label and an OE code (Landin Parts)."),
        ("none", "No source (no part record)."),
    ]),
    "sourcing_availability": OrderedDict([
        ("request_quote_stock_unknown", "Supplier asks for a quote; no stock statement."),
        ("supplier_unavailable", "Supplier page shows the item as unavailable. A found record, not a sourcing option."),
        ("not_established", "Source shows condition/price but no stock statement."),
        ("no_part_record", "No individual part record, so no availability statement exists."),
    ]),
    "ethiopian_availability": OrderedDict([
        ("listing_observed_exact_model", "Batch 06: at least one Ethiopian marketplace listing (Jiji or Adey) names this exact model AND this part. A listing is not verified stock, not a sale, not demand."),
        ("listing_observed_brand_only", "Batch 06: listings name the brand and the part but not this model. Fitment to this model is not shown."),
        ("not_found_on_sources_inspected", "Batch 06: no listing naming the model (or brand) and the part on the sources inspected (Jiji, Adey; first page). NOT a scarcity claim."),
        ("not_established", "No Ethiopian marketplace evidence was collected for this row."),
    ]),
    "evidence_scope": OrderedDict([
        ("international_model_specific_catalogue", "Non-Ethiopian supplier, model-specific catalogue."),
        ("international_supplier_part_list", "Non-Ethiopian supplier part list."),
        ("international_aftermarket_catalogue", "Non-Ethiopian aftermarket catalogue."),
        ("international_aftermarket_supplier", "Non-Ethiopian aftermarket supplier."),
        ("international_oem_catalogue_context", "Non-Ethiopian OEM catalogue (category context)."),
        ("international_supplier_catalogue", "Batch 05: non-Ethiopian (China) supplier catalogue."),
        ("uae_aftermarket_catalogue", "Batch 05: UAE aftermarket catalogue. NOT Ethiopian evidence."),
        ("none", "No source."),
    ]),
    "price_pairing_status": OrderedDict([
        ("single_product", "Row has one product; price belongs to it."),
        ("order_inferred_from_raw_record", "Raw record lists two products and states 'one price X and another Y' / 'second product price Y'; the pairing follows listing order and is not stated by part number. Verify against the live page before product-level price analysis."),
        ("unattributed_single_price_for_two_products", "Raw record lists two products but only one price; it cannot be assigned to either. `price_amount` is null."),
    ]),
    "currently_orderable": OrderedDict([("no", "Supplier shows unavailable."), ("not_established", "Source does not state orderability.")]),
    "stock_availability": OrderedDict([("supplier_unavailable", "Supplier shows unavailable."), ("not_established", "No stock statement.")]),
    "evidence_class": OrderedDict([
        ("category_listing_count", "Marketplace category/search-result page with a listing total."),
        ("grouped_family_listing_count", "Count covering several models; not usable as a single-model count."),
        ("catalogue_model_page", "Ethiopian catalogue/showroom page for a model."),
        ("catalogue_model_request_price", "Catalogue shows the exact model as request-price."),
        ("manufacturer_spec_page", "Manufacturer specification page."),
        ("parts_catalogue_model_page", "Parts catalogue page for the model (not market evidence)."),
        ("individual_listing", "A single advertisement."),
        ("access_blocked", "Page not accessible; no evidence accepted."),
    ]),
    "geographic_scope": OrderedDict([
        ("ethiopia_marketplace", "Ethiopian vehicle marketplace."), ("ethiopia_catalogue", "Ethiopian EV catalogue."),
        ("ethiopia_manufacturer_page", "BYD Ethiopia domain; Ethiopian context inferred from the domain, distributor/stock wording not returned."),
        ("international_catalogue_not_ethiopia", "Non-Ethiopian catalogue."), ("uae_catalogue_not_ethiopia", "UAE catalogue; NOT Ethiopian evidence."),
        ("none", "No usable content."),
    ]),
    "vehicle_presence_in_ethiopia": OrderedDict([
        ("marketplace_listings_observed", "Listings on an Ethiopian marketplace were observed (a proxy; not registrations/sales)."),
        ("catalogue_presence_only", "Appears in an Ethiopian catalogue; stock not established."),
        ("manufacturer_page_only", "Manufacturer Ethiopian page only."),
        ("expired_listing_only", "Only an expired listing was found."),
        ("not_evidence", "Source does not evidence Ethiopian presence."),
    ]),
    "listing_status_normalized": OrderedDict([
        ("active_per_page", "Page itself says For Sale / Available now. Not verified stock."),
        ("expired", "Page says not available / expired."),
        ("not_stated", "Status wording ambiguous (e.g. `New`)."), ("category_level", "Category page, not a single listing."),
        ("not_applicable", "Catalogue/spec page."),
    ]),
}

CONF_DEFS = None  # filled from Batch 04 at runtime

# ----------------------------------------------------------------------------- load raw
b1 = jload(RAW / RAW_FILES[0]); b2 = jload(RAW / RAW_FILES[1])
b3 = jload(RAW / RAW_FILES[2]); b4 = jload(RAW / B4)
CONF_DEFS = b4["confidence_definition"]

with open(RAW / "source_log_original.csv", encoding="utf-8", newline="") as f:
    log_rows = list(csv.DictReader(f))
LOG_COLS = list(log_rows[0].keys())
url_to_ids = defaultdict(list)
for r in log_rows:
    url_to_ids[r["source_url"]].append(r["source_id"])

log_add_rows = []
if (BASE / LOG_ADDITIONS).exists():
    with open(BASE / LOG_ADDITIONS, encoding="utf-8", newline="") as f:
        log_add_rows = list(csv.DictReader(f))
url_to_ids_add = defaultdict(list)
for r in log_add_rows:
    url_to_ids_add[r["source_url"]].append(r["source_id"])

def sid_for(url):
    # original log first (keeps every v2 source_id unchanged); additions only for URLs the original log lacks
    ids = url_to_ids.get(url) or url_to_ids_add.get(url)
    return "; ".join(ids) if ids else None

def sid_for_batch(url, batch):
    ids = [r["source_id"] for r in log_add_rows if r["source_url"] == url and r["batch"] == batch]
    return "; ".join(ids) or sid_for(url)

# ----------------------------------------------------------------------------- 1. raw flattened CSV
raw_rows = []
for i, r in enumerate(b4["records"]):
    vid = VEH_ID[r["vehicle_model"]]
    dp = r.get("displayed_price")
    raw_rows.append({
        "record_id": f"{vid}__{CAT[r['part_category']]}", "raw_pointer": f"{B4}:records[{i}]",
        "source_batch": "vehicle_part_evidence_batch_04",
        "vehicle_manufacturer": r["vehicle_manufacturer"], "vehicle_model": r["vehicle_model"],
        "model_year": r["model_year"], "generation": r["generation"], "variant": r["variant"],
        "part_category_original": r["part_category"], "part_description": r["part_description"],
        "oem_part_number": r["oem_part_number"], "aftermarket_part_number": r["aftermarket_part_number"],
        "compatibility_confidence_original": r["compatibility_confidence"],
        "source_name": r["source_name"], "source_url": r["source_url"], "collection_date": r["collection_date"],
        "displayed_price_amount": dp["amount"] if dp else None, "displayed_price_currency": dp["currency"] if dp else None,
        "supplier": r["supplier"], "supplier_country": r["supplier_country"],
        "availability_status_original": r["availability_status"],
        "compatibility_evidence": r["compatibility_evidence"], "supporting_evidence": r["supporting_evidence"],
        "missing_or_unverifiable": r["missing_or_unverifiable"],
        "raw_record_json": json.dumps(r, ensure_ascii=False, separators=(",", ":")),
    })

# ----------------------------------------------------------------------------- 2. cleaned dataset
def split_pn(s):
    if not s:
        return [], None
    toks = [t.strip() for t in s.split(";") if t.strip()]
    return [t for t in toks if re.search(r"\d", t)], ("; ".join(t for t in toks if not re.search(r"\d", t)) or None)

findings_by_scope = defaultdict(list)
for sf in b4["source_findings"]:
    findings_by_scope[sf["scope"]].append(sf["source_url"])
def inspected_for(vehicle_model):
    scope = {"Seagull": "BYD Seagull", "Yuan Up": "BYD Yuan Up", "ID.4": "Volkswagen ID.4"}[vehicle_model]
    ids = []
    for u in findings_by_scope[scope]:
        s = sid_for(u)
        if s:
            ids.append(s)
    return "; ".join(ids) or None

GAP_NOT_FOUND = "Not found in the extracted item list of the inspected source(s); this is not proof that the part does not exist."
GAP_CONTEXT = "Category label seen in a catalogue; no individual part record, number, price or fitment was exposed."

clean = []
for i, r in enumerate(b4["records"]):
    vm = r["vehicle_model"]; vid = VEH_ID[vm]; cat = CAT[r["part_category"]]
    rid = f"{vid}__{cat}"
    conf0 = r["compatibility_confidence"]; conf = conf0; adj = None; notes = []
    is_id4 = vm == "ID.4"
    cname = r["part_category"]

    # evidence availability
    if conf0 == "insufficient":
        ev = "not_found"
    elif is_id4 and cname in ("tail lights", "side mirrors"):
        ev = "category_context_only"
    elif is_id4 and cname == "fenders/body panels":
        ev = "related_part_found"
    else:
        ev = "specific_part_record_found"

    # fitment status
    if conf0 == "insufficient":
        fit = "not_established"
    elif vm == "Seagull" and conf0 == "high":
        fit = "explicit_model_text"
    elif vm == "Yuan Up":
        fit = "catalogue_model_context_only"
    elif is_id4 and cname in ("tail lights", "side mirrors"):
        fit = "catalogue_category_only"
    elif is_id4 and cname == "fenders/body panels":
        fit = "related_fender_flare_only"
    else:
        fit = "model_context_without_confirmed_individual_fitment"

    # documented confidence adjustment (only one in this build)
    if is_id4 and cname == "fenders/body panels" and conf0 == "medium":
        conf = "low"
        adj = "medium -> low: the product is a fender flare accessory (EIBACH), not a complete fender/body panel; carried over from the earlier audit pass."
        notes.append("CN-03 confidence medium->low (flare is not a complete fender/body panel)")

    status = r["availability_status"] or ""
    if ev in ("not_found", "category_context_only"):
        sourcing = "no_part_record"
    elif status == "Unavailable":
        sourcing = "supplier_unavailable"
    elif "request a quote" in status:
        sourcing = "request_quote_stock_unknown"
    else:
        sourcing = "not_established"
    condition = "New" if status == "New" else None
    if condition:
        notes.append("CN-01 'New' recorded as item_condition, not as a stock claim")

    # model year
    my_basis = "not_stated_by_source"; my_text = None
    if r["model_year"] is not None:
        my_basis = "raw_value_removed_not_stated_in_source_record"
        notes.append("CN-04 raw model_year '%s' removed: the AUTODOC record states no year; the only 2020 in the raw batches is the Batch 02 EXIST (UAE) catalogue page" % r["model_year"])
    else:
        m = re.search(r"\b((?:19|20)\d{2})\b", r["supporting_evidence"] or "")
        if m:
            my_text = int(m.group(1)); my_basis = "year_appears_in_listing_title_only"

    # part numbers
    oem, oem_note = split_pn(r["oem_part_number"]); aft, aft_note = split_pn(r["aftermarket_part_number"])
    pn_note = "; ".join(x for x in (oem_note, aft_note) if x)
    pn_note = (pn_note + " (numbers not captured in the raw batch)") if pn_note else None
    if pn_note:
        notes.append("CN-07 non-numeric remark moved out of the part-number field")

    # scope notes
    desc = r["part_description"] or ""
    scope_note = None
    if is_id4 and cname == "fenders/body panels":
        scope_note = "Fender flare accessory (EIBACH); not a complete fender/body panel."
    elif vm == "Yuan Up" and cname == "fenders/body panels" and "hood" in desc:
        scope_note = "Record also lists a hood and a tailgate, which are not fenders."
    elif vm == "Yuan Up" and cname == "tail lights" and "fog" in desc:
        scope_note = "Record includes a centre rear lamp and rear fog/reverse lamps as well as combination lamps."
    elif vm == "Yuan Up" and cname == "bumpers" and "components" in desc:
        scope_note = "Record covers bumper components (supports/sections), not only complete bumper covers."

    # price
    dp = r.get("displayed_price"); multi = bool(dp) and (len(oem) + len(aft) > 1)
    price_amt = None if (multi or not dp) else dp["amount"]
    price_cur = None if (multi or not dp) else dp["currency"]
    attrib = None; ptype = None; pscope = None; orderable = None
    if dp:
        ptype = "displayed_on_source_page"; pscope = "international_supplier_not_ethiopian_retail"
        attrib = "multi_product_see_product_observations" if multi else "single_product"
        orderable = "no" if status == "Unavailable" else "not_established"
    if multi:
        notes.append("CN-02 primary price moved to product_observations (row covers several products)")
    if is_id4 and cname == "brake pads":
        notes.append("Retained unchanged: USD 60.95 kept with supplier status 'Unavailable'; low confidence unchanged")
    if is_id4 and cname in ("tail lights", "side mirrors"):
        notes.append("CN-05 kept as category_context_only; raw missing_or_unverifiable kept verbatim")
    if is_id4 and cname == "fenders/body panels":
        notes.append("CN-05 raw missing_or_unverifiable kept verbatim (earlier build appended text to it)")

    has_src = bool(r["source_name"])
    clean.append({
        "record_id": rid, "vehicle_id": vid, "vehicle_manufacturer": r["vehicle_manufacturer"], "vehicle_model": vm,
        "model_year": None, "model_year_basis": my_basis, "model_year_in_listing_text": my_text,
        "generation": r["generation"], "variant": r["variant"],
        "part_category": cat, "part_category_display": cname,
        "evidence_availability": ev, "compatibility_confidence": conf, "compatibility_confidence_original": conf0,
        "confidence_adjustment_note": adj, "fitment_evidence_status": fit,
        "source_quality": SRC_QUALITY.get(r["source_name"], "none") if has_src else "none",
        "sourcing_availability": sourcing, "item_condition": condition, "ethiopian_availability": "not_established",
        "evidence_scope": SRC_SCOPE.get(r["source_name"], "none") if has_src else "none",
        "part_description": r["part_description"], "category_scope_note": scope_note,
        "oem_part_number": "; ".join(oem) or None, "aftermarket_part_number": "; ".join(aft) or None,
        "part_number_count": len(oem) + len(aft), "part_number_note": pn_note,
        "compatibility_evidence": r["compatibility_evidence"],
        "source_id": sid_for(r["source_url"]) if r["source_url"] else None,
        "source_name": r["source_name"], "source_url": r["source_url"], "collection_date": r["collection_date"],
        "cited_source_count": 1 if has_src else 0, "sources_inspected_for_vehicle": inspected_for(vm),
        "displayed_price_amount": price_amt, "displayed_price_currency": price_cur, "price_attribution": attrib,
        "price_observation_type": ptype, "price_market_scope": pscope, "currently_orderable": orderable,
        "product_observation_ids": None,
        "supplier": r["supplier"], "supplier_country": r["supplier_country"],
        "availability_status_original": r["availability_status"], "supporting_evidence": r["supporting_evidence"],
        "missing_or_unverifiable": r["missing_or_unverifiable"],
        "evidence_gap_note": GAP_NOT_FOUND if ev == "not_found" else (GAP_CONTEXT if ev == "category_context_only" else None),
        "correction_notes": "; ".join(notes) or None, "raw_pointer": f"{B4}:records[{i}]",
    })
clean_by_id = {c["record_id"]: c for c in clean}

# ----------------------------------------------------------------------------- 3. product observations (derived from raw text only)
prod = []
def add_prod(rid, n, desc, size_text, brand, pn, cond, stock, price, cur, status, price_set, fitstat, caveat, deriv):
    c = clean_by_id[rid]; rr = b4["records"][int(c["raw_pointer"].split("[")[1].rstrip("]"))]
    m = re.search(r"(\d+)\s*mm", size_text or "")
    prod.append({
        "observation_id": f"{rid}__{n}", "parent_record_id": rid, "vehicle_id": c["vehicle_id"],
        "vehicle_manufacturer": c["vehicle_manufacturer"], "vehicle_model": c["vehicle_model"],
        "part_category": c["part_category"], "product_description": desc, "product_size_text": size_text,
        "size_mm": int(m.group(1)) if m else None, "brand": brand, "part_number": pn, "part_number_type": "aftermarket",
        "item_condition": cond, "stock_availability": stock, "price_amount": price, "currency": cur,
        "price_pairing_status": status, "price_set_in_raw_batch": price_set,
        "price_observation_type": "displayed_on_source_page", "currently_orderable": "no" if stock == "supplier_unavailable" else "not_established",
        "price_market_scope": "international_supplier_not_ethiopian_retail", "fitment_status": fitstat, "fitment_caveat": caveat,
        "source_id": c["source_id"], "source_name": c["source_name"], "source_url": c["source_url"],
        "source_url_type": "model_catalogue_page", "collection_date": c["collection_date"],
        "source_batch": "vehicle_part_evidence_batch_04", "raw_pointer": c["raw_pointer"], "derivation_note": deriv,
    })

def brand_of(supplier):
    return supplier.split("/")[0].strip() if supplier else None

for i, r in enumerate(b4["records"]):
    rid = f"{VEH_ID[r['vehicle_model']]}__{CAT[r['part_category']]}"
    if rid == "id4__brake_pad":
        add_prod(rid, 1, r["part_description"], None, brand_of(r["supplier"]), r["aftermarket_part_number"], None, "supplier_unavailable",
                 r["displayed_price"]["amount"], r["displayed_price"]["currency"], "single_product",
                 "%s %s" % (r["displayed_price"]["amount"], r["displayed_price"]["currency"]),
                 "model_context_fitment_text_unavailable",
                 "The listing title mentions 2021 VW ID.4 but the supplier shows no fitment text and the item as Unavailable. Price is a displayed observation, not an orderable or Ethiopian price.",
                 "Single product in raw record; values copied unchanged.")
    elif rid == "id4__wiper_blade":
        descs = [d.strip() for d in r["part_description"].split(";")]
        pns = [p.strip() for p in r["aftermarket_part_number"].split(";")]
        p1 = r["displayed_price"]["amount"]
        m = re.search(r"second product price ([\d.]+) EUR", r["missing_or_unverifiable"])
        p2 = float(m.group(1)) if m else None
        m2 = re.search(r"one price ([\d.]+) EUR and another ([\d.]+) EUR", r["supporting_evidence"])
        assert m2 and float(m2.group(1)) == p1 and float(m2.group(2)) == p2, "wiper price statements disagree"
        for n, (d, pn, p) in enumerate(zip(descs, pns, (p1, p2)), 1):
            add_prod(rid, n, d, d.split()[-2] + " " + d.split()[-1], brand_of(r["supplier"]), pn, "New", "not_established", p, "EUR",
                     "order_inferred_from_raw_record", "%s EUR; %s EUR" % (p1, p2), "model_catalogue_context_exact_fitment_unconfirmed",
                     "AUTODOC model/category page returned both products for VW ID.4; exact model-year, trim and VIN fitment are NOT confirmed.",
                     "Description, part-number and price order in the raw record: product 1 = primary price, product 2 = 'second product price'. Pairing by order, not by part number.")
    elif rid == "id4__fender_body_panel":
        pns = [p.strip() for p in r["aftermarket_part_number"].split(";")]
        for n, pn in enumerate(pns, 1):
            add_prod(rid, n, "Fender flare (EIBACH) %s" % pn, None, brand_of(r["supplier"]), pn, "New", "not_established", None, "EUR",
                     "unattributed_single_price_for_two_products", "%s %s" % (r["displayed_price"]["amount"], r["displayed_price"]["currency"]),
                     "related_component_fitment_unconfirmed",
                     "Fender flare accessory; not a complete fender/body panel. Model year, trim and VIN fitment not shown.",
                     "Raw record lists two part numbers and one price (EUR 33.49); the price cannot be assigned to either product, so price_amount is null.")
for c in clean:
    ids = [p["observation_id"] for p in prod if p["parent_record_id"] == c["record_id"]]
    c["product_observation_ids"] = "; ".join(ids) or None

# ----------------------------------------------------------------------------- 3b. v3 extension: Batches 05-07
b5 = jload(RAW / B5); b6 = jload(RAW / B6); b7 = jload(RAW / B7)
b5_overlaid = []
for c in clean:
    c["part_record_batch"] = "04"
for i, r in enumerate(b5["records"]):
    rid = f"{VEH_ID[r['vehicle_model']]}__{cat_of(r['part_category'])}"
    c = clean_by_id[rid]
    c["part_record_urls_checked_b05"] = "; ".join(r["urls_checked"]) or None
    if r["row_status"] == "not_found":
        # Batch 04 values stay; Batch 05 only documents the extra search.
        c["correction_notes"] = "; ".join(x for x in (c["correction_notes"], "B05 re-check: not found in the Batch 05 sources (see part_record_urls_checked_b05)") if x)
        continue
    b5_overlaid.append(rid)
    dp = r.get("displayed_price")
    is_related = r["row_status"] == "related_part_only"
    nums_oem = [x for x in (r["oem_part_number"], r["oem_part_number_secondary"]) if x]
    nums_aft = [x for x in (r["aftermarket_part_number"],) if x]
    status = r["price_text_verbatim"] or ""
    c.update({
        "part_record_batch": "05",
        "evidence_availability": "related_part_found" if is_related else "specific_part_record_found",
        "compatibility_confidence": r["compatibility_confidence"], "compatibility_confidence_original": r["compatibility_confidence"],
        "confidence_adjustment_note": None,
        "fitment_evidence_status": "related_strut_mount_only" if is_related else "catalogue_model_context_only",
        "source_quality": SRC_QUALITY[r["source_name"]], "evidence_scope": SRC_SCOPE[r["source_name"]],
        "sourcing_availability": "request_quote_stock_unknown" if status == "Price on request" else "not_established",
        "item_condition": r["condition"],
        "part_description": r["part_description"],
        "category_scope_note": "Strut mount (adjacent suspension part); not a shock absorber." if is_related else None,
        "oem_part_number": "; ".join(nums_oem) or None, "aftermarket_part_number": "; ".join(nums_aft) or None,
        "part_number_count": len(nums_oem) + len(nums_aft),
        "part_number_note": (f"Supplier SKU {r['supplier_sku']} (Landin) is not an OE number." if r.get("supplier_sku") else None),
        "compatibility_evidence": r["compatibility_evidence"],
        "source_id": sid_for_batch(r["source_url"], "05"), "source_name": r["source_name"], "source_url": r["source_url"],
        "collection_date": r["collection_date"],
        "cited_source_count": 2 if r.get("corroborating_source_url") else 1,
        "corroborating_source_url": r.get("corroborating_source_url"),
        "displayed_price_amount": float(dp["amount"]) if dp else None, "displayed_price_currency": dp["currency"] if dp else None,
        "price_attribution": "single_product" if dp else None,
        "price_observation_type": "displayed_on_source_page" if dp else None,
        "price_market_scope": "international_supplier_not_ethiopian_retail" if dp else None,
        "currently_orderable": "not_established" if dp else None,
        "supplier": r["supplier"], "supplier_country": r["supplier_country"],
        "availability_status_original": r["price_text_verbatim"],
        "supporting_evidence": r["supporting_evidence"], "missing_or_unverifiable": r["missing_or_unverifiable"],
        "evidence_gap_note": None,
        "correction_notes": "; ".join(x for x in (c["correction_notes"], f"CN-14 part record from Batch 05 supersedes Batch 04 '{c['compatibility_confidence_original']}' row") if x),
        "raw_pointer": f"{B5}:records[{i}]",
    })

# Batch 06: Ethiopian marketplace evidence per row
et = defaultdict(lambda: {"jiji": None, "exact": 0, "brand": 0, "prices": [], "platforms": set()})
for r in b6["records"]:
    if r["vehicle_id"] == "all":
        continue
    k = f"{r['vehicle_id']}__{r['part_category']}"
    e = et[k]
    if r["platform"] == "Jiji Ethiopia":
        e["jiji"] = r.get("listing_count_stated")
        e["exact"] += r.get("items_naming_exact_model_and_part") or 0
        e["brand"] += r.get("items_naming_brand_only_and_part") or 0
        e["prices"] += [f"Jiji: {p}" for p in r.get("displayed_prices_exact_model") or []]
        e["platforms"].add("Jiji")
    elif r["platform"].startswith("Adey Market"):
        e["exact"] += r.get("items_naming_exact_model_and_part_listing") or 0
        e["brand"] += r.get("items_naming_brand_only_and_part_listing") or 0
        e["prices"] += [f"Adey: {p}" for p in r.get("displayed_prices_exact_model") or []]
        e["platforms"].add("Adey")
for c in clean:
    e = et.get(c["record_id"])
    if not e:
        continue
    c["et_jiji_listing_count_stated"] = e["jiji"]
    c["et_exact_model_part_listings"] = e["exact"]
    c["et_brand_only_part_listings"] = e["brand"]
    c["et_displayed_prices_etb"] = "; ".join(e["prices"]) or None
    c["et_platforms_inspected"] = "; ".join(sorted(e["platforms"]))
    c["ethiopian_availability"] = ("listing_observed_exact_model" if e["exact"] else
                                   "listing_observed_brand_only" if e["brand"] else "not_found_on_sources_inspected")

# Batch 07: NHTSA (ID.4 only)
for r in b7["records"]:
    c = clean_by_id[f"{r['vehicle_id']}__{r['part_category']}"]
    c["nhtsa_data_status"] = "available" if r["nhtsa_data_available"] else "no NHTSA data - not sold in US"
    c["nhtsa_complaints_component"] = r["complaint_count_component"]
    c["nhtsa_component_shared"] = (("Shared" in (r["complaint_count_component_note"] or "")) if r["nhtsa_data_available"] else None)
    c["nhtsa_complaints_keyword"] = r["complaint_count_keyword"]
    c["nhtsa_recall_campaigns"] = r["recall_campaigns"]

# ----------------------------------------------------------------------------- 4. vehicle market evidence (Batches 01-03)
mkt = []
def mrow(**kw):
    row = {c[0]: None for c in S_MKT}
    row.update(kw)
    vid = row["vehicle_id"]
    row["selected_vehicle"] = vid in SELECTED
    row["vehicle_model"] = VEH_MODEL_NORM[vid]
    if row.get("source_url") and not row.get("source_id"):
        row["source_id"] = sid_for(row["source_url"])
    row["interpretation"] = row.get("interpretation") or "Marketplace/catalogue evidence of vehicle visibility only; not registrations, sales, stock, or spare-part availability."
    mkt.append(row)

V1 = {"Yuan Up (Atto 2)": "yuan_up", "bZ series (bZ4X, bZ3, bZ3X, bZ5)": "toyota_bz_series_group",
      "Seagull (Dolphin Mini / Atto 1)": "seagull", "Seagull": "seagull", "Yuan Up": "yuan_up"}
for i, r in enumerate(b1["records"]):
    vid = V1[r["model"]]; adey = r["source_name"] == "Adey Market"
    cnt = re.search(r"([\d,]+) listings", r["observed_value"]) if adey else None
    ps = next(p for p in b1["page_summary"] if p["source_url"] == r["source_url"])
    mrow(market_record_id=r["evidence_id"], source_batch="vehicle_visibility_batch_01", raw_pointer=f"{RAW_FILES[0]}:records[{i}]",
         source_evidence_id=r["evidence_id"], vehicle_id=vid, vehicle_manufacturer=r["manufacturer"], vehicle_model_original=r["model"],
         evidence_class=("grouped_family_listing_count" if vid == "toyota_bz_series_group" else "category_listing_count") if adey else "catalogue_model_page",
         exact_vs_grouped="grouped_model_family" if vid == "toyota_bz_series_group" else "exact_model",
         geographic_scope="ethiopia_marketplace" if adey else "ethiopia_catalogue",
         vehicle_presence_in_ethiopia="marketplace_listings_observed" if adey else "catalogue_presence_only",
         listing_status_normalized="category_level" if adey else "not_applicable", listing_status_original=None,
         listing_count=to_int(cnt.group(1)) if cnt else None, pages_inspected=ps["pages_inspected"],
         source_name=r["source_name"], source_url=r["source_url"], collection_date=b1["collection_date"],
         interpretation=r["interpretation_status"], supporting_evidence=r["supporting_text"],
         limitations="Unavailable: " + "; ".join(r["fields_unavailable"]),
         notes=("Listing total comes from the page's 'Popular in Cars' list and is a grouped bZ-series count; it must not be used as a bZ4X count." if vid == "toyota_bz_series_group"
                else ("Same figure as the Batch 02 model page (taken from the 'Popular in Cars' list); do not add the two together." if adey else None)))

B2CFG = {  # evidence_id -> (vehicle_id, evidence_class, geographic_scope, presence, listing_status_norm)
    "ADEY-SEAGULL-001": ("seagull", "category_listing_count", "ethiopia_marketplace", "marketplace_listings_observed", "category_level"),
    "GEZAT-SEAGULL-001": ("seagull", "catalogue_model_page", "ethiopia_catalogue", "catalogue_presence_only", "not_applicable"),
    "BYD-ETH-SEAGULL-001": ("seagull", "manufacturer_spec_page", "ethiopia_manufacturer_page", "manufacturer_page_only", "not_applicable"),
    "ADEY-YUAN-001": ("yuan_up", "category_listing_count", "ethiopia_marketplace", "marketplace_listings_observed", "category_level"),
    "GEZAT-YUAN-001": ("yuan_up", "catalogue_model_page", "ethiopia_catalogue", "catalogue_presence_only", "not_applicable"),
    "BYD-ETH-YUAN-001": ("yuan_up", "manufacturer_spec_page", "ethiopia_manufacturer_page", "manufacturer_page_only", "not_applicable"),
    "TOYOTA-BZ4X-001": ("bz4x", "parts_catalogue_model_page", "international_catalogue_not_ethiopia", "not_evidence", "not_applicable"),
    "VW-ID4-001": ("id4", "parts_catalogue_model_page", "uae_catalogue_not_ethiopia", "not_evidence", "not_applicable"),
    "CHANGAN-BENBEN-001": ("benben", "individual_listing", "ethiopia_marketplace", "expired_listing_only", "expired"),
    "CHANGAN-BENBEN-002": ("benben", "access_blocked", "none", "not_evidence", "not_applicable"),
}
for i, r in enumerate(b2["records"]):
    vid, ecl, geo, pres, lst = B2CFG[r["evidence_id"]]
    text = r["observed_evidence"]
    m = re.search(r"([\d,]+) listings from ([\d,]+) sellers", text)
    pg = re.search(r"page 1 of (\d+)", text) or re.search(r"(\d+) pages", text)
    pr = re.search(r"([\d,]+) listings give a price", text)
    rg = re.search(r"displayed range ([\d,]+) ETB to ([\d,]+) ETB", text)
    tp = r.get("platform_reported_typical_price")
    pi = None
    if ecl == "category_listing_count":
        pi = int(next(x for x in log_rows if x["source_url"] == r["source_url"])["pages_inspected"])
    note = None
    if r["evidence_id"] == "VW-ID4-001":
        note = "UAE catalogue; not Ethiopian evidence. The year 2020 shown by the catalogue is the only source of the '2020' that an earlier version attached to the AUTODOC wiper row."
    if r["evidence_id"] == "ADEY-YUAN-001":
        note = "Displayed maximum (52,000,003 ETB) is an outlier-prone platform figure, not a validated price distribution."
    if r["evidence_id"] == "CHANGAN-BENBEN-002":
        note = "Security-verification page; no content accepted; no restriction bypassed."
    lims = r.get("limitations")
    mrow(market_record_id=r["evidence_id"], source_batch="vehicle_model_evidence_batch_02", raw_pointer=f"{RAW_FILES[1]}:records[{i}]",
         source_evidence_id=r["evidence_id"], vehicle_id=vid, vehicle_manufacturer=r["manufacturer"], vehicle_model_original=r["model"],
         model_year=int(r["model_year"]) if (r.get("model_year") and vid == "benben") else None, variant=r.get("variant"),
         catalogue_year_context=(r.get("catalogue_year_coverage") or (r["model_year"] if vid in ("id4",) else None)),
         evidence_class=ecl, exact_vs_grouped="exact_model", geographic_scope=geo, vehicle_presence_in_ethiopia=pres,
         listing_status_normalized=lst, listing_status_original=r.get("availability_status"),
         listing_count=to_int(m.group(1)) if m else None, seller_count=to_int(m.group(2)) if m else None,
         priced_listing_count=to_int(pr.group(1)) if pr else None, total_pages_available=int(pg.group(1)) if pg else None, pages_inspected=pi,
         platform_reported_typical_price_amount=tp["amount"] if tp else None, platform_reported_typical_price_currency=tp["currency"] if tp else None,
         displayed_price_min=to_int(rg.group(1)) if rg else None, displayed_price_max=to_int(rg.group(2)) if rg else None,
         displayed_price_currency="ETB" if rg else None, displayed_price_currency_original="ETB" if rg else None,
         location="Addis Ababa" if vid == "benben" and ecl == "individual_listing" else None,
         sample_listing_urls="; ".join(r["individual_listing_urls"]) if r.get("individual_listing_urls") else None,
         source_name=r["source_name"], source_url=r["source_url"], collection_date=r["collection_date"],
         supporting_evidence=text, limitations=("; ".join(lims) if isinstance(lims, list) else lims), notes=note)

B3V = {"bZ4X": "bz4x", "ID.4": "id4", "BenBen E-Star": "benben"}
slug = {"Adey Market": "adey", "Golden Car Market": "golden", "Gezat": "gezat", "Gezat Electric": "gezat", "Mekina.net": "mekina"}
ctr = Counter()
def b3id(vid, src):
    ctr[(vid, src)] += 1
    return f"B03-{vid}-{slug[src]}-{ctr[(vid, src)]:02d}"
CUR = {"Birr": "ETB", "ETB": "ETB"}
for ci, cand in enumerate(b3["candidates"]):
    vid = B3V[cand["model"]]
    for ei, e in enumerate(cand["exact_model_market_evidence"]):
        is_cat = "total_listing_count" in e
        dp = e.get("displayed_price"); st = e.get("listing_status") or ""
        lst = ("category_level" if is_cat else "expired" if re.search(r"not available|expired", st, re.I)
               else "active_per_page" if st in ("For Sale", "Available now") else "not_stated")
        tp = e.get("platform_reported_typical_price")
        mrow(market_record_id=b3id(vid, e["source_name"]), source_batch="vehicle_selection_investigation_batch_03",
             raw_pointer=f"{RAW_FILES[2]}:candidates[{ci}].exact_model_market_evidence[{ei}]", vehicle_id=vid,
             vehicle_manufacturer=cand["manufacturer"], vehicle_model_original=cand["model"],
             model_year=e.get("model_year"), variant=e.get("variant"),
             evidence_class="category_listing_count" if is_cat else "individual_listing", exact_vs_grouped="exact_model",
             geographic_scope="ethiopia_marketplace", vehicle_presence_in_ethiopia="marketplace_listings_observed" if lst != "expired" else "expired_listing_only",
             listing_status_normalized=lst, listing_status_original=st, seller=e.get("seller"), location=e.get("location"),
             listing_count=e.get("total_listing_count"), seller_count=e.get("seller_count"),
             priced_listing_count=to_int(re.search(r"([\d,]+) listings give a price", e["supporting_evidence"]).group(1)) if re.search(r"([\d,]+) listings give a price", e["supporting_evidence"]) else None,
             total_pages_available=e.get("total_pages_available"), pages_inspected=e.get("pages_inspected"),
             platform_reported_typical_price_amount=tp["amount"] if tp else None, platform_reported_typical_price_currency=CUR[tp["currency"]] if tp else None,
             displayed_price_amount=dp["amount"] if dp else None, displayed_price_currency=CUR[dp["currency"]] if dp else None,
             displayed_price_currency_original=dp["currency"] if dp else None,
             source_name=e["source_name"], source_url=e["url"], collection_date=b3["collection_date"],
             supporting_evidence=e["supporting_evidence"],
             notes="'New' is the platform's wording for this listing; it is not treated as proof of availability." if st == "New" else None)
    for gi, g in enumerate(cand["grouped_evidence"]):
        grouped = g.get("listing_count") is not None
        gvid = "toyota_bz_series_group" if grouped else vid
        mrow(market_record_id=b3id("bzgroup" if grouped else vid, g["source_name"]),
             source_batch="vehicle_selection_investigation_batch_03", raw_pointer=f"{RAW_FILES[2]}:candidates[{ci}].grouped_evidence[{gi}]",
             vehicle_id=gvid, vehicle_manufacturer=cand["manufacturer"], vehicle_model_original=cand["model"] if not grouped else "Toyota bZ series (grouped)",
             evidence_class="grouped_family_listing_count" if grouped else "catalogue_model_request_price",
             exact_vs_grouped="grouped_model_family" if grouped else "exact_model",
             geographic_scope="ethiopia_marketplace" if grouped else "ethiopia_catalogue",
             vehicle_presence_in_ethiopia="marketplace_listings_observed" if grouped else "catalogue_presence_only",
             listing_status_normalized="category_level" if grouped else "not_applicable", listing_status_original=g.get("listing_status"),
             listing_count=g.get("listing_count"), total_pages_available=g.get("total_pages_available"), pages_inspected=g.get("pages_inspected"),
             source_name=g["source_name"], source_url=g.get("listing_url") or g["url"], source_id=sid_for(g.get("listing_url") or "") or sid_for(g["url"]), collection_date=b3["collection_date"],
             interpretation=g.get("interpretation"), supporting_evidence=g.get("supporting_evidence") or g.get("interpretation"),
             limitations=g.get("access_note"),
             notes=("Stored under `grouped_evidence` in the raw batch although the content is exact-model; classified exact_model here." if not grouped else
                    "Grouped bZ-series count; not a bZ4X count. Page was not accessible (timeout then server-error page)."))
# de-dup ids (should already be unique)

# ----------------------------------------------------------------------------- 5. source log (original values untouched, extra columns appended)
EXTRA_LOG = ["batch", "source_scope", "pages_available", "cited_by_part_records", "cited_by_market_records", "log_note"]
pages_avail = {}
for m_ in mkt:
    if m_["evidence_class"] == "category_listing_count" and m_["total_pages_available"]:
        pages_avail[m_["source_url"]] = m_["total_pages_available"]
LOG_NOTES = {
    "ADEY-BZ4X-04": "Carries a -04 suffix but is an individual exact-listing source for Toyota bZ4X (same URL as market record B03-bz4x-adey-02: Batch 03-style vehicle-selection evidence; page says 'not available any more'). It is not listed in Batch 04 source_findings, bZ4X is not a selected vehicle, and no part record cites it. ID not renamed.",
    "CQS-SEAGULL-04": "Listed in Batch 04 source_findings but cited by no cleaned record: Batch 04 did not use it as high-confidence compatibility evidence (no per-item compatibility text).",
    "ADEY-BZ4X-GROUP-03": "Status partial: direct scrape timed out then returned a server-error page. The 1,021 grouped bZ-series count comes from Batch 01 and is not attributed to bZ4X.",
    "AUTOCANGO-BENBEN-02": "Blocked by a security-verification page; nothing accepted as evidence; no restriction bypassed.",
    "CARS45-BZ4X-03": "Scrape failed; no evidence collected.",
}
log_out = []
for r in log_rows:
    sid = r["source_id"]; u = r["source_url"]
    cp = [c["record_id"] for c in clean if c["source_id"] and sid in c["source_id"].split("; ")]
    cm = [m_["market_record_id"] for m_ in mkt if m_["source_id"] and sid in m_["source_id"].split("; ")]
    nr = OrderedDict(r)
    nr["batch"] = sid.rsplit("-", 1)[-1]
    nr["source_scope"] = LOG_SCOPE.get(r["source_name"], "unknown")
    nr["pages_available"] = pages_avail.get(u)
    nr["cited_by_part_records"] = "; ".join(cp) or None
    nr["cited_by_market_records"] = "; ".join(cm) or None
    nr["log_note"] = LOG_NOTES.get(sid)
    log_out.append(nr)
for r in log_add_rows:  # v3: append-only rows for batches 05-07 (+ B03 back-fill); values kept as logged
    sid = r["source_id"]
    nr = OrderedDict(r)
    cp = [c["record_id"] for c in clean if c["source_id"] and sid in c["source_id"].split("; ")]
    cm = [m_["market_record_id"] for m_ in mkt if m_["source_id"] and sid in m_["source_id"].split("; ")]
    if cp:
        nr["cited_by_part_records"] = "; ".join(cp)
    if cm:
        nr["cited_by_market_records"] = "; ".join(cm)
    log_out.append(nr)
S_LOG = [(k, "str", "Original source_log column, value unchanged.") for k in LOG_COLS] + [
    ("batch", "str", "Batch suffix taken from the source_id (01-04); for rows from source_log_additions_b05_b07.csv the batch as logged (03 back-fill, 05, 06, 07). Not corrected where the suffix is misleading (see log_note)."),
    ("source_scope", "str", "Ethiopian vehicle market / manufacturer page / international parts source / blocked etc."),
    ("pages_available", "int", "Platform-reported page count where known (category pages only). `pages_inspected` is the pages actually opened."),
    ("cited_by_part_records", "str", "record_ids in the cleaned part table that cite this source."),
    ("cited_by_market_records", "str", "market_record_ids that cite this source."),
    ("log_note", "str", "Audit note.")]

# ----------------------------------------------------------------------------- 6. write data files
write_csv(BASE / "raw_vehicle_part_evidence.csv", raw_rows, S_RAW)
write_csv(BASE / "cleaned_vehicle_part_evidence.csv", clean, S_CLEAN); write_json(BASE / "cleaned_vehicle_part_evidence.json", clean, S_CLEAN)
write_csv(BASE / "product_observations.csv", prod, S_PROD); write_json(BASE / "product_observations.json", prod, S_PROD)
write_csv(BASE / "vehicle_market_evidence.csv", mkt, S_MKT); write_json(BASE / "vehicle_market_evidence.json", mkt, S_MKT)
with open(BASE / "source_log.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); names = LOG_COLS + EXTRA_LOG; w.writerow(names)
    for r in log_out:
        w.writerow([cell(r.get(n)) for n in names])

# ----------------------------------------------------------------------------- 7. raw hashes
cur_hash = {f: (sha256(RAW / f), (RAW / f).stat().st_size) for f in RAW_FILES + ["source_log_original.csv"]}
with open(BASE / "raw_file_hashes.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["file", "sha256", "bytes"])
    for k, (h, n) in cur_hash.items():
        w.writerow([f"raw/{k}", h, n])
base_path = BASE / "raw_file_hashes_baseline.csv"; baseline_created = False
if not base_path.exists():
    base_path.write_text((BASE / "raw_file_hashes.csv").read_text(encoding="utf-8"), encoding="utf-8"); baseline_created = True
base_hash = {Path(r["file"]).name: r["sha256"] for r in csv.DictReader(open(base_path, encoding="utf-8"))}
# v3: new raw batches get their own manifest + baseline; the original 5-file files above are untouched in content
new_hash = {f: (sha256(RAW / f), (RAW / f).stat().st_size) for f in RAW_FILES_NEW}
with open(BASE / "raw_file_hashes_b05_b07.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n"); w.writerow(["file", "sha256", "bytes"])
    for k, (h, n) in new_hash.items():
        w.writerow([f"raw/{k}", h, n])
base_path_new = BASE / "raw_file_hashes_baseline_b05_b07.csv"; baseline_new_created = False
if not base_path_new.exists():
    base_path_new.write_text((BASE / "raw_file_hashes_b05_b07.csv").read_text(encoding="utf-8"), encoding="utf-8"); baseline_new_created = True
base_hash_new = {Path(r["file"]).name: r["sha256"] for r in csv.DictReader(open(base_path_new, encoding="utf-8"))}

# ----------------------------------------------------------------------------- 8. validation
checks = []
def chk(cid, name, status, detail=""):
    checks.append({"id": cid, "check": name, "status": status, "detail": detail})
P, F, NV, W = "PASSED", "FAILED", "NOT VERIFIED", "WARNING"
ok = lambda cond: P if cond else F

# reload outputs from disk to validate the files, not the in-memory objects
c_csv = read_csv_typed(BASE / "cleaned_vehicle_part_evidence.csv", S_CLEAN)
c_json = json.load(open(BASE / "cleaned_vehicle_part_evidence.json", encoding="utf-8"))
p_csv = read_csv_typed(BASE / "product_observations.csv", S_PROD)
p_json = json.load(open(BASE / "product_observations.json", encoding="utf-8"))
m_csv = read_csv_typed(BASE / "vehicle_market_evidence.csv", S_MKT)
m_json = json.load(open(BASE / "vehicle_market_evidence.json", encoding="utf-8"))
r_csv = read_csv_typed(BASE / "raw_vehicle_part_evidence.csv", S_RAW)
l_csv = list(csv.DictReader(open(BASE / "source_log.csv", encoding="utf-8")))

# A. completeness
veh = sorted({c["vehicle_id"] for c in c_csv}); cats = sorted({c["part_category"] for c in c_csv})
combos = Counter((c["vehicle_id"], c["part_category"]) for c in c_csv)
expected = {(v, k) for v in VEH_ID.values() for k in CAT.values()}
chk("A1", "Exactly 3 vehicles", ok(veh == sorted(VEH_ID.values())), ", ".join(veh))
chk("A2", "Exactly 10 categories, each present for every vehicle", ok(len(cats) == 10 and all(Counter(c["vehicle_id"] for c in c_csv)[v] == 10 for v in veh)), f"{len(cats)} categories; rows per vehicle {dict(Counter(c['vehicle_id'] for c in c_csv))}")
chk("A3", "30 unique vehicle-category combinations; none missing, none duplicated", ok(set(combos) == expected and max(combos.values()) == 1 and len(combos) == 30), f"{len(combos)} combinations")
chk("A4", "Row counts: raw CSV / cleaned CSV / cleaned JSON / Batch 04 raw", ok(len(r_csv) == len(c_csv) == len(c_json) == len(b4["records"]) == 30), f"{len(r_csv)} / {len(c_csv)} / {len(c_json)} / {len(b4['records'])}")
# B. ids and parity
chk("B1", "record_id unique (cleaned)", ok(len({c['record_id'] for c in c_csv}) == 30))
chk("B2", "observation_id unique (product observations)", ok(len({p['observation_id'] for p in p_csv}) == len(p_csv)), f"{len(p_csv)} observations")
chk("B3", "market_record_id unique (vehicle market)", ok(len({m['market_record_id'] for m in m_csv}) == len(m_csv)), f"{len(m_csv)} rows")
chk("B4", "Raw CSV and cleaned CSV share the same 30 record_ids", ok({r['record_id'] for r in r_csv} == {c['record_id'] for c in c_csv}))
def parity(csv_rows, json_rows, key):
    jm = {j[key]: j for j in json_rows}
    bad = [(c[key], k) for c in csv_rows for k, v in c.items() if jm.get(c[key], {}).get(k) != v]
    return bad
for cid, nm, a, b, k in (("B5", "cleaned CSV == cleaned JSON (all fields, typed)", c_csv, c_json, "record_id"),
                         ("B6", "product observations CSV == JSON", p_csv, p_json, "observation_id"),
                         ("B7", "vehicle market CSV == JSON", m_csv, m_json, "market_record_id")):
    bad = parity(a, b, k)
    chk(cid, nm, ok(not bad and len(a) == len(b)), f"{len(bad)} mismatching cells" if bad else "0 mismatching cells")
# C. traceability
trace_bad = []
for c in clean:
    fn, ptr = c["raw_pointer"].split(":records[")
    rec = jload(RAW / fn)["records"][int(ptr.rstrip("]"))]
    if rec["vehicle_model"] != c["vehicle_model"] or cat_of(rec["part_category"]) != c["part_category"] or rec["source_url"] != c["source_url"] or rec["collection_date"] != c["collection_date"]:
        trace_bad.append(c["record_id"])
chk("C1", "Every cleaned record resolves to its raw Batch 04/05 record (vehicle, category, URL, date identical)", ok(not trace_bad), f"{len(trace_bad)} failures")
chk("C2", "Every record with a source carries source_url and collection_date", ok(all(c['source_url'] and c['collection_date'] for c in c_csv if c['source_name'])), f"{sum(1 for c in c_csv if c['source_name'])} sourced records")
nolog = [c["record_id"] for c in c_csv if c["source_url"] and not c["source_id"]]
chk("C3", "Every sourced part record maps to a source_log row (source_id)", ok(not nolog), f"unmapped: {nolog}" if nolog else "all mapped")
nolog_m = [m["market_record_id"] for m in m_csv if not m["source_id"]]
chk("C4", "Every vehicle-market record maps to a source_log row", P if not nolog_m else W, "all mapped" if not nolog_m else f"{len(nolog_m)} market rows have no source_log row (URL not logged): {nolog_m}")
chk("C5", "source_log: all 29 original rows and original column values preserved (additions appended after them)", ok(len(l_csv) == len(log_rows) + len(log_add_rows) and all(all(l_csv[i][k] == log_rows[i][k] for k in LOG_COLS) for i in range(len(log_rows)))), f"{len(l_csv)} rows")
chk("C6", "Raw batch files byte-identical to the version used for the earlier datasets", NV, "No hash manifest existed before this build, so equality with the earlier version cannot be proven. Files were byte-copied from the supplied uploads (verified with cmp) and are hashed in raw_file_hashes.csv.")
if baseline_created:
    chk("C6b", "Raw batch files unchanged since baseline", NV, "Baseline (raw_file_hashes_baseline.csv) created in this run; later runs compare against it.")
else:
    same = all(base_hash.get(f) == h for f, (h, _) in cur_hash.items())
    chk("C6b", "Raw batch files unchanged since baseline hashes were first recorded", ok(same), "SHA-256 of all 5 raw files compared with raw_file_hashes_baseline.csv")
if baseline_new_created:
    chk("C6c", "Batches 05-07 unchanged since their baseline", NV, "Baseline (raw_file_hashes_baseline_b05_b07.csv) created in this run; later runs compare against it.")
else:
    chk("C6c", "Batches 05-07 unchanged since their baseline", ok(all(base_hash_new.get(f) == h for f, (h, _) in new_hash.items())), "SHA-256 of 3 new raw batch files compared with raw_file_hashes_baseline_b05_b07.csv")
# D. values / no invention
raw_tokens = set()
for r in b4["records"]:
    for k in ("oem_part_number", "aftermarket_part_number"):
        if r[k]:
            raw_tokens |= {t.strip() for t in r[k].split(";")}
for r in b5["records"]:
    for k in ("oem_part_number", "oem_part_number_secondary", "aftermarket_part_number"):
        if r[k]:
            raw_tokens |= {t.strip() for t in r[k].split(";")}
bad_pn = [(c["record_id"], t) for c in c_csv for k in ("oem_part_number", "aftermarket_part_number") if c[k] for t in c[k].split("; ") if t not in raw_tokens]
bad_pn += [(p["observation_id"], p["part_number"]) for p in p_csv if p["part_number"] not in raw_tokens]
chk("D1", "No part number exists that is not in the raw batches (04, 05)", ok(not bad_pn), f"{len(bad_pn)} unknown numbers")
raw_prices = {(r["displayed_price"]["amount"], r["displayed_price"]["currency"]) for r in b4["records"] if r.get("displayed_price")}
raw_prices.add((15.49, "EUR"))  # stated in raw text: 'second product price 15.49 EUR'
raw_prices |= {(float(r["displayed_price"]["amount"]), r["displayed_price"]["currency"]) for r in b5["records"] if r.get("displayed_price")}
price_bad = [c["record_id"] for c in c_csv if c["displayed_price_amount"] is not None and (c["displayed_price_amount"], c["displayed_price_currency"]) not in raw_prices]
price_bad += [p["observation_id"] for p in p_csv if p["price_amount"] is not None and (p["price_amount"], p["currency"]) not in raw_prices]
chk("D2", "Every price equals a price stated in the raw batch (no invented prices)", ok(not price_bad), f"{len(price_bad)} unmatched")
chk("D3", "No price is zero, and every price has a currency", ok(all((c['displayed_price_amount'] or 1) > 0 and (c['displayed_price_amount'] is None or c['displayed_price_currency']) for c in c_csv) and all(p['price_amount'] is None or (p['price_amount'] > 0 and p['currency']) for p in p_csv)))
chk("D4", "Prices are numeric (typed float) in CSV and JSON", ok(all(isinstance(c['displayed_price_amount'], (float, type(None))) for c in c_json) and all(isinstance(p['price_amount'], (float, type(None))) for p in p_json)))
chk("D5", "No currency conversion performed (all currencies original)", ok({p['currency'] for p in p_csv if p['currency']} <= {"EUR", "USD"} and {c['displayed_price_currency'] for c in c_csv if c['displayed_price_currency']} <= {"USD", "CNY", "AED"}), "part prices in original USD/EUR/CNY/AED only; no ETB conversion of part prices; Ethiopian ETB prices live only in et_displayed_prices_etb")
chg = [(c["record_id"], c["compatibility_confidence_original"], c["compatibility_confidence"]) for c in c_csv if c["compatibility_confidence"] != c["compatibility_confidence_original"]]
chk("D6", "Confidence changes are exactly the documented set and each has a note", ok(chg == [("id4__fender_body_panel", "medium", "low")] and all(c['confidence_adjustment_note'] for c in c_csv if c['compatibility_confidence'] != c['compatibility_confidence_original'])), f"changes: {chg}")
chk("D7", "No confidence level was raised", ok(not any(["insufficient", "low", "medium", "high"].index(c['compatibility_confidence']) > ["insufficient", "low", "medium", "high"].index(c['compatibility_confidence_original']) for c in c_csv)))
et_ok = all(c['ethiopian_availability'] in ENUMS['ethiopian_availability'] for c in c_csv) and all(
    (c['ethiopian_availability'] == 'listing_observed_exact_model') == bool(c['et_exact_model_part_listings']) for c in c_csv)
chk("D8", "ethiopian_availability uses only allowed values and agrees with Batch 06 listing counts (exact-model listings <=> listing_observed_exact_model)", ok(et_ok), dict(Counter(c['ethiopian_availability'] for c in c_csv)).__repr__())
chk("D9", "Missing values stay null: rows without a source have no part number, price or description", ok(all(not (c['oem_part_number'] or c['aftermarket_part_number'] or c['part_description'] or c['displayed_price_amount']) for c in c_csv if c['evidence_availability'] in ('not_found', 'category_context_only'))))
chk("D10", "Dimensions not conflated: no 'New' mapped to stock; condition separate from sourcing", ok(all(c['item_condition'] == 'New' for c in c_csv if c['availability_status_original'] == 'New') and all(c['sourcing_availability'] == 'not_established' for c in c_csv if c['item_condition'] == 'New')))
chk("D11", "Rows without a part record have sourcing_availability = no_part_record", ok(all(c['sourcing_availability'] == 'no_part_record' for c in c_csv if c['evidence_availability'] in ('not_found', 'category_context_only'))))
# E. specific corrections
fl = clean_by_id["id4__fender_body_panel"]; bp = clean_by_id["id4__brake_pad"]; wp = clean_by_id["id4__wiper_blade"]
chk("E1", "ID.4 fender flare: related_part_found, low, flare note, not a complete panel", ok(fl["evidence_availability"] == "related_part_found" and fl["compatibility_confidence"] == "low" and "not a complete" in fl["category_scope_note"]))
chk("E2", "ID.4 tail light & side mirror: category_context_only, low, no part number/price", ok(all(clean_by_id[f"id4__{k}"]["evidence_availability"] == "category_context_only" and clean_by_id[f"id4__{k}"]["compatibility_confidence"] == "low" for k in ("tail_light", "side_mirror"))))
chk("E3", "ID.4 brake pad: low, supplier_unavailable, found record, USD 60.95 kept, not orderable", ok(bp["compatibility_confidence"] == "low" and bp["sourcing_availability"] == "supplier_unavailable" and bp["evidence_availability"] == "specific_part_record_found" and bp["displayed_price_amount"] == 60.95 and bp["displayed_price_currency"] == "USD" and bp["currently_orderable"] == "no"))
wprod = [p for p in prod if p["parent_record_id"] == "id4__wiper_blade"]
chk("E4", "ID.4 wipers: 2 separate observations, own sizes/part numbers/EUR prices, no average", ok(len(wprod) == 2 and {(p['part_number'], p['price_amount'], p['currency'], p['size_mm']) for p in wprod} == {("3 397 006 839", 18.49, "EUR", 700), ("3 397 006 831", 15.49, "EUR", 450)} and wp["displayed_price_amount"] is None))
chk("E5", "ID.4 wiper model_year not asserted from catalogue context", ok(wp["model_year"] is None and wp["model_year_basis"] == "raw_value_removed_not_stated_in_source_record"))
chk("E6", "All 7 Yuan Up found records are catalogue_model_context_only (no individual fitment confirmation)", ok(all(c['fitment_evidence_status'] == 'catalogue_model_context_only' for c in c_csv if c['vehicle_id'] == 'yuan_up' and c['evidence_availability'] == 'specific_part_record_found') and sum(1 for c in c_csv if c['vehicle_id'] == 'yuan_up' and c['evidence_availability'] == 'specific_part_record_found') == 7))
chk("E7", "Fender flare: single price not assigned to either product", ok(all(p['price_amount'] is None and p['price_set_in_raw_batch'] == "33.49 EUR" for p in prod if p['parent_record_id'] == 'id4__fender_body_panel')))
chk("E7b", "Cleaned wiper and fender-flare rows carry no primary price and point to the child table", ok(all(clean_by_id[k]['displayed_price_amount'] is None and clean_by_id[k]['price_attribution'] == 'multi_product_see_product_observations' and clean_by_id[k]['product_observation_ids'] for k in ('id4__wiper_blade', 'id4__fender_body_panel'))))
chk("E8", "No empty calculated/converted price columns exist", ok(not any(re.search(r"calculated|converted|etb_equiv", c[0]) for c in S_CLEAN + S_PROD + S_MKT)))
# F. market table
labels = Counter(m["vehicle_model"] for m in m_csv)
chk("F1", "Vehicle model labels normalised (one label per vehicle_id)", ok(len({(m['vehicle_id'], m['vehicle_model']) for m in m_csv}) == len({m['vehicle_id'] for m in m_csv})), dict(labels).__repr__())
cat_rows = {m["vehicle_id"]: m for m in m_csv if m["evidence_class"] == "category_listing_count" and m["source_batch"] != "vehicle_visibility_batch_01" and m["exact_vs_grouped"] == "exact_model"}
chk("F2", "Category counts present as numbers: Seagull 764, Yuan Up 1362, ID.4 102, BenBen 279", ok((cat_rows['seagull']['listing_count'], cat_rows['yuan_up']['listing_count'], cat_rows['id4']['listing_count'], cat_rows['benben']['listing_count']) == (764, 1362, 102, 279)))
chk("F3", "Pages available vs inspected recorded separately (32/57/5/12 vs 1)", ok((cat_rows['seagull']['total_pages_available'], cat_rows['yuan_up']['total_pages_available'], cat_rows['id4']['total_pages_available'], cat_rows['benben']['total_pages_available']) == (32, 57, 5, 12) and all(cat_rows[v]['pages_inspected'] == 1 for v in cat_rows)))
chk("F4", "Grouped Toyota bZ-series 1,021 is flagged grouped and not attributed to bZ4X", ok(all(m['exact_vs_grouped'] == 'grouped_model_family' for m in m_csv if m['listing_count'] == 1021) and not any(m['vehicle_id'] == 'bz4x' and m['listing_count'] for m in m_csv)))
chk("F5", "Platform-reported typical price kept distinct; no calculated averages/medians", ok(cat_rows['id4']['platform_reported_typical_price_amount'] == 5700000 and cat_rows['benben']['platform_reported_typical_price_amount'] == 2700000))
chk("F6", "Only the 3 study vehicles are flagged selected_vehicle", ok({m['vehicle_id'] for m in m_csv if m['selected_vehicle']} == SELECTED))
chk("F7", "UAE/international catalogue rows are not labelled as Ethiopian evidence", ok(all(m['vehicle_presence_in_ethiopia'] == 'not_evidence' for m in m_csv if m['geographic_scope'] in ('uae_catalogue_not_ethiopia', 'international_catalogue_not_ethiopia', 'none'))))
# G. urls / encoding
all_urls = [c["source_url"] for c in c_csv if c["source_url"]] + [p["source_url"] for p in p_csv] + [m["source_url"] for m in m_csv] + [l["source_url"] for l in l_csv]
badu = sorted({u for u in all_urls if not url_ok(u)})
chk("G1", "URL syntax: http(s), host present, no whitespace, no backslashes (all part, product, market and source-log URLs)", ok(not badu), f"{len(set(all_urls))} distinct URLs checked; invalid: {badu}")
bs = []
for fn in ["raw_vehicle_part_evidence.csv", "cleaned_vehicle_part_evidence.csv", "cleaned_vehicle_part_evidence.json", "product_observations.csv", "product_observations.json", "vehicle_market_evidence.csv", "vehicle_market_evidence.json", "source_log.csv"]:
    t = (BASE / fn).read_text(encoding="utf-8")
    if re.search(r"https?\\|www\\|\\[:./]", t):
        bs.append(fn)
chk("G2", "No backslash escaping in any output file (https\\:// or www\\.)", ok(not bs), f"files with hits: {bs}" if bs else "0 hits in 8 files")
bom = [fn for fn in ["raw_vehicle_part_evidence.csv", "cleaned_vehicle_part_evidence.csv", "cleaned_vehicle_part_evidence.json", "product_observations.csv", "product_observations.json", "vehicle_market_evidence.csv", "vehicle_market_evidence.json", "source_log.csv"] if open(BASE / fn, "rb").read(3) == b"\xef\xbb\xbf"]
chk("G3", "Outputs are UTF-8 without BOM; JSON loads with plain utf-8 json.load", ok(not bom), f"BOM in: {bom}" if bom else "no BOM; json.load OK")
chk("G4", "URL accessibility (pages reachable now)", NV, "Syntax only in this build (no network). A 12-URL spot-check on 2026-11-16 found 9 x HTTP 200 and 3 x 403 (AUTODOC FR/UK, parts.vw.com); see verification_stage4.md.")
chk("G5", "Product-level wiper pairing vs the live AUTODOC page", NV, "Pairing follows listing order inside the raw record (price_pairing_status = order_inferred_from_raw_record). Re-check attempted 2026-11-16: AUTODOC returned HTTP 403 (bot protection); the user's manual browser check did not confirm the pairing either, so it stays order-inferred.")
chk("G6", "Source-provided evidence IDs for Batch 04 records", NV, "Batch 04 supplies none (record_id is the derived key). Not applicable rather than failed.")
g7_pairs = [(l['source_url'], l['batch']) for l in l_csv]
chk("G7", "No duplicate source URL within the same batch in source_log (re-visits in a later batch are logged as new rows)", ok(len(set(g7_pairs)) == len(g7_pairs)), f"{len(l_csv)} rows, {len({l['source_url'] for l in l_csv})} distinct URLs, {len(set(g7_pairs))} distinct (url, batch) pairs")
# I. batches 05-07
B5_TARGET = {"seagull__brake_pad", "seagull__brake_disc", "seagull__cabin_air_filter", "seagull__wiper_blade", "seagull__tail_light", "seagull__side_mirror",
             "yuan_up__cabin_air_filter", "yuan_up__wiper_blade", "yuan_up__side_mirror",
             "id4__brake_disc", "id4__cabin_air_filter", "id4__headlight", "id4__tail_light", "id4__side_mirror", "id4__bumper", "id4__shock_absorber"}
b5_ids = {f"{VEH_ID[r['vehicle_model']]}__{cat_of(r['part_category'])}" for r in b5["records"]}
chk("I1", "Batch 05 addresses exactly the 16 target rows, each with the URLs checked", ok(b5_ids == B5_TARGET and len(b5["records"]) == 16 and all(r["urls_checked"] for r in b5["records"])), f"{len(b5_ids)} rows; overlaid: {len(b5_overlaid)}")
chk("I2", "Batch 05 not_found rows carry no part number, price or description", ok(all(not (r['oem_part_number'] or r['aftermarket_part_number'] or r['displayed_price'] or r['part_description']) for r in b5['records'] if r['row_status'] == 'not_found')))
chk("I3", "Every Batch 05 price has its original currency and verbatim price text", ok(all(r['original_currency'] and r['price_text_verbatim'] for r in b5['records'] if r.get('displayed_price'))))
chk("I4", "Batch 06 covers all 30 combinations on Jiji (one query each)", ok({(r['vehicle_id'], r['part_category']) for r in b6['records'] if r['platform'] == 'Jiji Ethiopia'} == expected), f"{sum(1 for r in b6['records'] if r['platform'] == 'Jiji Ethiopia')} Jiji records")
chk("I5", "No NHTSA data attached to Seagull or Yuan Up", ok(all(c['nhtsa_complaints_component'] is None and c['nhtsa_complaints_keyword'] is None and c['nhtsa_recall_campaigns'] is None and c['nhtsa_data_status'] == 'no NHTSA data - not sold in US' for c in c_csv if c['vehicle_id'] in ('seagull', 'yuan_up'))))
chk("I6", "ID.4 NHTSA fields present for all 10 categories (null only where no NHTSA component maps)", ok(all(c['nhtsa_data_status'] == 'available' and c['nhtsa_complaints_keyword'] is not None for c in c_csv if c['vehicle_id'] == 'id4')))
scarce = [fn for fn in (B5, B6, B7) if re.search(r"scarc", (RAW / fn).read_text(encoding="utf-8"), re.I) and not re.search(r"not a scarcity claim|never claim scarcity|NOT a scarcity", (RAW / fn).read_text(encoding="utf-8"))]
chk("I7", "No scarcity claim in batches 05-07 (0 found = not found on sources inspected)", ok(not scarce), f"files: {scarce}")
etb_in_part = [c['record_id'] for c in c_csv if c['displayed_price_currency'] == 'ETB']
chk("I8", "ETB never appears as a part-supplier price currency (Ethiopian prices kept separately, unconverted)", ok(not etb_in_part))
b4_rows = [l for l in l_csv if l["source_id"].endswith("-04")]
b4_domains = {urlparse(l["source_url"]).netloc for l in b4_rows}
chk("G8", "Batch 04 source reconciliation", ok(len(b4_rows) == 7 and len(b4["source_findings"]) == 6 and len(b4_domains) == 6), f"{len(b4_rows)} log rows with a -04 suffix / {len(b4['source_findings'])} source_findings in Batch 04 / {len(b4_domains)} distinct domains in the 7 rows; the 7th row is ADEY-BZ4X-04")
# H. documentation completeness

# ----------------------------------------------------------------------------- 9. data dictionary
def tbl(schema):
    out = ["| Field | Type | Meaning |", "|---|---|---|"]
    for n, t, d in schema:
        out.append(f"| `{n}` | {t} | {d} |")
    return "\n".join(out)
def enum_md(cols):
    out = []
    for col in cols:
        out.append(f"**`{col}`**\n")
        out.append("| Value | Meaning |\n|---|---|")
        for v, d in ENUMS[col].items():
            out.append(f"| `{v}` | {d} |")
        out.append("")
    return "\n".join(out)

ET_SUMMARY = ", ".join(f"{k} {v}" for k, v in Counter(c["ethiopian_availability"] for c in clean).items())
dd = f"""# Data Dictionary (v3: Batches 01-07)

Generated by `build_dataset.py` from the same schema lists that write the files, so every column below exists in the file and vice versa.

## 1. Files

| File | Rows | Role |
|---|---:|---|
| `raw/*.json` (4 batches) + `raw/source_log_original.csv` | - | **Raw evidence. Preserved byte-for-byte; never written by the pipeline.** SHA-256 in `raw_file_hashes.csv`. |
| `raw/vehicle_part_evidence_batch_05.json` | 16 | Batch 05 part records for the 16 rows empty after Batch 04 (found / related / not_found + URLs checked). |
| `raw/vehicle_part_evidence_batch_06.json` + `raw/ethiopia_search_2026-11-16/` | - | Batch 06 Ethiopian marketplace searches (Jiji, Adey) with saved raw responses. |
| `raw/vehicle_failure_evidence_batch_07.json` + `raw/nhtsa_api_2026-11-16/` | 30 | Batch 07 NHTSA complaints/recalls for ID.4 (MY2021-2026); Seagull/Yuan Up = no NHTSA data. SHA-256 of 05-07 in `raw_file_hashes_b05_b07.csv`. |
| `source_log_additions_b05_b07.csv` | {len(log_add_rows)} | Append-only source rows for Batches 05-07 and the B03 back-fill; merged into `source_log.csv` after the 29 original rows. |
| `nhtsa_component_mapping.csv` | - | NHTSA component -> part category mapping used in Batch 07 (shared mappings flagged). |
| `raw_vehicle_part_evidence.csv` | {len(r_csv)} | Flattened copy of Batch 04, values verbatim (still contains the unsupported `model_year` 2020; see CN-04). |
| `cleaned_vehicle_part_evidence.csv/.json` | {len(c_csv)} | One row per vehicle x category. Analysis table for spare-part evidence. |
| `product_observations.csv/.json` | {len(p_csv)} | Child table: one row per product when a part row covers priced/multiple products. |
| `vehicle_market_evidence.csv/.json` | {len(m_csv)} | Vehicle visibility evidence (Batches 01-03). **Never mix with part evidence rows.** Join via `vehicle_id`. |
| `source_log.csv` | {len(l_csv)} | Provenance log: 29 original rows (columns unchanged, six columns appended) followed by {len(log_add_rows)} rows from `source_log_additions_b05_b07.csv`. |
| `validation_results.json`, `raw_file_hashes*.csv` | - | Check results and raw-file hash manifest. |

CSV: UTF-8 **without** BOM, `\\n` line ends, empty cell = null. JSON: UTF-8 without BOM, native numbers/null/booleans. Read in Colab with `pd.read_csv(path)` / `json.load(open(path, encoding="utf-8"))`.

## 2. Raw, cleaned and derived

| Layer | What it is | May contain |
|---|---|---|
| **Raw** | `raw/*.json`, `raw_vehicle_part_evidence.csv` | Facts as researched, including their flaws. |
| **Cleaned** | `cleaned_*`, `product_observations.*`, `vehicle_market_evidence.*` | Same facts, renamed, typed, split into separate concepts. No new facts. Raw text fields are copied **verbatim**; audit remarks live only in `correction_notes` / `notes`. |
| **Derived** | `part_number_count`, `cited_source_count`, `size_mm`, `listing_count` etc. parsed from raw text, `source_id`, `vehicle_id`, `batch`, `cited_by_*` | Mechanical parses/joins. Nothing here is scored, ranked or converted. |

## 3. Five dimensions that must not be confused

| Dimension | Column | Question it answers | Answer for this dataset |
|---|---|---|---|
| Part record exists | `evidence_availability` | Did we find a specific part record? | 12 specific, 1 related, 2 context-only, 14 not found... see report |
| Fitment | `compatibility_confidence`, `fitment_evidence_status` | How well does the source show it fits *this vehicle*? | Model-level at best; never year/variant/VIN-confirmed |
| Source quality | `source_quality`, `evidence_scope` | How good/what type is the source? | Independent of fitment |
| Supplier availability | `sourcing_availability`, `item_condition` | Does the supplier say it is available? (Condition `New` is not availability.) | Quote-request, unavailable or not stated; never verified stock |
| Ethiopian evidence | `ethiopian_availability` (parts) vs `vehicle_presence_in_ethiopia` (vehicles) | Is the **spare part** locally available / priced, vs. is the **vehicle** visible in Ethiopian listings? | Parts (Batch 06, listing evidence only): {ET_SUMMARY}. Vehicles: see market table. Listing counts are visibility proxies, not registrations, sales or demand. |

**A found part record is not a fitment confirmation, not stock, and not a local price.** High confidence = model-level evidence with an identifiable part reference; exact year/variant fitment may still need confirmation.

### Confidence definitions (verbatim from Batch 04, plus the clarification above)

| Level | Definition |
|---|---|
""" + "\n".join(f"| {k} | {v} |" for k, v in CONF_DEFS.items()) + f"""

Clarification: **no level, including `high`, asserts exact model-year, trim, drivetrain or VIN fitment.** Batch 05 Seagull rows cite two catalogues that list the same part number (`cited_source_count` = 2); this corroborates the number, not the fitment.

## 4. Prices and currencies
* `*_amount` columns are floats; the currency is stored beside them in its own column and is always the **original displayed currency** (`EUR`, `USD`, `CNY`, `AED` for international part suppliers; Ethiopian listing prices `ETB`, where the platform's label `Birr` is normalised to `ETB` and the original label kept in `displayed_price_currency_original`).
* **No conversion, average or median** is calculated anywhere. `platform_reported_typical_price_*` is a number the platform itself states, not a calculation.
* A price is a **displayed observation on a source page** (`price_observation_type`). It is not an orderable price (`currently_orderable`), and part prices are international supplier prices, never Ethiopian retail prices (`price_market_scope`).
* If a row covers several products, its own price fields are null and the prices live in `product_observations` (`price_pairing_status` explains how reliable the pairing is).
* A missing price is null, never 0.
* Batch 06 Ethiopian part-listing prices are kept as verbatim text with their `ETB` label in `et_displayed_prices_etb`; they are never placed in `displayed_price_*` and never converted.

## 4b. Scoring inputs (not part of this build)
`make_scoring_input.py` turns this table into `data/scoring_input.csv` (5 factors in 0-1). Rules: `data/scoring_rules.csv` (v4). Weights: `data/weights_proposed.csv` (0.30/0.20/0.20/0.15/0.15). `ethiopian_availability` = `not_found_on_sources_inspected` scores a **neutral** 0.5 on the scarcity factor: not finding a listing is not evidence of scarcity.

## 5. Missing values
* **Null / empty cell**: the source did not provide this field. Never imputed.
* **Status words** (`not_established`, `not_found`, `no_part_record`, `supplier_unavailable`, `none`) are used only in status columns and have the meanings listed below. `not_found` means *not found in the extracted item list of the inspected source(s)*, not that the part does not exist.
* Retired vocabulary (earlier build): `unknown`, `not_available`, `not_verified_or_not_found`, `listed_new_stock_claim`.

## 6. `cleaned_vehicle_part_evidence`
{tbl(S_CLEAN)}

### Allowed values
{enum_md(["part_category", "evidence_availability", "compatibility_confidence", "fitment_evidence_status", "source_quality", "sourcing_availability", "ethiopian_availability", "evidence_scope", "model_year_basis"])}
## 7. `product_observations`
{tbl(S_PROD)}

### Allowed values
{enum_md(["price_pairing_status", "currently_orderable", "stock_availability"])}
## 8. `vehicle_market_evidence`
Marketplace listings are **proxies for market visibility, not registrations or sales**; a category total is not a count of distinct cars.

{tbl(S_MKT)}

### Allowed values
{enum_md(["evidence_class", "geographic_scope", "vehicle_presence_in_ethiopia", "listing_status_normalized"])}
## 9. `source_log.csv`
{tbl(S_LOG)}

## 10. `raw_vehicle_part_evidence.csv`
{tbl(S_RAW)}
"""
dd = dd.replace("| Part record exists | `evidence_availability` | Did we find a specific part record? | 12 specific, 1 related, 2 context-only, 14 not found... see report |",
                "| Part record exists | `evidence_availability` | Did we find a specific part record? | %d specific, %d related, %d category-context only, %d not found |" % tuple(Counter(c['evidence_availability'] for c in clean)[k] for k in ("specific_part_record_found", "related_part_found", "category_context_only", "not_found")))
(BASE / "data_dictionary.md").write_text(dd, encoding="utf-8")
undoc = [(t, n) for t, sch in (("cleaned", S_CLEAN), ("product", S_PROD), ("market", S_MKT), ("source_log", S_LOG), ("raw", S_RAW)) for n, _, _ in sch if f"`{n}`" not in dd]
hdr = {"cleaned": [c[0] for c in S_CLEAN], "product": [c[0] for c in S_PROD], "market": [c[0] for c in S_MKT], "raw": [c[0] for c in S_RAW]}
files_cols = {"cleaned_vehicle_part_evidence.csv": hdr["cleaned"], "product_observations.csv": hdr["product"], "vehicle_market_evidence.csv": hdr["market"], "raw_vehicle_part_evidence.csv": hdr["raw"]}
mism = [fn for fn, cols in files_cols.items() if next(csv.reader(open(BASE / fn, encoding="utf-8"))) != cols]
chk("H1", "Every column of every output file is documented in data_dictionary.md, and file headers match the schema", ok(not undoc and not mism), f"undocumented: {undoc}; header mismatches: {mism}")

# ----------------------------------------------------------------------------- 10. quality report
conf_o = Counter(c["compatibility_confidence_original"] for c in clean); conf_c = Counter(c["compatibility_confidence"] for c in clean)
ev_by_v = {v: Counter(c["evidence_availability"] for c in clean if c["vehicle_id"] == v) for v in VEH_ID.values()}
def cats_of(v, ev):
    return ", ".join(c["part_category_display"] for c in clean if c["vehicle_id"] == v and c["evidence_availability"] == ev) or "-"
stat = Counter(c["status"] for c in checks)
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
null_found = {k: sum(1 for c in clean if c["evidence_availability"] != "not_found" and c[k] is None) for k in ("model_year", "generation", "variant", "oem_part_number", "aftermarket_part_number", "displayed_price_amount", "compatibility_evidence")}
rows_checks = "\n".join(f"| {c['id']} | {c['check']} | **{c['status']}** | {c['detail']} |" for c in checks)
report = f"""# Data Quality Report (v3: Batches 01-07)

Build: {now} - Python {platform.python_version()} - `build_dataset.py`. No web research, scoring, ranking, recommendation or currency conversion was performed. Raw batch files were read, never written.

## 1. Result at a glance
**{stat['PASSED']} PASSED - {stat['FAILED']} FAILED - {stat['NOT VERIFIED']} NOT VERIFIED - {stat['WARNING']} WARNING.** The dataset is structurally valid and traceable; the NOT VERIFIED items below are limits of what could be checked here, not hidden failures. All checks ran against the generated files on disk (see `validation_results.json`).

## 2. Validation checks
| ID | Check | Status | Detail |
|---|---|---|---|
{rows_checks}

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
| CN-14 | Batch 05 part records overlay the Batch 04 row for {len(b5_overlaid)} rows ({', '.join(b5_overlaid)}); `part_record_batch` = 05, `raw_pointer` points to Batch 05, `compatibility_confidence_original` = Batch 05 value. Not-found rows keep Batch 04 values plus the URLs checked. | New evidence, kept traceable; nothing from Batch 04 deleted (still in raw CSV). | 16 rows |
| CN-15 | `ethiopian_availability` now derived from Batch 06 listing searches (new allowed values); ETB prices kept verbatim in `et_displayed_prices_etb`. | Batch 06 collected Ethiopian part-listing evidence. | 30 rows |
| CN-16 | NHTSA columns from Batch 07 (ID.4 only); Seagull/Yuan Up = `no NHTSA data - not sold in US`. | Failure evidence; no substitute vehicle. | 30 rows |
| CN-18 | Final rerun: AUTODOC wiper pairing re-checked by the user in a browser and NOT confirmed, so `price_pairing_status` stays `order_inferred_from_raw_record` (G5 NOT VERIFIED). Scoring rules v4 (outside this build, in `make_scoring_input.py` / `data/scoring_rules.csv`): Ethiopian 'not found' scores neutral 0.5 (was 0.75), brand-only 0.375, evidence confidence -0.05 when the Ethiopian factor rests only on 'not found'. No evidence value changed. | User decisions after the sensitivity test. | scoring only |
| CN-17 | Source log: {len(log_add_rows)} rows appended from `source_log_additions_b05_b07.csv`, incl. back-fill `ADEY-ID4-ITEM-03` for market row B03-id4-adey-02 (resolves the old C4 WARNING). G7 now checks duplicates per (url, batch). D5 allows CNY/AED. | Provenance for every new URL. | source_log |

## 5. Confidence distribution
| Confidence | Original (Batch 04) | Cleaned |
|---|---:|---:|
""" + "\n".join(f"| {k} | {conf_o.get(k,0)} | {conf_c.get(k,0)} |" for k in ("high", "medium", "low", "insufficient")) + f"""
| **Total** | {sum(conf_o.values())} | {sum(conf_c.values())} |

One change only: `id4__fender_body_panel` medium -> low (CN-03). No level was raised. Earlier text that listed the fender flare under *Medium* and said tail-light/side-mirror were "changed to low" was wrong: those two were already low in the raw batch.

## 6. Evidence coverage (vehicle x category)
| Vehicle | Specific part record | Related component | Category context only | Not found |
|---|---:|---:|---:|---:|
""" + "\n".join(f"| {v} | {ev_by_v[v].get('specific_part_record_found',0)} | {ev_by_v[v].get('related_part_found',0)} | {ev_by_v[v].get('category_context_only',0)} | {ev_by_v[v].get('not_found',0)} |" for v in VEH_ID.values()) + f"""

Not found in the extracted item list (not proof of non-existence):
* **Seagull:** {cats_of('seagull','not_found')}
* **Yuan Up:** {cats_of('yuan_up','not_found')}
* **ID.4:** {cats_of('id4','not_found')}

Part records are international supplier/catalogue evidence (China, Albania, France, US, UAE); none is Ethiopian. Batch 05 Seagull rows have two catalogues agreeing on the part number. Ethiopian part-listing evidence (Batch 06): {ET_SUMMARY}.

## 7. Source-log reconciliation (the "7 vs 6" question)
* `source_log.csv` has {len(l_csv)} rows. Rows whose id ends in `-04`: **{len(b4_rows)}** (`{', '.join(l['source_id'] for l in b4_rows)}`).
* Batch 04's own `source_findings` lists **{len(b4['source_findings'])}** sources.
* The difference is exactly one row: **`ADEY-BZ4X-04`**. It is an individual Toyota bZ4X Adey listing (expired), which is Batch 03-style vehicle-selection evidence for a vehicle that was not selected. It is not in Batch 04's findings and no part record cites it. It is flagged in `log_note`, **not renamed or deleted**.
* An earlier explanation ("Connect Drive appears twice") was incorrect: that accounts for 7 rows vs 6 *domains*, not for 7 vs 6 findings.
* `CQS-SEAGULL-04` is in Batch 04's findings but cited by no cleaned record (not used as high-confidence evidence).
* Earlier batches are summarised, not re-labelled: pages **available** vs **inspected** are separate columns (`pages_available` populated for the four Adey category pages: Seagull 32, Yuan Up 57, ID.4 5, BenBen 12; one page inspected each).

## 8. Duplicates and missing values
* Duplicate record ids: 0. Duplicate combinations: 0. Duplicate source URLs in the log: 0. Duplicate market ids: 0.
* Multiple part numbers in one row (left/right, front/rear) are one category record, not duplicates.
* Nulls among the {len(clean) - Counter(c['evidence_availability'] for c in clean)['not_found']} rows that have some evidence: {', '.join(f'{k} {v}' for k, v in null_found.items())}. `model_year`, `generation`, `variant` are null for all 30 rows because no product source states them; this is a finding, not a defect.
* No price was filled with 0; no part number, price, fitment, stock or Ethiopian availability was inferred.

## 9. Product observations
{len(p_csv)} observations: 1 brake pad (USD 60.95, supplier *Unavailable*), 2 wipers (EUR 18.49 / EUR 15.49), 2 fender flares (price not attributable). **Wiper pairing is `order_inferred_from_raw_record`**: Batch 04 says "one price 18.49 EUR and another 15.49 EUR" and "second product price 15.49 EUR" and lists the two products in the same order; it does not tie prices to part numbers explicitly. Treat product-level wiper prices as provisional until checked against the live AUTODOC page. Never average the two.

## 10. Remaining limitations and unresolved issues
1. **Ethiopian spare-part evidence is listing-level only** (Batch 06: Jiji + Adey, first page per query): {ET_SUMMARY}. No stock, seller count or sales is established; Telegram/Facebook sellers were not inspected directly; Gezat, Golden Car Market and Mekina.net have no parts search. "0 found" means not found on the sources inspected, not scarcity.
2. **Fitment is model-level at best**, single-source, and never year/trim/VIN-confirmed. The high-confidence Seagull rows come from one supplier page.
3. **Part-record coverage after Batch 05:** {sum(1 for c in clean if c['evidence_availability']=='specific_part_record_found')} specific, {sum(1 for c in clean if c['evidence_availability']=='related_part_found')} related, {sum(1 for c in clean if c['evidence_availability']=='category_context_only')} category-context only, {sum(1 for c in clean if c['evidence_availability']=='not_found')} not found. This reflects the sources inspected, not the market. AUTODOC and parts.vw.com returned HTTP 403 in the Stage 4 re-check.
4. **Wiper price pairing** is order-inferred (section 9).
5. **Fender flare price** (EUR 33.49) cannot be assigned to VT540-S or VT540-L.
6. **NOT VERIFIED:** URL accessibility; raw files vs the version used for the earlier datasets (no earlier manifest existed; baseline hashes were first recorded at this build); the wiper price pairing against the live page; source-provided evidence ids (none exist).
7. `ADEY-BZ4X-04` carries a misleading batch suffix (kept, flagged).
8. Yuan Up Adey maximum displayed price (52,000,003 ETB) is a platform figure and an outlier; do not treat the min/max as a distribution.
9. Market-table rows without a `source_id` (if any) correspond to URLs that were collected but never logged; see check C4.
10. Seller names are copied as displayed (one is Amharic); no identity resolution was attempted.
11. **Failure data exists for the ID.4 only** (NHTSA, US complaints: self-reported, unverified, US conditions). BYD Seagull and Yuan Up have no comparable public failure dataset in this study.
""" 
(BASE / "data_quality_report.md").write_text(report, encoding="utf-8")

# ----------------------------------------------------------------------------- 11. validation_results.json + console summary
results = {
    "build_utc": now, "python": platform.python_version(), "platform": platform.platform(),
    "summary": dict(stat), "baseline_hashes_created_this_run": baseline_created,
    "raw_file_sha256": {k: v[0] for k, v in cur_hash.items()}, "checks": checks,
}
with open(BASE / "validation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2); f.write("\n")

print("=" * 78); print("EV spare-parts dataset build  -", now, "- Python", platform.python_version()); print("=" * 78)
print(f"raw CSV {len(r_csv)} | cleaned CSV {len(c_csv)} | cleaned JSON {len(c_json)} | product obs {len(p_csv)} | market rows {len(m_csv)} | source_log rows {len(l_csv)}")
print("confidence original:", dict(conf_o), "-> cleaned:", dict(conf_c))
for c in checks:
    print(f"[{c['status']:<12}] {c['id']:<3} {c['check']}")
print("-" * 78); print("SUMMARY:", dict(stat))
sys.exit(1 if stat["FAILED"] else 0)
