"""
data/recipes.py

Per-board "extraction recipes" that turn each board's idiosyncratic
sheet layout(s) in the master workbook into two normalized long-format
tables, used by the Overview page (and reusable by the dedicated Gender
/ Regular-vs-Private pages later):

  load_gender_table()    ->  Board | Year | Gender   | Appeared | Passed | Pass %
  load_category_table()  ->  Board | Year | Category | Appeared | Passed | Pass %

Gender is always "Male"/"Female"; Category is always "Regular"/"Private".
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