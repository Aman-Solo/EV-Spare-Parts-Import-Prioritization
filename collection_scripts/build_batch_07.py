"""Stage 3: builds raw/vehicle_failure_evidence_batch_07.json and nhtsa_component_mapping.csv
from the NHTSA API responses saved in raw/nhtsa_api_2026-11-16/ (fetched 2026-11-16 from
api.nhtsa.gov complaintsByVehicle / recallsByVehicle, make=VOLKSWAGEN model=ID.4, MY 2021-2026).

Counting rules
* A complaint is counted once (unique odiNumber), even if it appears in several model-year responses.
* primary count  = complaints whose NHTSA `components` field contains a mapped component.
  NHTSA components are coarse, so one component can map to several of our categories
  (e.g. SERVICE BRAKES -> brake_pad AND brake_disc). Those counts are marked shared=True and must
  not be summed across categories.
* keyword count = complaints whose free-text summary mentions a category keyword. Secondary,
  supporting signal only (a mention is not a confirmed failure of that part).
* Seagull and Yuan Up: not sold in the US, so no NHTSA data. No other vehicle is substituted."""
import csv, json, re, glob, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
RAWD = BASE / "raw" / "nhtsa_api_2026-11-16"
CATS = ["brake_pad", "brake_disc", "cabin_air_filter", "wiper_blade", "headlight", "tail_light",
        "side_mirror", "bumper", "fender_body_panel", "shock_absorber"]
# NHTSA top-level component -> our categories (complaints API returns top-level names only)
MAP = [
    ("SERVICE BRAKES", ["brake_pad", "brake_disc"], "Covers pads, rotors, calipers, ABS hydraulics etc.; cannot be split by component code."),
    ("EXTERIOR LIGHTING", ["headlight", "tail_light"], "Covers all exterior lamps; recalls give sub-component (e.g. HEADLIGHTS)."),
    ("VISIBILITY/WIPER", ["wiper_blade"], "Covers wiper motor/arms/washer and blades."),
    ("VISIBILITY", ["wiper_blade", "side_mirror"], "Covers glass, defrost, mirrors and wipers."),
    ("SUSPENSION", ["shock_absorber"], "Covers springs, control arms, struts and shock absorbers."),
    ("STRUCTURE", ["bumper", "fender_body_panel"], "Covers body, doors, hood, frame; bumper/fender not separable."),
]
UNMAPPED_NOTE = {"cabin_air_filter": "No NHTSA component covers cabin air filters; keyword count only."}
KW = {
    "brake_pad": r"brake pad|pads\b", "brake_disc": r"rotor|brake disc", "cabin_air_filter": r"cabin (air )?filter|air filter",
    "wiper_blade": r"wiper", "headlight": r"headlight|head light|headlamp", "tail_light": r"tail ?light|tail ?lamp|rear light",
    "side_mirror": r"side mirror|side-view mirror|sideview mirror|wing mirror|outside mirror|mirror", "bumper": r"bumper",
    "fender_body_panel": r"fender|quarter panel", "shock_absorber": r"shock absorber|\bshocks?\b|\bstruts?\b"}
RECALL_MAP = {"EXTERIOR LIGHTING:HEADLIGHTS": ["headlight"], "SERVICE BRAKES": ["brake_pad", "brake_disc"]}


def main():
    comps = {}
    for f in sorted(RAWD.glob("complaints_*.json")):
        for x in json.loads(f.read_text(encoding="utf-8")).get("results", []):
            comps.setdefault(x["odiNumber"], x)
    recalls = {}
    for f in sorted(RAWD.glob("recalls_*.json")):
        yr = f.stem.split("_")[1]
        for x in json.loads(f.read_text(encoding="utf-8")).get("results", []):
            r = recalls.setdefault(x["NHTSACampaignNumber"], {"campaign": x["NHTSACampaignNumber"], "component": x["Component"],
                                                              "model_years_queried": [], "summary": x["Summary"][:400]})
            r["model_years_queried"].append(yr)
    cat_to_comp = {c: [m for m, cs, _ in MAP if c in cs] for c in CATS}
    rows = []
    for c in CATS:
        mapped = set(cat_to_comp[c])
        prim = [o for o, x in comps.items() if mapped & {s.strip() for s in x["components"].split(",")}]
        kw = [o for o, x in comps.items() if re.search(KW[c], x.get("summary") or "", re.I)]
        rec_ids = sorted(k for k, v in recalls.items() if c in RECALL_MAP.get(v["component"], []))
        shared = any(len(cs) > 1 for m, cs, _ in MAP if m in mapped)
        rows.append({"vehicle_manufacturer": "Volkswagen", "vehicle_model": "ID.4", "vehicle_id": "id4", "part_category": c,
                     "nhtsa_data_available": True, "model_years_queried": "2021-2026",
                     "nhtsa_components_mapped": "; ".join(sorted(mapped)) or None,
                     "complaint_count_component": len(prim) if mapped else None,
                     "complaint_count_component_note": (("Shared with other categories mapped to the same NHTSA component; do not sum across categories. " if shared else "")
                                                        + ("" if mapped else UNMAPPED_NOTE.get(c, "No mapped NHTSA component."))) or None,
                     "complaint_count_keyword": len(kw), "complaint_keyword_regex": KW[c],
                     "recall_campaigns": "; ".join(rec_ids) or None, "recall_count": len(rec_ids),
                     "total_unique_complaints_vehicle": len(comps),
                     "source_url_complaints": "https://api.nhtsa.gov/complaints/complaintsByVehicle?make=VOLKSWAGEN&model=ID.4&modelYear={2021..2026}",
                     "source_url_recalls": "https://api.nhtsa.gov/recalls/recallsByVehicle?make=VOLKSWAGEN&model=ID.4&modelYear={2021..2026}",
                     "collection_date": "2026-11-16",
                     "caveat": "US complaints are self-reported to NHTSA and unverified; they reflect US use conditions, not Ethiopia, and are not failure rates."})
    for vid, model in [("seagull", "Seagull"), ("yuan_up", "Yuan Up")]:
        for c in CATS:
            rows.append({"vehicle_manufacturer": "BYD", "vehicle_model": model, "vehicle_id": vid, "part_category": c,
                         "nhtsa_data_available": False, "model_years_queried": None, "nhtsa_components_mapped": None,
                         "complaint_count_component": None, "complaint_count_component_note": "no NHTSA data - not sold in US",
                         "complaint_count_keyword": None, "complaint_keyword_regex": None, "recall_campaigns": None,
                         "recall_count": None, "total_unique_complaints_vehicle": None, "source_url_complaints": None,
                         "source_url_recalls": None, "collection_date": "2026-11-16",
                         "caveat": "no NHTSA data - not sold in US. No substitute vehicle used."})
    out = {"collection_date": "2026-11-16", "batch": "vehicle_failure_evidence_07",
           "source": "NHTSA public APIs (api.nhtsa.gov), no key required",
           "counting_rules": __doc__.split("Counting rules")[1].strip(),
           "component_mapping": [{"nhtsa_component": m, "categories": cs, "note": n} for m, cs, n in MAP],
           "recalls": sorted(recalls.values(), key=lambda r: r["campaign"]),
           "records": rows}
    p = BASE / "raw" / "vehicle_failure_evidence_batch_07.json"
    assert not p.exists(), "refusing to overwrite existing raw batch"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(BASE / "nhtsa_component_mapping.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["nhtsa_component", "part_category", "shared_with_other_categories", "note"])
        for m, cs, n in MAP:
            for c in cs:
                w.writerow([m, c, len(cs) > 1, n])
        w.writerow(["(none)", "cabin_air_filter", False, UNMAPPED_NOTE["cabin_air_filter"]])
    for r in rows[:10]:
        print(r["part_category"], r["complaint_count_component"], r["complaint_count_keyword"], r["recall_campaigns"])
    print("unique complaints", len(comps), "recall campaigns", len(recalls), "rows", len(rows))


if __name__ == "__main__":
    main()
