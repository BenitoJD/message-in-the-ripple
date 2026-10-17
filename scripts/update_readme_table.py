"""Regenerate the results table in README.md from the committed metrics files.

Reads results/*/metrics.json and rewrites the block between the
<!--RESULTS--> markers. Keeps the README's numbers tied to the artifacts
instead of to hand-copied digits.

Run:  .venv/bin/python scripts/update_readme_table.py
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
README = ROOT / "README.md"
MARK = "<!--RESULTS-->"

ORDER = ["flower8", "flower", "outline_gap20", "outline", "ink", "coarse16", "coarse8", "coarse8_strong"]
TITLES = {
    "flower8": "**8-petal flower** outline, 32x32 actuators",
    "flower": "**6-petal flower** outline, 32x32 actuators",
    "outline_gap20": "heart **outline**, 32x32 actuators, 20 cm throw",
    "outline": "heart **outline**, 32x32 actuators, 12 cm throw",
    "ink": "filled heart, 32x32 actuators",
    "coarse16": "filled heart, 16x16 actuators",
    "coarse8": "filled heart, 8x8 actuators",
    "coarse8_strong": "filled heart, 8x8, contrast penalty x10",
}


def load(tag: str) -> dict | None:
    p = RESULTS / tag / "metrics.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> None:
    rows = []
    for tag in ORDER:
        m = load(tag)
        if m is None:
            print(f"missing: results/{tag}/metrics.json (skipped)")
            continue
        n = m["params"]["n_coarse"]
        rows.append(
            "| {title} | {act} | {corr:+.3f} | {con:.1%} | {chi:.2f} | {imp:+.3f} | {win:.0f} ms |".format(
                title=TITLES.get(tag, tag),
                act=f"{n}x{n} ({n * n})",
                corr=m["corr_at_tstar_exact"],
                con=m.get("contrast_at_tstar", float("nan")),
                chi=m.get("chi_at_tstar", float("nan")),
                imp=m["corr_at_t0_imprint_only"],
                win=m["legible_window_ms"],
            )
        )

    refs = []
    for tag, label in (("static", "filled heart"), ("static_outline", "heart outline"), ("flower_static", "flower outline")):
        f = RESULTS / tag / "static_metrics.json"
        if f.exists():
            sm = json.loads(f.read_text())
            refs.append(
                f"| *(stage A reference, {label}: no wave constraint)* | - | {sm['corr']:+.3f} | "
                f"{sm['contrast']:.1%} | {sm['chi']:.2f} | - | - |"
            )
    static_line = (
        "\nStage A (the same optics with the surface free to be anything, no wave dynamics) "
        "is the ceiling to compare against — a stage C row is only interesting if it "
        "approaches its own target's reference.\n"
    )

    table = (
        "| run | actuators | corr @ t* | contrast | chi | imprint-only corr | legible window |\n"
        "|---|---|---|---|---|---|---|\n" + "\n".join(rows + refs) + "\n" + static_line
    )

    text = README.read_text()
    if MARK not in text:
        print(f"marker {MARK} not found in README.md", file=sys.stderr)
        sys.exit(1)
    parts = text.split(MARK)
    if len(parts) == 2:  # single placeholder: expand it into a marker pair
        README.write_text(parts[0] + MARK + "\n" + table + MARK + parts[1])
    elif len(parts) == 3:  # already expanded: replace the block
        README.write_text(parts[0] + MARK + "\n" + table + MARK + parts[2])
    else:
        print(f"expected 1 or 2 occurrences of {MARK}, found {len(parts) - 1}", file=sys.stderr)
        sys.exit(1)
    print(f"README table updated with {len(rows)} runs")


if __name__ == "__main__":
    main()
