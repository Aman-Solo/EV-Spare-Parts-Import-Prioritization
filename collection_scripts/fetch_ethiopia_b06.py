"""Stage 2 collector: runs the 30 vehicle x category searches on Ethiopian marketplaces and saves raw
responses to a directory given on the command line (one file per query). No parsing here.
Usage: python fetch_ethiopia_b06.py OUT_DIR"""
import json, sys, time, urllib.parse, urllib.request, pathlib

VEH = {"seagull": "BYD Seagull", "yuan_up": "BYD Yuan Up", "id4": "Volkswagen ID.4"}
CAT = {"brake_pad": "brake pad", "brake_disc": "brake disc", "cabin_air_filter": "cabin air filter",
       "wiper_blade": "wiper blade", "headlight": "headlight", "tail_light": "tail light",
       "side_mirror": "side mirror", "bumper": "bumper", "fender_body_panel": "fender",
       "shock_absorber": "shock absorber"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
SITES = {
    "adey": "https://adey-market.com/api/backend/public/search?q={q}",
    "jiji": "https://jiji.com.et/search?query={q}",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # network failure is logged, not hidden
        return 0, f"ERROR {type(e).__name__}: {e}"


def main(out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for vid, vname in VEH.items():
        for cid, cname in CAT.items():
            q = f"{vname} {cname}"
            for site, tpl in SITES.items():
                url = tpl.format(q=urllib.parse.quote(q))
                status, body = get(url)
                fn = f"{site}__{vid}__{cid}." + ("json" if site == "adey" else "html")
                (out / fn).write_text(body, encoding="utf-8")
                manifest.append({"site": site, "vehicle_id": vid, "category": cid, "query": q, "url": url,
                                 "http_status": status, "file": fn, "bytes": len(body)})
                time.sleep(1.0)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    bad = [m for m in manifest if m["http_status"] != 200]
    print(len(manifest), "requests;", len(bad), "non-200")


def brand_pass(out):
    """Adey treats '<brand> <model> <part>' as a whole-car query (0 part hits), so a second pass
    searches '<brand> <part>' and model names are classified from listing titles afterwards."""
    out = pathlib.Path(out)
    manifest = []
    for brand in ["BYD", "Volkswagen"]:
        for cid, cname in CAT.items():
            q = f"{brand} {cname}"
            url = SITES["adey"].format(q=urllib.parse.quote(q))
            status, body = get(url)
            fn = f"adeybrand__{brand.lower()}__{cid}.json"
            (out / fn).write_text(body, encoding="utf-8")
            manifest.append({"site": "adey_brand", "brand": brand, "category": cid, "query": q, "url": url,
                             "http_status": status, "file": fn, "bytes": len(body)})
            time.sleep(1.0)
    (out / "manifest_brand_pass.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(len(manifest), "requests;", sum(m["http_status"] != 200 for m in manifest), "non-200")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--brand-pass":
        brand_pass(sys.argv[1])
    else:
        main(sys.argv[1])
