"""
data/recipes.py

Per-board "extraction recipes" that turn each board's idiosyncratic
sheet layout(s) in the master workbook into three normalized long-format
tables, used by the Overview page (and reusable by the dedicated Gender
/ Group / Regular-vs-Private pages later):

  load_gender_table()    ->  Board | Year | Gender   | Appeared | Passed | Pass %
  load_category_table()  ->  Board | Year | Category | Appeared | Passed | Pass %
  load_group_table()     ->  Board | Year | Group    | Appeared | Passed | Pass %

Gender is always "Male"/"Female"; Category is always "Regular"/"Private";
Group is always "Science"/"Humanities" (the gazettes' "Arts" and
"General" labels normalize to Humanities — see the group section's
_canon_group map and the Group Wise page's footnote).
Pass % is recomputed here as Passed / Appeared so the fraction-vs-percent
formatting differences between boards can never leak into charts.

WHY RECIPES: the 15 gazettes report gender and candidate type in at
least six different layouts — combined "Regular (Boys)" text, separate
Gender columns, wide Metric-row sheets (Lahore), split sheets (Kohat,
Gujranwala tech streams), and a board with no gender data at all (FSD).
Each recipe below was written against its sheet's real layout and then
VERIFIED: the extracted rows were summed per board/year and cross-checked
against the Overall Summary sheet's Appeared/Passed totals (every board
matches exactly; see the verification notes per board below).

Conventions encoded here (do not "simplify" without re-verifying):
  * Total / Sub Total / Grand Total / 'Change (2026-2025)' rows are
    always excluded — they would double-count the detail rows.
  * Gujranwala: the Tech-group sheet is ADDED to the main group sheet
    (tech streams live in a separate sheet); its 'Grand Total' rows
    duplicate 'Sub Total' and are dropped.
  * Kohat: Science Group sheet + General Group sheet are combined.
  * Lahore: three wide sheets (Science/Humanities/Tech); gender comes
    from the 'All Boys/Girls (Reg+Pvt)' columns, category from
    'Regular Total'/'Private Total'. Tech has no 2025 rows.
  * Mardan reports 'Promoted', not 'Passed' (see
    availability.PROMOTED_TERMINOLOGY_BOARDS): Appeared := Total
    Candidates, Passed := Promoted Candidates (matches Overall Summary).
  * Peshawar uses the same Pass/Promoted convention: Appeared :=
    Total Students, Passed := Passed + Promoted (the workbook's own
    Overall Summary convention for Peshawar — verified: sums match its
    101,888/100,660 and 97,950/96,950 rows exactly).
  * Bahawalpur 2026: the gazette's Grand Total (105,601) exceeds its
    own group-level detail rows (101,680) by 3,921 candidates it never
    classifies by group/gender. The category table uses the sheet's own
    published category totals (exact match); the gender table keeps
    only the detail rows that actually exist — the 3,921 unclassified
    candidates are NOT invented.
  * FBISE 'Ex/Private' is mapped to 'Private'.
  * FSD publishes no gender breakdown (its gender table is empty); its
    Regular/Private split comes from the 'Overall * Candidates' rows of
    FSD-Overall Statistical Data.
  * DGK gender comes from its dedicated Gender Wise sheet; its
    Regular/Private totals from the 'Regular Total'/'Private Total'
    group rows of DGK-Group Wise Regular Private.
  * Swat has only a 2026 gazette, so its rows carry Year=2026 only.
"""

import pandas as pd
import streamlit as st

from data.loader import load_sheet

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _clean(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """Standard first step for every recipe: coerce Year to numeric
    (which drops 'Change (2026-2025)' caption rows), coerce the value
    columns to numeric, and drop rows with no usable numbers."""
    out = df.copy()
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce")
    out = out[out["Year"].isin([2025, 2026])]
    out["Year"] = out["Year"].astype(int)
    for col in value_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=value_cols)


def _gender_of(text) -> str | None:
    """'Regular (Boys)' / 'Private Female' / 'Male' ... -> Male/Female."""
    t = str(text).lower()
    if "female" in t or "girl" in t:
        return "Female"
    if "male" in t or "boy" in t:
        return "Male"
    return None


def _category_of(text) -> str | None:
    """'Regular (Govt.)' -> Regular; 'Ex/Private' -> Private; else None."""
    t = str(text).lower()
    if "regular" in t:
        return "Regular"
    if "private" in t:
        return "Private"
    return None


def _aggregate(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Sum Appeared/Passed by the given key columns."""
    agg = df.groupby(keys, as_index=False)[["Appeared", "Passed"]].sum()
    agg["Appeared"] = agg["Appeared"].round(0).astype(int)
    agg["Passed"] = agg["Passed"].round(0).astype(int)
    return agg


# ---------------------------------------------------------------------------
# Per-board extractors — each returns {"gender": df|None, "category": df}
# with columns Year | Gender-or-Category | Appeared | Passed (no Board
# column; the loaders below tag the board name on).
# ---------------------------------------------------------------------------


def _extract_abbottabad():
    # Abbottabad-Overall Pass %: Year | Candidate Type ('Regular Female',
    # 'Private Male', ...) | Appeared | Passed, with GRAND TOTAL and
    # Change rows to skip. Verified: sums match Overall Summary exactly.
    df = load_sheet("Abbottabad-Overall Pass %")
    df = _clean(df, ["Appeared", "Passed"])
    df = df[~df["Candidate Type"].astype(str).str.lower().str.contains("grand")]
    df["Gender"] = df["Candidate Type"].map(_gender_of)
    df["Category"] = df["Candidate Type"].map(_category_of)
    return {
        "gender": _aggregate(df.dropna(subset=["Gender"]), ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_bahawalpur():
    # Bahawalpur-General Pass Percent: Year | Category ('Regular (Govt.)',
    # 'Regular (Affiliated)', 'Private', 'Total (Regular)', 'Grand Total')
    # | Group | Gender.
    #
    # DATA INTEGRITY NOTE (verified against the raw sheet): in 2026 the
    # gazette's own Grand Total (105,601) exceeds the sum of its
    # group-level detail rows (101,680) by 3,921 candidates that the
    # source table never classifies by group/gender. We therefore do NOT
    # reconstruct totals from detail rows:
    #   * category table <- the sheet's own published category totals
    #     ('Total (Regular)' and 'Private' rows at Group=Total,
    #     Gender=Total), which match Overall Summary exactly for both
    #     years (2026: 86,390 + 19,211 = 105,601).
    #   * gender table <- the group-level Male/Female detail rows, the
    #     only gender breakdown the gazette publishes. For 2026 these
    #     cover 101,680 of 105,601 candidates; the 3,921 unclassified
    #     candidates are NOT invented — the board's gender rows are
    #     simply short of its board total by that amount.
    df = load_sheet("Bahawalpur-General Pass Percent")
    df = _clean(df, ["Appeared", "Passed"])

    detail = df[df["Category"].isin(
        ["Regular (Govt.)", "Regular (Affiliated)", "Private"]
    )]
    detail = detail[~detail["Group"].astype(str).str.lower().str.contains("total")]
    detail = detail[~detail["Gender"].astype(str).str.lower().str.contains("total")]
    gender = _aggregate(detail, ["Year", "Gender"])

    reg = df[(df["Category"] == "Total (Regular)")
             & (df["Group"] == "Total") & (df["Gender"] == "Total")].assign(Category="Regular")
    prv = df[(df["Category"] == "Private")
             & (df["Group"] == "Total") & (df["Gender"] == "Total")].assign(Category="Private")
    category = _aggregate(
        pd.concat([reg, prv])[["Year", "Category", "Appeared", "Passed"]],
        ["Year", "Category"],
    )
    return {"gender": gender, "category": category}


def _extract_bannu():
    # Bannu-Result at a Glance: Year | Group | Category ('Regular (Boys)',
    # 'Private (Girls)', 'Sub Total', 'G. Total'). Detail rows only.
    # Verified vs Overall Summary.
    df = load_sheet("Bannu-Result at a Glance")
    df = _clean(df, ["Appeared", "Passed"])
    df = df[df["Category"].isin(
        ["Regular (Boys)", "Regular (Girls)", "Private (Boys)", "Private (Girls)"]
    )]
    df["Gender"] = df["Category"].map(_gender_of)
    df["Category"] = df["Category"].map(_category_of)
    return {
        "gender": _aggregate(df.dropna(subset=["Gender"]), ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_dgk():
    # Gender: dedicated DGK-Gender Wise Pass % sheet (clean Male/Female
    # rows). Regular/Private: the 'Regular Total' / 'Private Total' group
    # rows of DGK-Group Wise Regular Private (one row per year each).
    # Verified vs Overall Summary.
    g = load_sheet("DGK-Gender Wise Pass %")
    g = _clean(g, ["Appeared", "Passed"])
    gender = _aggregate(g[g["Gender"].isin(["Male", "Female"])], ["Year", "Gender"])

    rp = load_sheet("DGK-Group Wise Regular Private")
    rp = _clean(rp, ["Appeared", "Passed"])
    # The 'Regular Total'/'Private Total' rows exist for Male, Female AND
    # Total — only the Gender='Total' row is the category total (the
    # Male/Female rows are its halves; summing all three would double).
    totals = rp[rp["Group"].isin(["Regular Total", "Private Total"])
                & rp["Gender"].eq("Total")].copy()
    totals["Category"] = totals["Group"].map(
        {"Regular Total": "Regular", "Private Total": "Private"}
    )
    category = _aggregate(totals.dropna(subset=["Category"]), ["Year", "Category"])
    return {"gender": gender, "category": category}


def _extract_fbise():
    # FBISE-Group Wise Pass %: Candidate Type ('Regular' / 'Ex/Private'),
    # Group (Science/Humanities/Total), Gender (Male/Female/Total).
    # Detail rows (real genders, real groups) only. Verified.
    df = load_sheet("FBISE-Group Wise Pass %")
    df = _clean(df, ["Appeared", "Pass"])
    df = df[df["Candidate Type"].isin(["Regular", "Ex/Private"])]
    df = df[df["Gender"].isin(["Male", "Female"]) & df["Group"].ne("Total")]
    df["Passed"] = df["Pass"]
    df["Category"] = df["Candidate Type"].map(_category_of)
    return {
        "gender": _aggregate(df, ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_fsd():
    # FSD publishes NO gender breakdown. Regular/Private: the
    # 'Overall Private Candidates' / 'Overall Regular Candidates' rows of
    # FSD-Overall Statistical Data. Verified vs Overall Summary.
    df = load_sheet("FSD-Overall Statistical Data")
    df = _clean(df, ["Appeared", "Pass"])
    totals = df[df["Group"].astype(str).str.startswith("Overall")].copy()
    totals["Passed"] = totals["Pass"]
    totals["Category"] = totals["Category"].map(_category_of)
    return {
        "gender": None,
        "category": _aggregate(totals.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_gujranwala():
    # Two sheets: Gujranwala-Group Wise Pass % (Science/General/Deaf &
    # Dumb, Category Regular/Private, Gender Male/Female/Sub Total) plus
    # Gujranwala-Tech Group Wise Pass (tech streams, Regular Male/Female
    # + Sub Total; its Grand Total rows duplicate Sub Total). Verified:
    # combined sums match Overall Summary.
    main = load_sheet("Gujranwala-Group Wise Pass %")
    main = _clean(main, ["Appeared", "Passed"])
    main = main[main["Category"].isin(["Regular", "Private"])]

    tech = load_sheet("Gujranwala-Tech Group Wise Pass")
    tech = _clean(tech, ["Appeared", "Passed"])
    tech = tech[tech["Category"].ne("Grand Total")]

    g_main = main[main["Gender"].isin(["Male", "Female"])]
    g_tech = tech[tech["Category"].isin(["Regular Male", "Regular Female"])].copy()
    g_tech["Gender"] = g_tech["Category"].map(_gender_of)
    gender = pd.concat(
        [g_main[["Year", "Gender", "Appeared", "Passed"]],
         g_tech[["Year", "Gender", "Appeared", "Passed"]]]
    )

    c_main = main[main["Gender"] == "Sub Total"]
    c_tech = tech[tech["Category"] == "Sub Total"].copy()
    c_tech["Category"] = "Regular"  # tech streams are all Regular
    category = pd.concat(
        [c_main[["Year", "Category", "Appeared", "Passed"]],
         c_tech[["Year", "Category", "Appeared", "Passed"]]]
    )
    return {
        "gender": _aggregate(gender, ["Year", "Gender"]),
        "category": _aggregate(category, ["Year", "Category"]),
    }


def _extract_kohat():
    # Two sheets (Science Group + General Group), same layout:
    # Year | Category ('Regular (Boys)', 'Private (Girls)', 'Total',
    # 'Grand Total (Science..)'). Detail rows only. Verified.
    frames = []
    for sheet in ("Kohat-Science Group", "Kohat-General Group"):
        df = load_sheet(sheet)
        df = _clean(df, ["Appeared", "Passed"])
        frames.append(df)
    df = pd.concat(frames)
    df = df[~df["Category"].astype(str).str.lower().str.contains("total")]
    df["Gender"] = df["Category"].map(_gender_of)
    df["Category"] = df["Category"].map(_category_of)
    return {
        "gender": _aggregate(df.dropna(subset=["Gender"]), ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_lahore():
    # Three WIDE sheets (Science/Humanities/Tech): one row per
    # Year x Metric ('Appeared'/'Passed'/'Pass %'), with columns
    # Regular Boys/Girls/Total, Private ..., 'All Boys (Reg+Pvt)',
    # 'All Girls (Reg+Pvt)'. Gender from the All Boys/Girls columns,
    # category from Regular/Private Total. Tech has no 2025 rows.
    # Verified vs Overall Summary.
    gender_records, category_records = [], []
    for sheet in ("Lahore-Science Group", "Lahore-Humanities Group", "Lahore-Tech Group"):
        df = load_sheet(sheet)
        value_cols = ["Regular Total", "Private Total", "All Boys (Reg+Pvt)", "All Girls (Reg+Pvt)"]
        df = _clean(df, value_cols)
        for year, grp in df.groupby("Year"):
            appeared = grp[grp["Metric"] == "Appeared"]
            passed = grp[grp["Metric"] == "Passed"]
            if appeared.empty or passed.empty:
                continue
            a, p = appeared.iloc[0], passed.iloc[0]
            gender_records.append(
                {"Year": year, "Gender": "Male",
                 "Appeared": a["All Boys (Reg+Pvt)"], "Passed": p["All Boys (Reg+Pvt)"]}
            )
            gender_records.append(
                {"Year": year, "Gender": "Female",
                 "Appeared": a["All Girls (Reg+Pvt)"], "Passed": p["All Girls (Reg+Pvt)"]}
            )
            category_records.append(
                {"Year": year, "Category": "Regular",
                 "Appeared": a["Regular Total"], "Passed": p["Regular Total"]}
            )
            category_records.append(
                {"Year": year, "Category": "Private",
                 "Appeared": a["Private Total"], "Passed": p["Private Total"]}
            )
    gender = _aggregate(pd.DataFrame(gender_records), ["Year", "Gender"])
    category = _aggregate(pd.DataFrame(category_records), ["Year", "Category"])
    return {"gender": gender, "category": category}


def _extract_mardan():
    # Two sheets (Science + Humanities), Promoted terminology:
    # Year | Category ('Regular (Female)', ..., 'TOTAL') |
    # Total Candidates | Promoted Candidates. Appeared := Total
    # Candidates, Passed := Promoted (matches Overall Summary). Verified.
    frames = []
    for sheet in ("Mardan-Science Group", "Mardan-Humanities Group"):
        df = load_sheet(sheet)
        df = _clean(df, ["Total Candidates", "Promoted Candidates"])
        df = df[~df["Category"].astype(str).str.lower().str.contains("total")]
        df["Appeared"] = df["Total Candidates"]
        df["Passed"] = df["Promoted Candidates"]
        frames.append(df[["Year", "Category", "Appeared", "Passed"]])
    df = pd.concat(frames)
    df["Gender"] = df["Category"].map(_gender_of)
    df["Category"] = df["Category"].map(_category_of)
    return {
        "gender": _aggregate(df.dropna(subset=["Gender"]), ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_peshawar():
    # Gender: Peshawar-Gender Wise Result (Category 'Regular (Male)' etc.,
    # Grand Total row skipped). Reg/Private: Peshawar-Group Wise
    # Distributio (same layout + Group column). Promoted convention:
    # Appeared := Total Students (the Overall Summary sheet counts every
    # registered candidate as 'Appeared' for Peshawar), Passed :=
    # Passed + Promoted. Verified vs Overall Summary.
    g = load_sheet("Peshawar-Gender Wise Result")
    g = _clean(g, ["Total Students", "Passed", "Promoted", "Absent"])
    g = g[~g["Category"].astype(str).str.lower().str.contains("grand")]
    g["Appeared"] = g["Total Students"]
    g["PassedTotal"] = g["Passed"] + g["Promoted"]
    g["Gender"] = g["Category"].map(_gender_of)
    gender = _aggregate(
        g.dropna(subset=["Gender"])[["Year", "Gender", "Appeared", "PassedTotal"]]
        .rename(columns={"PassedTotal": "Passed"}),
        ["Year", "Gender"],
    )

    w = load_sheet("Peshawar-Group Wise Distributio")
    w = _clean(w, ["Total Students", "Passed", "Promoted", "Absent"])
    w = w[~w["Category"].astype(str).str.lower().str.contains("grand")]
    w["Appeared"] = w["Total Students"]
    w["PassedTotal"] = w["Passed"] + w["Promoted"]
    w["Category"] = w["Category"].map(_category_of)
    category = _aggregate(
        w.dropna(subset=["Category"])[["Year", "Category", "Appeared", "PassedTotal"]]
        .rename(columns={"PassedTotal": "Passed"}),
        ["Year", "Category"],
    )
    return {"gender": gender, "category": category}


def _extract_rawalpindi():
    # Rawalpindi-Result Statistical D: Year | Gender (Male/Female/Total)
    # | Category ('Regular (Government Institutes)',
    # 'Regular (Affiliated Institutes)', 'Private Candidates',
    # 'Sub-Total'). Detail rows only; both Regular variants -> Regular.
    # Verified vs Overall Summary.
    df = load_sheet("Rawalpindi-Result Statistical D")
    df = _clean(df, ["Appeared", "Passed"])
    df = df[~df["Category"].astype(str).str.lower().str.contains("sub-total")]
    df = df[df["Gender"].isin(["Male", "Female"])]
    df["Category"] = df["Category"].map(_category_of)
    return {
        "gender": _aggregate(df, ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


def _extract_sahiwal():
    # Sahiwal-Group Wise Pass %: Year | Candidate Type ('Regular',
    # 'Private', 'Overall') | Group (6 groups + 'TOTAL') | Gender.
    # Detail rows only (drop Group TOTAL rows to avoid double-count).
    # Verified vs Overall Summary.
    df = load_sheet("Sahiwal-Group Wise Pass %")
    df = _clean(df, ["Appeared", "Pass"])
    df = df[df["Candidate Type"].isin(["Regular", "Private"])]
    df = df[df["Gender"].isin(["Male", "Female"])
            & ~df["Group"].astype(str).str.lower().str.contains("total")]
    df["Passed"] = df["Pass"]
    df["Category"] = df["Candidate Type"]
    return {
        "gender": _aggregate(df, ["Year", "Gender"]),
        "category": _aggregate(df, ["Year", "Category"]),
    }


def _extract_sargodha():
    # Sargodha-Group Wise Pass %: Year | Candidate Type ('Regular',
    # 'Private', 'Overall') | Group (7 groups + 'Total') | Gender.
    # Detail rows only. Verified vs Overall Summary.
    df = load_sheet("Sargodha-Group Wise Pass %")
    df = _clean(df, ["Appeared", "Pass"])
    df = df[df["Candidate Type"].isin(["Regular", "Private"])]
    df = df[df["Gender"].isin(["Male", "Female"])
            & ~df["Group"].astype(str).str.lower().str.contains("total")]
    df["Passed"] = df["Pass"]
    df["Category"] = df["Candidate Type"]
    return {
        "gender": _aggregate(df, ["Year", "Gender"]),
        "category": _aggregate(df, ["Year", "Category"]),
    }


def _extract_swat():
    # Swat-Group Wise Pass %: Year | Group | Category ('Regular (Boys)',
    # ..., 'Sub Total', 'Grand Total'). 2026 only. Detail rows only.
    # Verified vs Overall Summary.
    df = load_sheet("Swat-Group Wise Pass %")
    df = _clean(df, ["Appeared", "Passed"])
    df = df[df["Category"].isin(
        ["Regular (Boys)", "Regular (Girls)", "Private (Boys)", "Private (Girls)"]
    )]
    df["Gender"] = df["Category"].map(_gender_of)
    df["Category"] = df["Category"].map(_category_of)
    return {
        "gender": _aggregate(df.dropna(subset=["Gender"]), ["Year", "Gender"]),
        "category": _aggregate(df.dropna(subset=["Category"]), ["Year", "Category"]),
    }


# Board order follows config.settings.ALL_BOARDS.
_EXTRACTORS = {
    "Abbottabad": _extract_abbottabad,
    "Bahawalpur": _extract_bahawalpur,
    "Bannu": _extract_bannu,
    "DGK": _extract_dgk,
    "FBISE": _extract_fbise,
    "FSD": _extract_fsd,
    "Gujranwala": _extract_gujranwala,
    "Kohat": _extract_kohat,
    "Lahore": _extract_lahore,
    "Mardan": _extract_mardan,
    "Peshawar": _extract_peshawar,
    "Rawalpindi": _extract_rawalpindi,
    "Sahiwal": _extract_sahiwal,
    "Sargodha": _extract_sargodha,
    "Swat": _extract_swat,
}

_TABLE_COLUMNS = ["Board", "Year", "Gender", "Appeared", "Passed", "Pass %"]


def _build_table(kind: str) -> pd.DataFrame:
    """Runs every board's extractor and stacks the requested table
    (kind='gender' or 'category'), tagging the Board name on and
    recomputing Pass % = Passed / Appeared."""
    frames = []
    for board, extractor in _EXTRACTORS.items():
        result = extractor()
        table = result[kind]
        if table is None or table.empty:
            continue
        table = table.copy()
        table.insert(0, "Board", board)
        frames.append(table)
    if not frames:
        return pd.DataFrame(columns=_TABLE_COLUMNS)
    df = pd.concat(frames, ignore_index=True)
    df["Pass %"] = (df["Passed"] / df["Appeared"]).where(df["Appeared"] > 0)
    return df.sort_values(["Board", "Year"]).reset_index(drop=True)


@st.cache_data(show_spinner="Loading gender data...")
def load_gender_table() -> pd.DataFrame:
    """All boards' gender breakdown, normalized. FSD is absent (its
    gazette publishes no gender split — see data/availability.py)."""
    return _build_table("gender")


@st.cache_data(show_spinner="Loading Regular/Private data...")
def load_category_table() -> pd.DataFrame:
    """All 15 boards' Regular vs Private breakdown, normalized."""
    return _build_table("category")


# ---------------------------------------------------------------------------
# Group-wise (Science vs Humanities) extractors — same discipline as the
# recipes above: each returns DETAIL rows only (Year | Group | Appeared |
# Passed) with every Total / Sub Total / Grand Total / 'Overall *' rollup
# excluded; the loader re-aggregates and recomputes Pass %.
#
# Label normalization (verified against every sheet's actual values):
#   * "Humanities" ships as: Humanities / Humanities Group (Bahawalpur,
#     Bannu, DGK, FBISE, Sargodha, Swat), Humanities (General) (Rawalpindi
#     2025 — its 2026 gazette renames the same group to "Humanities"),
#     Arts (Abbottabad, Peshawar), General (DGK M/F sheet, FSD,
#     Gujranwala, Kohat, Sahiwal).
#   * Out of scope, deliberately excluded: Matric-Tech streams
#     (Rawalpindi, Sahiwal, Sargodha), Tech (Gujranwala, Lahore), Deaf &
#     Dumb / Deaf & Defective (FSD, Gujranwala, Sahiwal, Sargodha), FSD's
#     Computer Science / Agriculture / Dars-e-Nazami / Fashion Designing,
#     and every Total / Grand Total rollup — including Kohat's
#     "Grand Total (Science + General)" which is exactly the
#     Science+Humanities sum and would double-count.
# ---------------------------------------------------------------------------


def _canon_group(text) -> str | None:
    """Raw group label -> 'Science' / 'Humanities', or None when the row
    is a rollup / special group that this page does not chart."""
    key = str(text).strip().lower().replace(" group", "").strip()
    return {
        "science": "Science",
        "humanities": "Humanities",
        "humanities (general)": "Humanities",
        "arts": "Humanities",
        "general": "Humanities",
    }.get(key)


def _canon_rows(df: pd.DataFrame, group_col: str, appeared_col: str,
                passed_col: str) -> list[dict]:
    """Maps a long-format sheet's detail rows to canonical group records."""
    recs = []
    for _, r in df.iterrows():
        g = _canon_group(r[group_col])
        if g is not None:
            recs.append({"Year": int(r["Year"]), "Group": g,
                         "Appeared": float(r[appeared_col]),
                         "Passed": float(r[passed_col])})
    return recs


def _group_rows_abbottabad():
    # Abbottabad-Group Wise Pass %: Year | Candidate Type (Regular
    # Female/Male) | Group ('Science'/'Arts'). All rows are details.
    df = _clean(load_sheet("Abbottabad-Group Wise Pass %"), ["Appeared", "Passed"])
    return _canon_rows(df, "Group", "Appeared", "Passed")


def _group_rows_bahawalpur():
    # Bahawalpur-General Pass Percent: Year | Category | Group |
    # Gender ('Male'/'Female'/'Total'). Take the Gender='Total' rows of
    # the three real categories (Total (Regular)/Grand Total category
    # rollups dropped) — group detail covers 101,680 of the board's
    # 105,601 (2026); 3,921 candidates are unclassified in the gazette.
    df = _clean(load_sheet("Bahawalpur-General Pass Percent"), ["Appeared", "Passed"])
    df = df[df["Category"].isin(["Regular (Govt.)", "Regular (Affiliated)", "Private"])]
    df = df[df["Gender"] == "Total"]
    return _canon_rows(df, "Group", "Appeared", "Passed")


def _group_rows_bannu():
    # Bannu-Result at a Glance: Year | Group ('Science'/'Humanities'/
    # 'Grand Total') | Category ('Regular (Boys)', ..., 'Sub Total').
    # Keep ONLY the four candidate-detail rows — each group also has a
    # 'Sub Total' row (its exact sum; keeping it would double-count).
    # Detail rows cover the whole board (verified vs Overall Summary).
    df = _clean(load_sheet("Bannu-Result at a Glance"), ["Appeared", "Passed"])
    df = df[~df["Category"].astype(str).str.strip().str.lower().isin(["sub total"])]
    return _canon_rows(df, "Group", "Appeared", "Passed")


def _group_rows_dgk():
    # DGK-Group Wise Male Female: Year | Group ('Science'/'General') |
    # Gender | Appeared | Passed. This table reconciles EXACTLY with the
    # board's Overall Summary rows for both years (appeared 105,854 /
    # 106,001 and passed 60,698 / 51,081) — i.e. it covers 100% of DGK's
    # candidates. Its Regular/Private table uses a different, non-
    # reconciling group taxonomy and is deliberately NOT used here.
    df = _clean(load_sheet("DGK-Group Wise Male Female"), ["Appeared", "Passed"])
    return _canon_rows(df, "Group", "Appeared", "Passed")


def _group_rows_fbise():
    # FBISE-Group Wise Pass %: Year | Candidate Type | Group | Gender |
    # Enrolled | Absent | Appeared | ... | Pass. Keep Gender detail rows
    # (drop Gender='Total' and the Group 'Total'/'Grand Total' rollups);
    # Candidate Type spans Regular + Ex/Private — both summed.
    df = _clean(load_sheet("FBISE-Group Wise Pass %"), ["Appeared", "Pass"])
    df = df[df["Gender"].astype(str).str.strip() != "Total"]
    return _canon_rows(df, "Group", "Appeared", "Pass")


def _group_rows_fsd():
    # FSD-Overall Statistical Data: Year | Category ('Regular'/'Private')
    # | Group. The 'Overall Private/Regular Candidates' rows are board
    # rollups and drop out via the canon map; FSD's applied groups
    # (Computer Science, Agriculture, Dars-e-Nazami, Fashion Designing,
    # Deaf & Defective) are excluded by design.
    df = _clean(load_sheet("FSD-Overall Statistical Data"), ["Appeared", "Pass"])
    return _canon_rows(df, "Group", "Appeared", "Pass")


def _group_rows_gujranwala():
    # Gujranwala-Group Wise Pass %: Year | Group ('Science'/'General'/
    # 'Deaf & Dumb') | Category ('Regular'/'Private'/'Grand Total') |
    # Gender ('Male'/'Female'/'Sub Total'). Keep the category/gender
    # detail rows; the separate Tech sheet is out of scope.
    df = _clean(load_sheet("Gujranwala-Group Wise Pass %"), ["Appeared", "Passed"])
    df = df[df["Category"].isin(["Regular", "Private"])]
    df = df[df["Gender"].astype(str).str.strip() != "Sub Total"]
    return _canon_rows(df, "Group", "Appeared", "Passed")


def _group_rows_kohat():
    # Kohat: two sheets. Each carries Regular (Boys/Girls) [+ Private]
    # detail rows and a 'Total' row; the General sheet additionally has
    # 'Grand Total (Science + General)' — the Science+General sum, which
    # must never be included. Take each sheet's own 'Total' rows.
    recs = []
    sci = _clean(load_sheet("Kohat-Science Group"), ["Appeared", "Passed"])
    for _, r in sci[sci["Category"] == "Total"].iterrows():
        recs.append({"Year": int(r["Year"]), "Group": "Science",
                     "Appeared": float(r["Appeared"]), "Passed": float(r["Passed"])})
    gen = _clean(load_sheet("Kohat-General Group"), ["Appeared", "Passed"])
    for _, r in gen[gen["Category"] == "Total"].iterrows():
        recs.append({"Year": int(r["Year"]), "Group": "Humanities",
                     "Appeared": float(r["Appeared"]), "Passed": float(r["Passed"])})
    return recs


def _group_rows_lahore():
    # Lahore: two wide Metric-row sheets (Science / Humanities; the Tech
    # sheet is out of scope). 'Total (Boys+Girls)' is the group total —
    # one value per Year x Metric.
    recs = []
    for sheet, group in (("Lahore-Science Group", "Science"),
                         ("Lahore-Humanities Group", "Humanities")):
        df = _clean(load_sheet(sheet), ["Total (Boys+Girls)"])
        for year in (2025, 2026):
            y = df[df["Year"] == year]
            app = y[y["Metric"] == "Appeared"]["Total (Boys+Girls)"]
            pas = y[y["Metric"] == "Passed"]["Total (Boys+Girls)"]
            if not app.empty and not pas.empty:
                recs.append({"Year": year, "Group": group,
                             "Appeared": float(app.iloc[0]), "Passed": float(pas.iloc[0])})
    return recs


def _group_rows_mardan():
    # Mardan: two sheets (Science / Humanities), columns 'Total
    # Candidates' / 'Promoted Candidates'. Promoted convention (see
    # availability.PROMOTED_TERMINOLOGY_BOARDS): Appeared := Total
    # Candidates, Passed := Promoted Candidates. Drop the 'TOTAL'
    # category rollups.
    recs = []
    for sheet, group in (("Mardan-Science Group", "Science"),
                         ("Mardan-Humanities Group", "Humanities")):
        df = _clean(load_sheet(sheet), ["Total Candidates", "Promoted Candidates"])
        df = df[~df["Category"].astype(str).str.upper().str.contains("TOTAL")]
        for _, r in df.iterrows():
            recs.append({"Year": int(r["Year"]), "Group": group,
                         "Appeared": float(r["Total Candidates"]),
                         "Passed": float(r["Promoted Candidates"])})
    return recs


def _group_rows_peshawar():
    # Peshawar-Group Wise Distributio: Year | Category ('Regular
    # (Female)', ..., 'Private (Male)') | Group ('Science'/'Arts') |
    # Total Students | Passed | Promoted. Peshawar's convention: Passed
    # := Passed + Promoted (matches its Overall Summary rows).
    df = _clean(load_sheet("Peshawar-Group Wise Distributio"),
                ["Total Students", "Passed", "Promoted"])
    recs = []
    for _, r in df.iterrows():
        g = _canon_group(r["Group"])          # 'Arts' -> Humanities
        if g is not None:
            recs.append({"Year": int(r["Year"]), "Group": g,
                         "Appeared": float(r["Total Students"]),
                         "Passed": float(r["Passed"] + r["Promoted"])})
    return recs


def _group_rows_rawalpindi():
    # Rawalpindi-Group Wise Pass %: Year | Candidate Type ('Regular'/
    # 'Private'/'Overall' — Overall rows are rollups) | Group | Gender
    # | Appeared | Pass | Pass %.
    #
    # HEADER QUIRK (verified): the sheet's Gender column has a blank
    # header cell, so load_sheet's columns come back shifted — the
    # gender values sit in the column NAMED 'Appeared', the appeared
    # counts in 'Pass', and the passed counts in 'Pass %'. Read the
    # value columns BY POSITION, never by name.
    #
    # The humanities group is named 'Humanities' in 2026 and 'Humanities
    # (General)' in 2025 — the same group, renamed between gazettes
    # (verified: both years have exactly Science + one humanities group,
    # and Regular+Private sums reproduce the 'Overall' rows). Gender
    # 'Total' rows dropped; M+F details summed.
    raw = load_sheet("Rawalpindi-Group Wise Pass %")
    gender_col, appeared_col, passed_col = raw.columns[3], raw.columns[4], raw.columns[5]
    df = _clean(raw, [appeared_col, passed_col])
    df = df[df["Candidate Type"].isin(["Regular", "Private"])]
    df = df[df[gender_col].astype(str).str.strip() != "Total"]
    recs = []
    for _, r in df.iterrows():
        g = _canon_group(r["Group"])
        if g is not None:
            recs.append({"Year": int(r["Year"]), "Group": g,
                         "Appeared": float(r[appeared_col]),
                         "Passed": float(r[passed_col])})
    return recs


def _group_rows_sahiwal():
    # Sahiwal-Group Wise Pass %: Year | Candidate Type ('Regular'/
    # 'Private'/'Overall' — Overall is the Reg+Pvt rollup, dropped) |
    # Group ('Science'/'General'/Deaf & Dumb/Matric-Tech x4/'TOTAL') |
    # Gender | Appeared | Pass. Gender='Total' and the group-'TOTAL'
    # rollups drop out too; Deaf & Dumb and the Matric-Tech streams are
    # out of scope.
    df = _clean(load_sheet("Sahiwal-Group Wise Pass %"), ["Appeared", "Pass"])
    df = df[df["Candidate Type"].isin(["Regular", "Private"])]
    df = df[df["Gender"].astype(str).str.strip() != "Total"]
    return _canon_rows(df, "Group", "Appeared", "Pass")


def _group_rows_sargodha():
    # Sargodha-Group Wise Pass %: same shape as Sahiwal ('Science Group'/
    # 'Humanities Group'/'Deaf and Dumb Group'/'Matric-Tech (...) Group'/
    # 'Total'), Candidate Type likewise carries an 'Overall' rollup.
    df = _clean(load_sheet("Sargodha-Group Wise Pass %"), ["Appeared", "Pass"])
    df = df[df["Candidate Type"].isin(["Regular", "Private"])]
    df = df[df["Gender"].astype(str).str.strip() != "Total"]
    return _canon_rows(df, "Group", "Appeared", "Pass")


def _group_rows_swat():
    # Swat-Group Wise Pass %: Year (2026 ONLY — no 2025 gazette) | Group
    # ('Science Group'/'Humanities Group'/'Grand Total') | Category
    # ('Regular (Boys)', ..., 'Sub Total'). Detail rows only; Swat
    # simply has no 2025 group data — nothing is invented.
    df = _clean(load_sheet("Swat-Group Wise Pass %"), ["Appeared", "Passed"])
    df = df[df["Category"].isin(
        ["Regular (Boys)", "Regular (Girls)", "Private (Boys)", "Private (Girls)"]
    )]
    return _canon_rows(df, "Group", "Appeared", "Passed")


# Board order follows config.settings.ALL_BOARDS.
_GROUP_EXTRACTORS = {
    "Abbottabad": _group_rows_abbottabad,
    "Bahawalpur": _group_rows_bahawalpur,
    "Bannu": _group_rows_bannu,
    "DGK": _group_rows_dgk,
    "FBISE": _group_rows_fbise,
    "FSD": _group_rows_fsd,
    "Gujranwala": _group_rows_gujranwala,
    "Kohat": _group_rows_kohat,
    "Lahore": _group_rows_lahore,
    "Mardan": _group_rows_mardan,
    "Peshawar": _group_rows_peshawar,
    "Rawalpindi": _group_rows_rawalpindi,
    "Sahiwal": _group_rows_sahiwal,
    "Sargodha": _group_rows_sargodha,
    "Swat": _group_rows_swat,
}


def _build_group_table() -> pd.DataFrame:
    """Runs every board's group extractor, stacks the detail rows,
    aggregates per Board x Year x Group and recomputes
    Pass % = Passed / Appeared."""
    frames = []
    for board, extractor in _GROUP_EXTRACTORS.items():
        recs = extractor()
        if not recs:
            continue
        df = pd.DataFrame(recs)
        df.insert(0, "Board", board)
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["Board", "Year", "Group", "Appeared", "Passed", "Pass %"])
    df = pd.concat(frames, ignore_index=True)
    df = _aggregate(df, ["Board", "Year", "Group"])
    df["Pass %"] = (df["Passed"] / df["Appeared"]).where(df["Appeared"] > 0)
    return df.sort_values(["Board", "Year", "Group"]).reset_index(drop=True)


@st.cache_data(show_spinner="Loading group data...")
def load_group_table() -> pd.DataFrame:
    """All 15 boards' Science vs Humanities breakdown, normalized
    ('Arts'/'General' -> Humanities; tech/special groups out of scope —
    see the group section comment and the Group Wise page's footnote)."""
    return _build_group_table()

# ---------------------------------------------------------------------------
# Subject-wise table — Board | Year | Subject | Appeared | Passed | Pass %
# ---------------------------------------------------------------------------
# 12 of 15 boards publish a subject-wise pass-percentage table. Bannu,
# Mardan, and Sahiwal do not (see availability.SUBJECT_AVAILABLE_BOARDS).
#
# Each board's sheet has a different layout — some have Regular/Private
# columns (DGK, Lahore, FBISE), some have grade breakdowns (Sargodha),
# some have title/note rows before the header (Lahore, Kohat, Peshawar,
# Rawalpindi, Gujranwala). Each extractor below handles its board's
# specific layout.
#
# NaN rows are excluded — they represent curriculum-gap subjects (Tech
# subjects in 2026 only, Old Course subjects in 2025 only for Bahawalpur).
# These are NOT parsing errors; the data genuinely does not exist for
# that year.
#
# Normalization: case/hyphen/spacing only. Meaningful suffixes like
# "(NEW COURSE)" and "(TECH)" are PRESERVED — stripping them would
# accidentally merge Bahawalpur's Old and New Course subjects in the
# heatmap, violating the Q2 decision to keep them separate.
#
# Pass % is recomputed as Passed / Appeared (never taken from the sheet
# directly) to ensure consistent fraction formatting across boards.
#
# VALIDATION (3-tier sanity check, since subject data will NOT 1:1 match
# Overall Summary — one candidate takes multiple subjects):
#   1. Each subject's Appeared <= Board's Total Appeared (sanity bound)
#   2. All Pass % values in [0, 1] (no invalid percentages)
#   3. Manual spot-check: 2-3 subject numbers match source sheet
#
# Spot-check anchors (verified against source sheets):
#   - Abbottabad 2025: ARABIC Appeared=379, Passed=332, Pass%=87.6%
#   - Bahawalpur 2026: BIOLOGY-I (NEW COURSE) Appeared=44311, Passed=30744
#   - DGK 2025: BIOLOGY Regular Appeared=59068, Regular Passed=45636


def _canon_subject(name: str) -> str:
    """Normalize subject name: standardize case, hyphen, spacing.
    Does NOT strip meaningful suffixes like (NEW COURSE) or (TECH)."""
    if not isinstance(name, str):
        return str(name)
    s = name.strip()
    # Standardize to title case
    s = s.title()
    # Normalize hyphens: " - " -> "-", "- " -> "-", " -" -> "-"
    s = s.replace(" - ", "-").replace(" -", "-").replace("-", "-")
    # Normalize spacing around parentheses
    s = s.replace("( ", "(").replace(" )", ")")
    # Collapse multiple spaces
    s = " ".join(s.split())
    return s


def _subject_rows_abbottabad() -> list[dict]:
    """Abbottabad: header row 0, data from row 1.
    Columns: Subject, Year, Total Students, Passed, Pass %age"""
    df = pd.read_excel(xl, sheet_name="Abbottabad-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Total Students"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Total Students"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_bahawalpur() -> list[dict]:
    """Bahawalpur: header row 0, data from row 1.
    Columns: Subject, Year, Appeared, Passed, Pass %age.
    Old/New Course subjects are kept separate (not merged)."""
    df = pd.read_excel(xl, sheet_name="Bahawalpur-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_dgk() -> list[dict]:
    """DGK: header row 0, data from row 1.
    Columns: Year, Subject, Regular Appeared, Regular Passed, Regular Pass %,
    Private Appeared, Private Passed, Private Pass %.
    Regular and Private are summed to get total per subject."""
    df = pd.read_excel(xl, sheet_name="DGK-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    records = []
    for _, row in df.iterrows():
        reg_app = pd.to_numeric(row["Regular Appeared"], errors="coerce")
        reg_pass = pd.to_numeric(row["Regular Passed"], errors="coerce")
        pvt_app = pd.to_numeric(row["Private Appeared"], errors="coerce")
        pvt_pass = pd.to_numeric(row["Private Passed"], errors="coerce")
        appeared = (0 if pd.isna(reg_app) else reg_app) + (0 if pd.isna(pvt_app) else pvt_app)
        passed = (0 if pd.isna(reg_pass) else reg_pass) + (0 if pd.isna(pvt_pass) else pvt_pass)
        if appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_fbise() -> list[dict]:
    """FBISE: header row 0, data from row 1.
    Columns: Subject Name, Year, S.No, Appeared - Regular, Appeared - Ex/Private,
    Appeared - Total, Passed - Regular, Passed - Ex/Private, Passed - Total,
    Pass % - Regular, Pass % - Ex/Private, Pass % - Total.
    Uses Total columns."""
    df = pd.read_excel(xl, sheet_name="FBISE-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject Name", "Year"])
    df = df[df["Subject Name"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared - Total"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared - Total"], errors="coerce")
        passed = pd.to_numeric(row["Passed - Total"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject Name"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_fsd() -> list[dict]:
    """FSD: two sheets (Regular + Private), header row 0, data from row 1.
    Columns: Year, Subject, Enroll, Absent, Appeared, Passed, Pass %.
    Both sheets are combined."""
    records = []
    for sheet_name in ["FSD-Subject Wise Pass % (Regula", "FSD-Subject Wise Pass % (Privat"]:
        df = pd.read_excel(xl, sheet_name=sheet_name, header=0)
        df = df.dropna(subset=["Subject", "Year"])
        df = df[df["Subject"].astype(str).str.strip() != ""]
        df = df.dropna(subset=["Appeared"])
        for _, row in df.iterrows():
            appeared = pd.to_numeric(row["Appeared"], errors="coerce")
            passed = pd.to_numeric(row["Passed"], errors="coerce")
            if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
                continue
            records.append({
                "Year": int(row["Year"]),
                "Subject": _canon_subject(str(row["Subject"])),
                "Appeared": int(appeared),
                "Passed": int(passed),
            })
    return records


def _subject_rows_gujranwala() -> list[dict]:
    """Gujranwala: title row 0, note row 1, header row 2, data from row 3.
    Columns: Year, Subject Name, Appeared, Passed, Pass %.
    Only 2025 data published (2026 gazette did not include this table)."""
    df = pd.read_excel(xl, sheet_name="Gujranwala-Subject Wise Pass %", header=2)
    df = df.dropna(subset=["Subject Name", "Year"])
    df = df[df["Subject Name"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject Name"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_kohat() -> list[dict]:
    """Kohat: title row 0, blank row 1, header row 2, data from row 3.
    Columns: Subject, Year, Appeared, Passed, Pass %."""
    df = pd.read_excel(xl, sheet_name="Kohat-Subject Wise Pass %", header=2)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_lahore() -> list[dict]:
    """Lahore: title row 0, blank row 1, header row 2, data from row 3.
    Columns: Subject (Theory/Practical), Year, Regular Appeared, Regular Passed,
    Regular Pass %, Private Appeared, Private Passed, Private Pass %,
    Overall Appeared, Overall Passed, Overall Pass %.
    Uses Overall columns."""
    df = pd.read_excel(xl, sheet_name="Lahore-Subject Wise Pass %", header=2)
    df = df.dropna(subset=["Subject (Theory/Practical)", "Year"])
    df = df[df["Subject (Theory/Practical)"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Overall Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Overall Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Overall Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject (Theory/Practical)"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_peshawar() -> list[dict]:
    """Peshawar: title row 0, blank row 1, header row 2, data from row 3.
    Columns: Subject, Year, Appeared, Passed, Pass %."""
    df = pd.read_excel(xl, sheet_name="Peshawar-Subject Wise Pass %", header=2)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_rawalpindi() -> list[dict]:
    """Rawalpindi: title row 0, note row 1, header row 2, data from row 3.
    Columns: Subject, Year, Appeared, Passed, Pass %.
    Some subjects have "- Small Cohort (Tech)" suffix — preserved."""
    df = pd.read_excel(xl, sheet_name="Rawalpindi-Subject Wise Pass %", header=2)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_sargodha() -> list[dict]:
    """Sargodha: header row 0, data from row 1.
    Columns: Subject Code, Subject Name, Year, Total, Absent, Appeared,
    A+, A, B, C, D, E, F, Pass, Pass %.
    Uses Subject Name, Appeared, Pass columns."""
    df = pd.read_excel(xl, sheet_name="Sargodha-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject Name", "Year"])
    df = df[df["Subject Name"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Pass"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject Name"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


def _subject_rows_swat() -> list[dict]:
    """Swat: header row 0, data from row 1.
    Columns: Year, Subject, Abbreviation, Appeared, Passed, Pass %.
    Swat has only 2026 gazette."""
    df = pd.read_excel(xl, sheet_name="Swat-Subject Wise Pass %", header=0)
    df = df.dropna(subset=["Subject", "Year"])
    df = df[df["Subject"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["Appeared"])
    records = []
    for _, row in df.iterrows():
        appeared = pd.to_numeric(row["Appeared"], errors="coerce")
        passed = pd.to_numeric(row["Passed"], errors="coerce")
        if pd.isna(appeared) or pd.isna(passed) or appeared <= 0:
            continue
        records.append({
            "Year": int(row["Year"]),
            "Subject": _canon_subject(str(row["Subject"])),
            "Appeared": int(appeared),
            "Passed": int(passed),
        })
    return records


_SUBJECT_EXTRACTORS = {
    "Abbottabad": _subject_rows_abbottabad,
    "Bahawalpur": _subject_rows_bahawalpur,
    "DGK": _subject_rows_dgk,
    "FBISE": _subject_rows_fbise,
    "FSD": _subject_rows_fsd,
    "Gujranwala": _subject_rows_gujranwala,
    "Kohat": _subject_rows_kohat,
    "Lahore": _subject_rows_lahore,
    "Peshawar": _subject_rows_peshawar,
    "Rawalpindi": _subject_rows_rawalpindi,
    "Sargodha": _subject_rows_sargodha,
    "Swat": _subject_rows_swat,
}


def _build_subject_table() -> pd.DataFrame:
    """Runs every board's subject extractor, stacks the detail rows,
    aggregates per Board x Year x Subject and recomputes
    Pass % = Passed / Appeared."""
    import streamlit as st
    global xl
    xl = pd.ExcelFile("data/BISE_9th_MASTER_2025-2026.xlsx")
    frames = []
    for board, extractor in _SUBJECT_EXTRACTORS.items():
        recs = extractor()
        if not recs:
            continue
        df = pd.DataFrame(recs)
        df.insert(0, "Board", board)
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["Board", "Year", "Subject", "Appeared", "Passed", "Pass %"])
    df = pd.concat(frames, ignore_index=True)
    df = _aggregate(df, ["Board", "Year", "Subject"])
    df["Pass %"] = (df["Passed"] / df["Appeared"]).where(df["Appeared"] > 0)
    return df.sort_values(["Board", "Year", "Subject"]).reset_index(drop=True)


@st.cache_data(show_spinner="Loading subject data...")
def load_subject_table() -> pd.DataFrame:
    """12 boards' subject-wise pass percentage, normalized.
    Columns: Board | Year | Subject | Appeared | Passed | Pass %.
    NaN rows excluded (curriculum-gap subjects). Old/New Course subjects
    kept separate. Pass % recomputed as Passed / Appeared."""
    return _build_subject_table()
