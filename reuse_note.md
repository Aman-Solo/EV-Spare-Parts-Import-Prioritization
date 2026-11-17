# Reuse note

## Reference repositories (read-only review, 2026-11-16)

Three repositories were downloaded into `references/` (outside `collection/`), and only their README, LICENSE, a 2-level file tree and their schema/column definitions were read. A similarity check then compared them with this project's code, notebook and schema (`collection_scripts/similarity_check.py`, results in `similarity_check_results.json`). It looked for identical function names, identical column names and identical blocks of 5 or more lines.

**Check result:** 0 identical blocks of 5+ lines in any repo. The only overlaps are generic names: the function `main`, and the columns `brand`, `part_number` and `vehicle_id` (interchange DB only). These three columns already existed in this project's v2 dataset (`_v2_backup/`), built before this review, so the overlap is a naming coincidence, not reuse.

| Repo | Licence | What it offers (1 line) | Reused | Where in my files | What I changed | What I rejected and why |
|---|---|---|---|---|---|---|
| `automotive-part-interchange-database` (3r1nC) | MIT | SQLite + Streamlit prototype that cross-references OE/OEM/aftermarket part numbers to vehicle fitment (tables `vehicles`, `parts`, `cross_references`, `fitment`). | **Nothing.** Same *idea* only: OE and aftermarket numbers are kept in separate fields and fitment is kept separate from the part record. This project's schema already did this in v2. [CONFIRM: did you look at this repo before designing the v2 schema? If yes, list it as "schema idea"] | n/a (if confirmed: `build_dataset.py` S_CLEAN: `oem_part_number`, `aftermarket_part_number`, `fitment_evidence_status`) | n/a | Its relational fitment table assumes year/make/model fitment is known. Our sources give model-level catalogue context only, so a `fitment` join table would overstate certainty. Its sample data has no BYD or VW EV rows. |
| `auto-parts-cross-reference` (FAPI) | MIT (code); data files: **evaluation-only sample** (DATA-LICENSE.md) | Sample of a commercial part-number cross-reference base: 1,506 brands, 13,869 part numbers, 22,550 crosses (MySQL/PostgreSQL schema). | **Nothing.** | n/a | n/a | None of our 7 tested part numbers (e.g. 14758996-00, EQEA-3501500CH, Bosch 3 397 006 839, 1EA412331B) appears in the sample. BYD appears only as a brand row. The data is licensed for evaluation only, so it could not be redistributed in our zip anyway. |
| `SparePartsInventory` (Priyanshu Raj) | MIT | Spare-parts demand forecasting (intermittent demand, ABC-XYZ classification), CPLEX inventory optimisation and anyLogistix simulation, built on M5 sales data. | **Nothing.** | n/a | n/a | It needs historical demand or sales series. We have no Ethiopian sales data, only listing counts, so forecasting or inventory optimisation would invent precision. ABC-XYZ classification was considered as a framing for the category ranking but not used. [CONFIRM: did you use its ideas anywhere, e.g. in the presentation?] |

The repos were **not** changed, **not** used by the pipeline, and are excluded from the build, the validation and the zip.

## Other code and data used

| What | Source | How it was used | Licence |
|---|---|---|---|
| NHTSA Complaints and Recalls APIs | api.nhtsa.gov (US government, public, no key) | ID.4 complaint/recall JSON saved in `raw/nhtsa_api_2026-11-16/` | US public data |
| pandas, numpy | PyPI | Scoring in `analysis.ipynb` | BSD-3-Clause |
| nbformat, nbconvert | PyPI | Generating and executing the notebook | BSD-3-Clause |
| Python standard library | python.org | `build_dataset.py`, collection scripts | PSF |

All project scripts (`build_dataset.py`, `make_scoring_input.py`, `collection_scripts/*.py`) were written for this project. No code was copied from GitHub.

**Tools disclosure:** Batches 01-04 were collected with Firecrawl (see `firecrawl_status` in `source_log.csv`) using a VS Code AI assistant [CONFIRM]. Batches 05-07, the pipeline extension, the scoring, the notebook and these documents were produced with an AI coding assistant (Claude Code), with pages fetched by plain HTTP and saved under `raw/`. Firecrawl was not used for batches 05-07.
