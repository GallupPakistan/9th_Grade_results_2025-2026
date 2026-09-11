"""
data/verify_recipes.py

Data-integrity gate for data/recipes.py: re-extracts every board's
gender and Regular/Private rows, sums them per board/year, and
cross-checks the sums against the Overall Summary sheet's Appeared /
Passed totals — the same numbers the whole dashboard is built on.

Run from the project root whenever the master workbook changes:

    python data/verify_recipes.py

Expected result:
  * Category table: all 15 boards match Overall Summary exactly.
  * Gender table: all boards match except the two documented cases —
    FSD (publishes no gender breakdown at all) and Bahawalpur 2026
    (the gazette leaves 3,921 candidates unclassified by gender; see
    the note in data/recipes.py). Nothing is invented to force a match.
"""

import pandas as pd

from data.recipes import load_gender_table, load_category_table
from data.loader import load_overall_summary


def main() -> None:
    overall = load_overall_summary()
    overall = overall[overall["Year"].isin([2025, 2026])].copy()
    overall["Appeared"] = pd.to_numeric(overall["Appeared"], errors="coerce")
    overall["Passed"] = pd.to_numeric(overall["Passed"], errors="coerce")

    gender = load_gender_table()
    category = load_category_table()

    print(f"{'Board':<12} {'Yr':<5} | {'Overall App':>11} {'Passed':>9} | "
          f"{'G-App':>9} {'G-Pass':>9} {'dA':>6} {'dP':>6} {'':8} | "
          f"{'C-App':>9} {'C-Pass':>9} {'dA':>6} {'dP':>6}")
    print("-" * 120)

    failures = []
    for board in overall["Board"].unique():
        for year in (2025, 2026):
            o = overall[(overall["Board"] == board) & (overall["Year"] == year)]
            if o.empty or pd.isna(o["Appeared"].iloc[0]):
                print(f"{board:<12} {year:<5} | (no Overall Summary data)")
                continue
            oa, op = int(o["Appeared"].iloc[0]), int(o["Passed"].iloc[0])

            g = gender[(gender["Board"] == board) & (gender["Year"] == year)]
            ga = int(g["Appeared"].sum()) if not g.empty else 0
            gp = int(g["Passed"].sum()) if not g.empty else 0

            c = category[(category["Board"] == board) & (category["Year"] == year)]
            ca = int(c["Appeared"].sum()) if not c.empty else 0
            cp = int(c["Passed"].sum()) if not c.empty else 0

            g_ok = (ga, gp) == (oa, op)
            c_ok = (ca, cp) == (oa, op)
            if not g_ok:
                failures.append(f"gender {board} {year}")
            if not c_ok:
                failures.append(f"category {board} {year}")
            print(f"{board:<12} {year:<5} | {oa:>11} {op:>9} | "
                  f"{ga:>9} {gp:>9} {ga-oa:>6} {gp-op:>6} {'OK' if g_ok else 'MISMATCH':8} | "
                  f"{ca:>9} {cp:>9} {ca-oa:>6} {cp-op:>6} {'OK' if c_ok else 'MISMATCH'}")
        print()

    print("=" * 120)
    if failures:
        print("MISMATCHES (must be documented in data/recipes.py or fixed):")
        for f in failures:
            print(f"  - {f}")
    else:
        print("ALL BOARDS MATCH Overall Summary EXACTLY.")


if __name__ == "__main__":
    main()