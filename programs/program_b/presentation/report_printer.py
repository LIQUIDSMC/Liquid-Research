"""
Program B — Market Microstructure Research
Report Printer
programs/program_b/presentation/report_printer.py

PURPOSE:
Minimal presentation layer. Formats existing analysis output into
simple, fixed-width plain text tables for terminal display. This
module contains NO analysis logic — it only formats dicts already
produced by programs/program_b/analysis/*.

This module does NOT:
- modify any analysis module or its return values
- add colors, charts, or any visual styling beyond plain text
- add thresholds, classifications, or stable/unstable labels
- build a dashboard (that remains Phase 4, not started)

Rounding to 4 decimals happens here, for DISPLAY ONLY. The
underlying analysis dicts are never modified — this module reads
them and produces a formatted string, nothing else.
"""


def _format_value(value, decimals: int = 4) -> str:
    """
    Format a single numeric value for display, or return an
    em-dash if the value is None/missing.

    Receives:
        value (float or None): the raw value from an analysis dict.
        decimals (int): number of decimal places to round to for
        display (default 4).

    Returns:
        str: formatted number, or "—" if value is None.
    """
    if value is None:
        return "—"
    return f"{float(value):.{decimals}f}"


def format_stability_table(stability_section: dict) -> str:
    """
    Format a stability section dict (from track_stability() or
    build_market_report()["stability"]) into a fixed-width plain
    text table.

    Receives:
        stability_section (dict): must contain keys "obi",
        "near_obi", "midpoint_obi_source", "midpoint_near_source",
        each itself a dict with count/mean/min/max/range/stddev/latest.

    Returns:
        str: a fixed-width plain text table, e.g.:

            Indicator          Count    Mean      SD      Latest
            ----------------------------------------------------
            OBI                  3     -0.3812   0.0148  -0.3643
            Near OBI             1      0.9916     —      0.9916
            Midpoint (OBI)       3      0.1052   0.0167   0.1245
            Midpoint (Near)      1      0.1245     —      0.1245
    """
    rows = [
        ("OBI", stability_section.get("obi", {})),
        ("Near OBI", stability_section.get("near_obi", {})),
        ("Midpoint (OBI)", stability_section.get("midpoint_obi_source", {})),
        ("Midpoint (Near)", stability_section.get("midpoint_near_source", {})),
    ]

    header = f"{'Indicator':<18}{'Count':>7}{'Mean':>10}{'SD':>9}{'Latest':>9}"
    separator = "-" * len(header)

    lines = [header, separator]

    for label, section in rows:
        count = section.get("count", 0)
        mean_str = _format_value(section.get("mean"))
        sd_str = _format_value(section.get("stddev"))
        latest_str = _format_value(section.get("latest"))

        line = f"{label:<18}{count:>7}{mean_str:>10}{sd_str:>9}{latest_str:>9}"
        lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

    from programs.program_b.analysis.market_report import build_market_report

    report = build_market_report("will-the-fed-increase-interest-rates-by-25-bps-after-the-july-2026-meeting")
    print(format_stability_table(report["stability"]))