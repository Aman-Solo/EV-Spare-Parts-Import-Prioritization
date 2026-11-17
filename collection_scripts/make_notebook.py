"""Generates ../analysis.ipynb (kept as a script so the notebook source is reviewable as plain text)."""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# EV spare-parts import prioritisation: scoring, rankings and sensitivity

Vehicles: BYD Seagull, BYD Yuan Up, VW ID.4. Ten part categories, 30 vehicle-category rows.

* Runs top to bottom from a `data/` folder. No network calls and no API keys.
* The factor values come from `data/scoring_input.csv` (built by `make_scoring_input.py` from the cleaned evidence). The written rules are in `data/scoring_rules.csv` (v4: Ethiopian "not found" = neutral 0.5).
* Two rankings: **vehicle-part** (30 rows) and **part-category** (10 rows; the three vehicles combined, weighted by marketplace **listing counts**).
* **Listing counts are listing counts**, not sales, registrations or demand. "Not found" means *not found on the sources inspected*, not scarcity.""")

code('''# Cell 1 - setup: works locally (VS Code/Jupyter) and on Google Colab.
import os, sys

DATA_DIR = "data"                      # relative path: the data/ folder next to this notebook
IN_COLAB = "google.colab" in sys.modules
REQUIRED = ["scoring_input.csv", "scoring_rules.csv", "weights_proposed.csv",
            "cleaned_vehicle_part_evidence.csv", "vehicle_market_evidence.csv"]

if IN_COLAB:
    # Option A (default): upload the files from the data/ folder when the file picker appears.
    # Option B: put the data/ folder in Google Drive, set USE_DRIVE = True and adjust DRIVE_DATA_DIR.
    USE_DRIVE = False
    DRIVE_DATA_DIR = "/content/drive/MyDrive/ev_spare_parts/data"
    if USE_DRIVE:
        from google.colab import drive
        drive.mount("/content/drive")
        DATA_DIR = DRIVE_DATA_DIR
    elif not all(os.path.exists(os.path.join(DATA_DIR, f)) for f in REQUIRED):
        from google.colab import files
        os.makedirs(DATA_DIR, exist_ok=True)
        print("Select all files from the data/ folder:", ", ".join(REQUIRED))
        for name, content in files.upload().items():
            with open(os.path.join(DATA_DIR, os.path.basename(name)), "wb") as f:
                f.write(content)

missing = [f for f in REQUIRED if not os.path.exists(os.path.join(DATA_DIR, f))]
assert not missing, f"Missing in {DATA_DIR}/: {missing}"
print("Data folder OK:", DATA_DIR, "| Colab:", IN_COLAB)''')

code('''import pandas as pd
import numpy as np
pd.set_option("display.max_colwidth", 120)
pd.set_option("display.width", 220)

si = pd.read_csv(os.path.join(DATA_DIR, "scoring_input.csv"))
rules = pd.read_csv(os.path.join(DATA_DIR, "scoring_rules.csv"))
weights_df = pd.read_csv(os.path.join(DATA_DIR, "weights_proposed.csv"))
clean = pd.read_csv(os.path.join(DATA_DIR, "cleaned_vehicle_part_evidence.csv"))

FACTORS = ["demand_evidence", "compatibility", "sourcing_practicality", "scarcity_evidence", "evidence_confidence"]
FCOLS = ["f_" + f for f in FACTORS]
BASE_W = weights_df.set_index("factor")["weight"].reindex(FACTORS)
TOP_N = 5
print(len(si), "rows |", si["vehicle_id"].nunique(), "vehicles |", si["part_category"].nunique(), "categories")''')

md("## 1. Factor rules and weights")
code('''display(rules) if "display" in globals() else print(rules)
weights_df''')

md("## 2. Sanity checks (stop here if any fails)")
code('''assert len(si) == 30 and si["record_id"].is_unique, "need 30 unique vehicle-category rows"
assert set(si["record_id"]) == set(clean["record_id"]), "scoring_input does not match the cleaned dataset"
for c in FCOLS:
    vals = si[c].dropna()
    assert ((vals >= 0) & (vals <= 1)).all(), f"{c} outside 0-1"
assert abs(BASE_W.sum() - 1) < 1e-9, "weights must sum to 1"
print("All factors within 0-1; weights sum to", round(BASE_W.sum(), 6))
print("Missing factor values (left empty, never 0):", int(si[FCOLS].isna().sum().sum()))
print("Scarcity values used:", si["f_scarcity_evidence"].value_counts().sort_index().to_dict())''')

md("""## 3. Scoring functions

* Vehicle-part score: `sum(weight x factor) / sum(weights of the factors present)`. Missing factors are re-weighted, never set to 0.
* Category score: the three vehicles' scores for that category, combined with **listing-count weights** (Yuan Up 1,362 / Seagull 764 / ID.4 102 Adey listings). These are visibility weights, not sales. The **unweighted mean** is shown as a cross-check.
* Ties are broken by id, so the order is deterministic.""")
code('''LISTINGS = si.groupby("vehicle_id")["demand_vehicle_listing_count"].first()
assert LISTINGS.to_dict() == {"id4": 102, "seagull": 764, "yuan_up": 1362}, LISTINGS.to_dict()
LW = LISTINGS / LISTINGS.sum()
print("Listing-count weights (share of 2,228 listings):", LW.round(3).to_dict())

def score(df, w):
    w = pd.Series(w, dtype=float).reindex(FACTORS).fillna(0.0)
    vals = df[FCOLS].to_numpy(dtype=float)
    wts = np.tile(w.to_numpy(), (len(df), 1))
    present = ~np.isnan(vals)
    num = np.nansum(vals * wts, axis=1)
    den = (wts * present).sum(axis=1)
    return pd.Series(np.where(den > 0, num / den, np.nan), index=df.index)

def rank_parts(df, w):
    out = df.assign(score=score(df, w)).sort_values(["score", "record_id"], ascending=[False, True]).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out

def rank_categories(df, w):
    s = df.assign(score=score(df, w), lw=df["vehicle_id"].map(LW))
    g = s.groupby("part_category")
    out = pd.DataFrame({
        "score_listing_weighted": g.apply(lambda x: (x["score"] * x["lw"]).sum() / x["lw"].sum(), include_groups=False),
        "score_unweighted_mean": g["score"].mean(),
    }).reset_index()
    out = out.sort_values(["score_listing_weighted", "part_category"], ascending=[False, True]).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    out["rank_unweighted"] = out["score_unweighted_mean"].rank(ascending=False, method="first").astype(int)
    return out''')

md("## 4. Rankings with the proposed weights (side by side)")
code('''parts = rank_parts(si, BASE_W)
cats = rank_categories(si, BASE_W)
left = parts.head(10)[["rank", "record_id", "score"]].rename(columns={"rank": "part_rank", "score": "part_score"})
right = cats[["rank", "part_category", "score_listing_weighted", "score_unweighted_mean", "rank_unweighted"]].rename(columns={"rank": "cat_rank"})
side = pd.concat([left.reset_index(drop=True), right.reset_index(drop=True)], axis=1)
side.round(3)''')
code('''cols = ["rank", "record_id", "score", "part_numbers", "supplier_price", "ethiopian_availability",
        "et_displayed_prices_etb", "weak_evidence_flags"]
parts.head(TOP_N)[cols].round(3)''')
code('''# Evidence behind each top-5 vehicle-part row
for _, r in parts.head(TOP_N).iterrows():
    print(f"#{r['rank']} {r['record_id']}  score={r['score']:.3f}")
    for b in ["demand_basis", "compatibility_basis", "sourcing_basis", "scarcity_basis", "evidence_confidence_basis"]:
        print(f"   {b:<26} {r[b]}")
    print()''')

md("""## 5. Sensitivity analysis (both rankings)

1. Six alternative weight sets.
2. Drop-one-factor: each factor removed in turn, with the remaining weights re-normalised.
3. Random perturbation: every weight multiplied by U(0.8, 1.2), then re-normalised, 2,000 draws, fixed seed.

Rank correlation is Spearman (Pearson on ranks), so no scipy is needed.""")
code('''ALT = {
    "base (proposed)":   BASE_W.to_dict(),
    "equal weights":     dict.fromkeys(FACTORS, 0.2),
    "demand-heavy":      dict(zip(FACTORS, [0.45, 0.15, 0.15, 0.10, 0.15])),
    "feasibility-heavy": dict(zip(FACTORS, [0.20, 0.30, 0.30, 0.10, 0.10])),
    "scarcity-heavy":    dict(zip(FACTORS, [0.25, 0.15, 0.15, 0.30, 0.15])),
    "evidence-cautious": dict(zip(FACTORS, [0.25, 0.15, 0.15, 0.15, 0.30])),
}
for f in FACTORS:
    w = BASE_W.copy(); w[f] = 0.0
    ALT[f"drop {f}"] = (w / w.sum()).to_dict()

base_p = parts.set_index("record_id")["rank"]; base_c = cats.set_index("part_category")["rank"]
top_p, top_c = list(parts.head(TOP_N)["record_id"]), list(cats.head(TOP_N)["part_category"])
rows, tops_p, tops_c = [], {}, {}
for name, w in ALT.items():
    rp, rc = rank_parts(si, w), rank_categories(si, w)
    tops_p[name] = list(rp.head(TOP_N)["record_id"]); tops_c[name] = list(rc.head(TOP_N)["part_category"])
    rows.append({"scenario": name,
                 "parts_top5_overlap": len(set(tops_p[name]) & set(top_p)),
                 "parts_spearman": round(rp.set_index("record_id")["rank"].reindex(base_p.index).corr(base_p), 3),
                 "cats_top5_overlap": len(set(tops_c[name]) & set(top_c)),
                 "cats_spearman": round(rc.set_index("part_category")["rank"].reindex(base_c.index).corr(base_c), 3),
                 "parts_top5": ", ".join(tops_p[name]), "cats_top5": ", ".join(tops_c[name])})
sens = pd.DataFrame(rows)
sens''')
code('''rng = np.random.default_rng(20261116)
N = 2000
cnt_p = pd.Series(0, index=si["record_id"]); cnt_c = pd.Series(0, index=sorted(si["part_category"].unique()))
for _ in range(N):
    w = BASE_W * rng.uniform(0.8, 1.2, len(FACTORS)); w = w / w.sum()
    cnt_p[rank_parts(si, w).head(TOP_N)["record_id"]] += 1
    cnt_c[rank_categories(si, w).head(TOP_N)["part_category"]] += 1
share_p, share_c = (cnt_p / N).rename("perturb_share_top5"), (cnt_c / N).rename("perturb_share_top5")
pd.concat([share_p[share_p > 0].sort_values(ascending=False).round(3).reset_index().rename(columns={"index": "record_id"}),
           share_c[share_c > 0].sort_values(ascending=False).round(3).reset_index().rename(columns={"index": "part_category"})], axis=1)''')

md("""## 6. Robust, borderline and weak-evidence tiers

* **Robust**: in the top 5 in *every* named scenario (6 weight sets + 5 drop-one) **and** in at least 95% of perturbation draws.
* **Borderline**: in the base top 5 but not robust.
* **Weak evidence**: a flag that applies on top of either tier. For a vehicle-part row it means no specific part record, fitment low/insufficient, no supplier price, or Ethiopian factor only "not found". For a category it means the weak flag is set on the vehicle with the largest listing weight in that category.""")
code('''def tiers(base_top, tops, share, weak):
    out = []
    for k in base_top:
        every = all(k in t for t in tops.values())
        out.append({"item": k, "named_scenarios_in_top5": f"{sum(k in t for t in tops.values())}/{len(tops)}",
                    "perturb_share": round(float(share.get(k, 0)), 3),
                    "tier": "robust" if every and share.get(k, 0) >= 0.95 else "borderline",
                    "weak_evidence": weak.get(k) or "-"})
    return pd.DataFrame(out)

def weak_reason(r):
    rs = []
    flags = str(r["weak_evidence_flags"]) if pd.notna(r["weak_evidence_flags"]) else ""
    for k in ("no specific part record", "fitment low", "fitment insufficient", "no supplier price"):
        if k in flags: rs.append(k)
    if r["ethiopian_availability"] == "not_found_on_sources_inspected": rs.append("ET factor only 'not found'")
    return "; ".join(rs)

weak_p = {r["record_id"]: weak_reason(r) for _, r in si.iterrows()}
lead = si.assign(lw=si["vehicle_id"].map(LW)).sort_values("lw", ascending=False).groupby("part_category").first()
weak_c = {c: (f"{lead.loc[c, 'record_id']}: " + weak_reason(lead.loc[c])) if weak_reason(lead.loc[c]) else "" for c in lead.index}

tier_p = tiers(top_p, tops_p, share_p, weak_p)
tier_c = tiers(top_c, tops_c, share_c, weak_c)
print("VEHICLE-PART top 5"); display(tier_p) if "display" in globals() else print(tier_p)
print("CATEGORY top 5"); tier_c''')

code('''gap_p = parts["score"].iloc[TOP_N - 1] - parts["score"].iloc[TOP_N]
gap_c = cats["score_listing_weighted"].iloc[TOP_N - 1] - cats["score_listing_weighted"].iloc[TOP_N]
print(f"Vehicle-part: rank 5 vs 6 gap {gap_p:.3f}; ranks 1-10 span {parts['score'].iloc[0]:.3f}-{parts['score'].iloc[9]:.3f}")
print(f"Category:     rank 5 vs 6 gap {gap_c:.3f}")
s5 = parts["score"].iloc[TOP_N - 1]
tied = parts[np.isclose(parts["score"], s5, atol=1e-9)]["record_id"].tolist()
if len(tied) > 1:
    print(f"TIE at the rank-{TOP_N} cut-off (score {s5:.6f}): {tied} - the order between them is only the alphabetical tie-break; treat all as borderline.")
print("Mean top-5 overlap (named scenarios): parts", round(sens["parts_top5_overlap"].mean(), 2), "| categories", round(sens["cats_top5_overlap"].mean(), 2))
no_et_p, no_et_c = set(tops_p["drop scarcity_evidence"]), set(tops_c["drop scarcity_evidence"])
print("Base top-5 parts that leave the top 5 without the Ethiopian factor:", [x for x in top_p if x not in no_et_p] or "none")
print("Base top-5 categories that leave the top 5 without the Ethiopian factor:", [x for x in top_c if x not in no_et_c] or "none")
same_cat_order = (cats["rank"] == cats["rank_unweighted"]).all()
print("Category ranking identical with unweighted mean:", bool(same_cat_order),
      "| top-5 overlap weighted vs unweighted:", len(set(top_c) & set(cats.sort_values("rank_unweighted").head(TOP_N)["part_category"])), "of 5")''')

md("""## 7. How to read this

* The rankings prioritise **evidence**; they are not a sales forecast. Demand uses vehicle *listing counts* as a visibility proxy plus a stated part-replacement assumption.
* "Robust" means the item stays in the top 5 whatever reasonable weights are used. "Borderline" items depend on the weights. "Weak evidence" items need checking before money is spent.
* Before any purchase: confirm fitment by VIN with the supplier, confirm current price and stock, and check Ethiopian prices directly with sellers.""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb["metadata"]["language_info"] = {"name": "python"}
out = Path(__file__).resolve().parents[1] / "analysis.ipynb"
nbf.write(nb, out)
print("wrote", out.name, len(C), "cells")
