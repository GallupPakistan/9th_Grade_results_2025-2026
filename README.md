# 9th Class Result Analytics Dashboard

## Folder structure

```
9th_dashboard/
├── app.py                     # entry point (Overview page) — run this with `streamlit run app.py`
├── requirements.txt
├── data/
│   ├── BISE_9th_MASTER_2025-2026.xlsx   # <- the master workbook (place it here)
│   ├── loader.py                # ALL Excel reading happens here (cached)
│   ├── recipes.py               # per-board verified gender & Regular/Private extraction tables
│   ├── verify_recipes.py        # integrity gate: re-checks recipes vs Overall Summary (`python data/verify_recipes.py`)
│   └── availability.py          # which boards have gender/district/grade/trend data
├── config/
│   └── settings.py              # app name, icon, board lists — edit here to re-brand
├── styles/
│   ├── theme.py                 # COLORS + FONTS — edit here to re-theme the whole app
│   └── css.py                   # builds & injects all CSS from theme.py values
├── components/
│   ├── topbar.py                 # the navy header card (title/breadcrumb/stat badge)
│   ├── sidebar.py                 # custom branded nav — edit NAV_SECTIONS to add pages
│   ├── kpi_card.py                 # reusable KPI "glass card"
│   ├── chart_card.py                # reusable titled card wrapper for Plotly charts
│   └── filters.py                   # board/year selectors, restricted to available boards
├── charts/
│   ├── overview_charts.py            # one file per page, one function per chart
│   ├── comparison_charts.py
│   ├── gender_charts.py
│   ├── group_charts.py
│   ├── regular_private_charts.py
│   ├── subject_charts.py
│   ├── district_charts.py
│   └── grade_charts.py
└── pages/
    ├── 1_Overview.py
    ├── 2_Board_Comparison.py
    ├── 3_Gender_Analysis.py
    ├── 4_Group_Wise.py
    ├── 5_Regular_vs_Private.py
    ├── 6_Subject_Wise.py
    ├── 7_District_Wise.py
    └── 8_Grade_Distribution.py
```

## Where to make changes

| I want to change...                          | Edit ONLY this file            |
|-----------------------------------------------|---------------------------------|
| Colors / fonts for the whole app              | `styles/theme.py`               |
| App name, icon, "last updated" date           | `config/settings.py`            |
| Which boards appear in a gender/district/etc. filter | `data/availability.py`   |
| How a board's gender / Regular-Private data is read  | `data/recipes.py` (then re-run `python data/verify_recipes.py`) |
| The header/topbar look                        | `components/topbar.py` (structure) + `styles/css.py` (`_topbar_css`) |
| A KPI card's look                             | `components/kpi_card.py` + `styles/css.py` (`_kpi_card_css`) |
| Sidebar nav links / order                     | `components/sidebar.py` (`NAV_SECTIONS`) |
| A specific chart                              | its function inside `charts/<page>_charts.py` |
| A page's layout / which charts appear         | `pages/N_PageName.py`           |

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Status

Foundation files (config, styles, topbar, sidebar, kpi_card, chart_card,
filters, loader, availability, recipes) are complete and working.

- **Overview page (pages/1_Overview.py) is fully built**: KPI row, Top
  Gainer/Decliner callouts, and 8 charts (YoY totals, board pass %, YoY
  change, appeared share, gender pass %, gender share, Regular-vs-Private
  pass %, Reg/Pvt share) — all reactive to the Province filter.
- `data/recipes.py` normalizes every board's gender & Regular/Private
  data into two tables; every board/year sum was cross-checked against
  the Overall Summary sheet via `python data/verify_recipes.py`
  (category: 15/15 exact; gender: all match except FSD — no gender data
  published — and Bahawalpur 2026, where the gazette itself leaves 3,921
  candidates unclassified by gender; nothing is invented to force a match).
- Remaining page files and chart files are stubs with `TODO` markers —
  we're filling these in one page at a time.
