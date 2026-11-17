"""Read-only similarity check between this project's code/notebook/schema and the reference repos.
Compares: (1) function names, (2) column / field names, (3) identical normalised blocks of >= 5 consecutive lines.
Usage: python similarity_check.py <collection_dir> <references_dir> <out_json>"""
import ast, csv, json, re, sys
from pathlib import Path

BLOCK = 5


def norm_lines(text):
    out = []
    for ln in text.splitlines():
        s = re.sub(r"\s+", " ", ln.split("#")[0]).strip()
        if len(s) > 3 and s not in ("else:", "try:", "return", "pass", ")", "]", "}", "})", "])"):
            out.append(s)
    return out


def blocks(lines):
    return {"\n".join(lines[i:i + BLOCK]) for i in range(len(lines) - BLOCK + 1)}


def py_funcs(text):
    try:
        return {n.name for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    except SyntaxError:
        return set(re.findall(r"^\s*def (\w+)", text, re.M))


def nb_code(p):
    try:
        nb = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        return "\n".join("".join(c.get("source", "")) for c in nb.get("cells", []) if c.get("cell_type") == "code")
    except Exception:
        return ""


def sql_cols(text):
    cols = set()
    for body in re.findall(r"CREATE TABLE[^(]*\((.*?)\);", text, re.S | re.I):
        for ln in body.splitlines():
            m = re.match(r"\s*`?(\w+)`?\s+\w+", ln)
            if m and m.group(1).upper() not in ("PRIMARY", "KEY", "UNIQUE", "FOREIGN", "CONSTRAINT", "INDEX"):
                cols.add(m.group(1).lower())
    return cols


def collect(root, mine):
    funcs, cols, blks, files = set(), set(), {}, 0
    for p in root.rglob("*"):
        if not p.is_file() or ".git" in p.parts or (mine and ("references" in p.parts or "_v2_backup" in p.parts or "raw" in p.parts)):
            continue
        suf = p.suffix.lower()
        try:
            if suf == ".py":
                t = p.read_text(encoding="utf-8", errors="replace"); funcs |= py_funcs(t)
            elif suf == ".ipynb":
                t = nb_code(p); funcs |= py_funcs(t)
            elif suf == ".sql":
                t = p.read_text(encoding="utf-8", errors="replace"); cols |= sql_cols(t)
            elif suf == ".csv" and p.stat().st_size < 50_000_000:
                with open(p, encoding="utf-8", errors="replace", newline="") as f:
                    cols |= {c.strip().lower() for c in next(csv.reader(f), [])}
                continue
            else:
                continue
        except Exception:
            continue
        files += 1
        if mine and suf == ".py" and p.name == "similarity_check.py":
            continue
        for b in blocks(norm_lines(t)):
            blks.setdefault(b, str(p.relative_to(root)))
    # string literals of quoted column names in python (schemas defined in code)
    return funcs, cols, blks, files


def main(coll, refs, out):
    coll, refs = Path(coll), Path(refs)
    mf, mc, mb, mn = collect(coll, True)
    # my schema columns are also defined as tuples in build_dataset.py S_* lists; headers of my CSVs already cover them
    res = {"mine": {"files_scanned": mn, "functions": len(mf), "columns": len(mc), "blocks": len(mb)}, "repos": {}}
    for repo in sorted(d for d in refs.iterdir() if d.is_dir()):
        rf, rc, rb, rn = collect(repo, False)
        same_blocks = sorted(set(mb) & set(rb))
        res["repos"][repo.name] = {
            "files_scanned": rn, "functions": len(rf), "columns": len(rc),
            "identical_function_names": sorted(mf & rf),
            "identical_column_names": sorted(mc & rc),
            "identical_blocks_5plus_lines": [{"mine": mb[b], "theirs": rb[b], "first_line": b.splitlines()[0][:100]} for b in same_blocks],
        }
    Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("mine:", res["mine"])
    for k, v in res["repos"].items():
        print(f"{k}: scanned {v['files_scanned']} files | same function names {v['identical_function_names']} | "
              f"same column names {v['identical_column_names']} | identical 5+-line blocks {len(v['identical_blocks_5plus_lines'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
