import re
import warnings
import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.ticker as ticker
from scipy.stats import gaussian_kde


from nexus.md.analyze.generate_analysis_figures import (
    _apply_base_style,
    _DISC_COLORS,
    _smart_ylim,
    _rolling,
    _rolling_std,
    _savefig,
    _frames_to_ns,
)
_apply_base_style()


def _bar_ylim(ax: "plt.Axes", vals: list, errs: list | None = None,
              margin: float = 0.25) -> None:
    """Set y-limits for a bar chart, using data range rather than axis lines."""
    finite = [v for v in vals if np.isfinite(v)]
    if not finite:
        return
    lo, hi = min(finite), max(finite)
    if errs:
        finite_err = [e for e in errs if np.isfinite(e)]
        if finite_err:
            lo = min(lo - max(finite_err), lo)
            hi = max(hi + max(finite_err), hi)
    span = hi - lo if hi != lo else max(abs(lo), abs(hi)) * 0.2 or 1.0
    ax.set_ylim(lo - margin * span, hi + margin * span)



# ── MMPBSA-specific colour map (component → colour) ────────────────────────
_COMP_PAL = {
    "VdW":        "#4477AA",   # blue
    "Electrost.": "#EE6677",   # rose
    "Polar Solv.":"#228833",   # green
    "Non-Polar":  "#CCBB44",   # olive-yellow
    "Internal":   "#AA3377",   # purple
    "TOTAL":      "#333333",   # near-black
}

# GB and PB get distinct hues for cross-model comparisons
_MODEL_PAL = {"GB": "#4477AA", "PB": "#EE6677"}

# Minimum absolute ΔG (kcal/mol) a component must reach across any residue /
# ligand entry to be included in component-level plots.  Any row whose
# max(|value|) stays below this cutoff is treated as negligible and dropped.
_NEGLIGIBLE_COMPONENT: float = 0.05  # kcal/mol

# ═══════════════════════════════════════════════════════════════════════════════
# PARSERS
# ═══════════════════════════════════════════════════════════════════════════════

def parse_energy_file(path: str | Path) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Parse AMBER MMPBSA energy CSV.

    Returns
    -------
    result[model][section] → DataFrame
        model   : "GB" | "PB"
        section : "Complex" | "Receptor" | "Ligand" | "Delta"
    """
    result: dict[str, dict[str, pd.DataFrame]] = {}
    current_model: Optional[str] = None
    current_section: Optional[str] = None
    current_cols: Optional[list] = None
    buffer: list[list] = []

    model_map = {"GENERALIZED BORN:": "GB", "POISSON BOLTZMANN:": "PB"}
    section_re = re.compile(
        r"^(Complex|Receptor|Ligand|DELTA)\s+Energy\s+Terms\s*$", re.IGNORECASE
    )

    def _flush():
        nonlocal buffer, current_cols, current_model, current_section
        if buffer and current_cols and current_model and current_section:
            df = pd.DataFrame(buffer, columns=current_cols)
            df = df.apply(pd.to_numeric, errors="coerce")
            result.setdefault(current_model, {})[current_section] = df
        buffer.clear()

    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line in model_map:
                _flush()
                current_model = model_map[line]
                current_section = None
                current_cols = None
                continue
            m = section_re.match(line)
            if m:
                _flush()
                # Normalise "DELTA" → "Delta" so all sections use Title Case
                current_section = m.group(1).capitalize()
                current_cols = None
                continue
            if line.startswith("Frame #,"):
                current_cols = [c.strip() for c in line.split(",")]
                continue
            if current_cols and current_model and current_section:
                parts = line.split(",")
                if len(parts) == len(current_cols):
                    buffer.append(parts)

    _flush()
    return result


# Canonical flat column names for the decomp DataFrame
_COMPONENTS = [
    "Internal", "van der Waals", "Electrostatic",
    "Polar Solvation", "Non-Polar Solv.", "TOTAL",
]
_STATS = ["Avg", "Std_Dev", "Std_Err"]
_DECOMP_COLS = ["Residue", "Location"]
for _comp in _COMPONENTS:
    _short = (
        _comp.replace(" ", "_").replace(".", "").replace("/", "").rstrip("_")
    )
    for _stat in _STATS:
        _DECOMP_COLS.append(f"{_short}_{_stat}")


def parse_decomp_file(path: str | Path) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Parse AMBER MMPBSA decomposition CSV.

    Returns
    -------
    result[model][decomp_type] → DataFrame
        model      : "GB" | "PB"
        decomp_type: "Total" | "Sidechain" | "Backbone"

    Column layout (flat names, 20 columns total):
        Residue, Location,
        Internal_{Avg|Std_Dev|Std_Err},
        van_der_Waals_{Avg|...}, Electrostatic_{Avg|...},
        Polar_Solvation_{Avg|...}, Non-Polar_Solv_{Avg|...},
        TOTAL_{Avg|Std_Dev|Std_Err}
    """
    result: dict[str, dict[str, pd.DataFrame]] = {}
    current_model: Optional[str] = None
    current_dtype: Optional[str] = None
    buffer: list[list] = []
    skip_rows: int = 0

    model_re = re.compile(
        r"Energy Decomposition Analysis.*?:\s*(Generalized Born|Poisson Boltzmann) solvent",
        re.IGNORECASE,
    )
    dtype_re = re.compile(
        r"^(Total|Sidechain|Backbone)\s+Energy\s+Decomposition\s*:",
        re.IGNORECASE,
    )
    _skip_lines = frozenset({"DELTAS:", "COMPLEX:", "RECEPTOR:", "LIGAND:"})

    def _flush():
        nonlocal buffer, current_model, current_dtype
        if buffer and current_model and current_dtype:
            df = pd.DataFrame(buffer, columns=_DECOMP_COLS)
            for col in _DECOMP_COLS[2:]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            result.setdefault(current_model, {})[current_dtype] = df
        buffer.clear()

    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("|"):
                continue
            if re.match(r"^idecomp\s*=", line):
                continue
            if line in _skip_lines:
                continue

            m = model_re.search(line)
            if m:
                _flush()
                current_model = "GB" if "born" in m.group(1).lower() else "PB"
                current_dtype = None
                continue

            m = dtype_re.match(line)
            if m:
                _flush()
                current_dtype = m.group(1).capitalize()
                skip_rows = 2      # two header rows follow each section opener
                continue

            if skip_rows > 0:
                skip_rows -= 1
                continue

            if current_model and current_dtype:
                parts = line.split(",")
                if len(parts) == 20:
                    buffer.append([p.strip() for p in parts])

    _flush()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_top_resname(raw: str) -> str:
    """'PRO   1' → 'PRO1'."""
    return re.sub(r"\s+", "", raw)


def _top_contributors(df: pd.DataFrame, n: int = 20,
                      col: str = "TOTAL_Avg",
                      receptor_only: bool = True) -> pd.DataFrame:
    """
    Return the n residues with the largest |col|.

    receptor_only : exclude ligand rows (Location starts with 'L').
    """
    d = df.copy()
    if receptor_only:
        d = d[d["Location"].str.startswith("R")]
    d = d.loc[d[col].abs().sort_values(ascending=False).index]
    return d.head(n).reset_index(drop=True)


def _delta_total_col(df: pd.DataFrame) -> str:
    """Return the correct DELTA TOTAL column name (handles GB and PB)."""
    if "DELTA TOTAL" in df.columns:
        return "DELTA TOTAL"
    candidates = [c for c in df.columns if "TOTAL" in c.upper()]
    if candidates:
        return candidates[0]
    raise KeyError(f"Cannot find TOTAL column in {list(df.columns)}")


def _available_models(energy: dict, pb: bool, gb: bool) -> list[tuple[str, str]]:
    """Return [(model_key, label), ...] for models that exist in the data."""
    want = []
    if gb:
        want.append(("GB", "Generalized Born"))
    if pb:
        want.append(("PB", "Poisson–Boltzmann"))
    return [(k, l) for k, l in want if k in energy]


# Component columns shared across multiple plots
_COMP_COLS_GB = ["VDWAALS", "EEL", "EGB",    "ESURF"]
_COMP_COLS_PB = ["VDWAALS", "EEL", "EPB",    "ENPOLAR", "EDISPER"]
_COMP_LABELS  = {
    "VDWAALS": "VdW",
    "EEL":     "Electrost.",
    "EGB":     "Polar (GB)",
    "ESURF":   "Non-polar (GB)",
    "EPB":     "Polar (PB)",
    "ENPOLAR": "Non-polar (PB)",
    "EDISPER": "Dispersion",
}
_COMP_COLORS  = [
    _COMP_PAL["VdW"], _COMP_PAL["Electrost."],
    _COMP_PAL["Polar Solv."], _COMP_PAL["Non-Polar"],
    _COMP_PAL["Internal"], _DISC_COLORS[4], _DISC_COLORS[5],
]


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 01 – Binding free energy time-series (DELTA TOTAL) with KDE strip
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_binding_timeseries(energy: dict, gb: bool, pb: bool,
                             dt_frame: float, output_dir, format: str) -> None:
    models = _available_models(energy, pb=pb, gb=gb)
    if not models:
        return

    n = len(models)
    fig = plt.figure(figsize=(7 * n, 4.5))
    outer = gridspec.GridSpec(1, n, wspace=0.35, left=0.09, right=0.97)

    for col_idx, (key, label) in enumerate(models):
        if "Delta" not in energy.get(key, {}):
            continue
        df = energy[key]["Delta"]
        tcol = _delta_total_col(df)
        vals = df[tcol].values.astype(float)
        t_ns = _frames_to_ns(df["Frame #"].values, dt_frame)

        inner = gridspec.GridSpecFromSubplotSpec(
            1, 2, subplot_spec=outer[col_idx],
            width_ratios=[5, 1], wspace=0.05,
        )
        ax     = fig.add_subplot(inner[0])
        ax_kde = fig.add_subplot(inner[1], sharey=ax)

        window = max(5, len(vals) // 50)
        avg    = _rolling(vals, window)
        std    = _rolling_std(vals, window)
        col    = _MODEL_PAL[key]

        ax.plot(t_ns, vals, color=col, lw=0.6, alpha=0.35)
        ax.plot(t_ns, avg,  color=col, lw=1.9, label=f"Rolling avg ({window} fr)")
        ax.fill_between(t_ns, avg - std, avg + std,
                        color=col, alpha=0.18, label=r"$\pm$1 SD")

        mean_v = np.nanmean(vals)
        ax.axhline(mean_v, color="#444444", lw=1.1, ls="--")
        ax.text(t_ns[-1] * 0.98, mean_v,
                rf"$\mu={mean_v:.2f}$",
                ha="right", va="bottom", fontsize=9, color="#333333")

        ax.set_xlabel(r"Simulation Time (ns)")
        ax.set_ylabel(r"$\Delta G_{\mathrm{bind}}$ (kcal/mol)")
        ax.set_title(label, fontweight="bold")
        ax.legend(frameon=False, fontsize=8, ncol=2)
        _smart_ylim(ax)

        # KDE strip
        kde    = gaussian_kde(vals[np.isfinite(vals)])
        y_grid = np.linspace(vals.min(), vals.max(), 300)
        ax_kde.fill_betweenx(y_grid, 0, kde(y_grid), color=col, alpha=0.35)
        ax_kde.plot(kde(y_grid), y_grid, color=col, lw=1.4)
        ax_kde.set_xlabel("Density", fontsize=9)
        ax_kde.tick_params(labelleft=False)
        ax_kde.spines["left"].set_visible(False)
        ax_kde.grid(False)

    fig.suptitle(r"Binding Free Energy ($\Delta G_{\mathrm{bind}}$) Time-Series",
                 fontsize=14, fontweight="bold")
    _savefig(fig, "01_binding_timeseries", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 02 – Mean DELTA energy components (bar + error) side-by-side
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_delta_components(energy: dict, gb: bool, pb: bool,
                           output_dir, format: str) -> None:
    models = _available_models(energy, pb=pb, gb=gb)
    if not models:
        return

    comp_map = {"GB": _COMP_COLS_GB, "PB": _COMP_COLS_PB}
    n = len(models)
    fig, axes = plt.subplots(1, n, figsize=(6.5 * n, 5),
                             constrained_layout=True)
    if n == 1:
        axes = [axes]

    for ax, (key, label) in zip(axes, models):
        if "Delta" not in energy.get(key, {}):
            ax.set_visible(False)
            continue
        df = energy[key]["Delta"]
        raw_cols = [c for c in comp_map[key] if c in df.columns]
        labels   = [_COMP_LABELS.get(c, c) for c in raw_cols]
        avgs     = [df[c].mean()            for c in raw_cols]
        errs     = [df[c].std()             for c in raw_cols]
        colors   = _COMP_COLORS[:len(raw_cols)]

        norm = mcolors.TwoSlopeNorm(vmin=min(avgs) * 1.1,
                                    vcenter=0,
                                    vmax=max(avgs) * 1.1 if max(avgs) > 0 else 1)
        bar_cols = [
            mcolors.to_hex(plt.get_cmap("RdBu_r")(norm(v))) for v in avgs
        ]

        bars = ax.bar(labels, avgs, color=bar_cols,
                      edgecolor="white", linewidth=0.8, zorder=3)
        ax.errorbar(labels, avgs, yerr=errs, fmt="none",
                    ecolor="#333333", capsize=4, lw=1.2, zorder=4)
        ax.axhline(0, color="#333333", lw=0.9, zorder=2)

        data_hi = max(a + e for a, e in zip(avgs, errs))
        data_lo = min(a - e for a, e in zip(avgs, errs))
        y_span  = (data_hi - data_lo) or 1.0   # guard against degenerate data
        pad     = y_span * 0.03                 # 3 % clearance beyond the cap
 
        for bar, val, err in zip(bars, avgs, errs):
            # Place label just beyond the error-bar cap, not just the bar edge.
            label_y = val + err + pad if val >= 0 else val - err - pad
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                label_y,
                f"{val:.1f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=8.5, fontweight="bold", color="#222222",
            )
        # ────────────────────────────────────────────────────────────────────
 
        ax.set_ylabel(r"$\Delta G$ (kcal/mol)")
        ax.set_xlabel("Energy Component")
        ax.set_title(f"Mean $\\Delta G$ Components — {key} ({label})",
                     fontweight="bold")
        ax.tick_params(axis="x", rotation=20)
        # error caps stay inside the axes.
        _bar_ylim(ax, avgs, errs=errs, margin=0.30)
 
    fig.suptitle(r"Average $\Delta G_{\mathrm{bind}}$ Decomposition",
                 fontsize=14, fontweight="bold")
    _savefig(fig, "02_delta_components", output_dir, format)
    fig.suptitle(r"Average $\Delta G_{\mathrm{bind}}$ Decomposition",
                 fontsize=14, fontweight="bold")
    _savefig(fig, "02_delta_components", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 03 – Per-residue TOTAL ΔG horizontal bar (one panel per model)
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_per_residue_total(decomp: dict, gb: bool, pb: bool,
                            n_top_res: int = 25,
                            output_dir=None, format: str = "pdf") -> None:
    models = [(k, lbl) for k, lbl in [("GB", "Generalized Born"),
                                        ("PB", "Poisson–Boltzmann")]
              if (k == "GB" and gb) or (k == "PB" and pb)]
    avail = [(k, l) for k, l in models
             if k in decomp and "Total" in decomp[k]]
    if not avail:
        return

    for key, label in avail:
        df = _top_contributors(decomp[key]["Total"], n=n_top_res)
        df = df.copy()
        df["label"] = df["Residue"].apply(_clean_top_resname)
        df_sorted   = df.sort_values("TOTAL_Avg")

        # Diverging: favourable (negative) = teal, unfavourable (positive) = salmon
        norm      = mcolors.TwoSlopeNorm(
            vmin=df_sorted["TOTAL_Avg"].min(),
            vcenter=0,
            vmax=max(df_sorted["TOTAL_Avg"].max(), 1e-6),
        )
        cmap_div  = plt.get_cmap("RdBu")   # blue=negative (favourable)
        bar_cols  = [mcolors.to_hex(cmap_div(norm(v)))
                     for v in df_sorted["TOTAL_Avg"]]

        bar_h = max(3.5, min(12, len(df_sorted) * 0.30 + 2.0))
        fig, ax = plt.subplots(figsize=(10, bar_h),
                               constrained_layout=True)

        bars = ax.barh(
            df_sorted["label"], df_sorted["TOTAL_Avg"],
            xerr=df_sorted["TOTAL_Std_Err"],
            color=bar_cols, edgecolor="white", linewidth=0.5,
            error_kw=dict(ecolor="#333333", capsize=3, lw=0.9),
        )
        ax.axvline(0, color="#333333", lw=0.9)

        xlim   = ax.get_xlim()
        x_span = xlim[1] - xlim[0]
        # Iterate rows alongside bars so we can read each row's own Std_Err.
        for bar, (_, row) in zip(bars, df_sorted.iterrows()):  # FIX 1b
            val = row["TOTAL_Avg"]
            # Per-bar error; fall back to 0 if the value is NaN.
            err = float(row["TOTAL_Std_Err"]) if pd.notna(row["TOTAL_Std_Err"]) else 0.0
            # Clearance = own error cap + 1 % of the full axis width.
            pad = err + x_span * 0.01
            ha  = "left"  if val >= 0 else "right"
            x   = val + pad if val >= 0 else val - pad
            ax.text(x, bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}", va="center", ha=ha,
                    fontsize=7.5, color="#222222")

        ax.set_xlabel(r"$\Delta G_{\mathrm{total}}$ (kcal/mol)")
        ax.set_title(
            f"Top {n_top_res} Per-Residue Binding Contributions ({key} · {label})\n"
            r"Blue $\Rightarrow$ favourable  |  Red $\Rightarrow$ unfavourable",
            fontweight="bold",
        )

        # Legend chips
        from matplotlib.patches import Patch
        legend_patches = [
            Patch(color=cmap_div(norm(-1)), label="Unfavourable (< 0)"),
            Patch(color=cmap_div(norm(+1)), label="Favourable (> 0)"),
        ]
        ax.legend(handles=legend_patches, frameon=False,
                  fontsize=8, loc="lower right")

        _savefig(fig, f"03_per_residue_total_{key}", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 04 – Stacked component bar for top contributors
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_component_stacked(decomp: dict, gb: bool, pb: bool,
                            n_top_res: int = 20,
                            output_dir=None, format: str = "pdf") -> None:
    models = [(k, lbl) for k, lbl in [("GB", "Generalized Born"),
                                        ("PB", "Poisson–Boltzmann")]
              if (k == "GB" and gb) or (k == "PB" and pb)]
    avail = [(k, l) for k, l in models
             if k in decomp and "Total" in decomp[k]]
    if not avail:
        return

    comp_col_map = [
        ("VdW",         "van_der_Waals_Avg",     _COMP_PAL["VdW"]),
        ("Electrost.",  "Electrostatic_Avg",      _COMP_PAL["Electrost."]),
        ("Polar Solv.", "Polar_Solvation_Avg",    _COMP_PAL["Polar Solv."]),
        ("Non-Polar",   "Non-Polar_Solv_Avg",     _COMP_PAL["Non-Polar"]),
        ("Internal",    "Internal_Avg",           _COMP_PAL["Internal"]),
    ]

    for key, label in avail:
        top = _top_contributors(decomp[key]["Total"], n=n_top_res)
        top = top.copy()
        top["label"] = top["Residue"].apply(_clean_top_resname)
        top = top.sort_values("TOTAL_Avg")

        present = [(nm, col, clr) for nm, col, clr in comp_col_map
                   if col in top.columns]

        x         = np.arange(len(top))
        lefts_pos = np.zeros(len(top))
        lefts_neg = np.zeros(len(top))

        fig, ax = plt.subplots(figsize=(max(10, n_top_res * 0.6), 5.5),
                               constrained_layout=True)

        for nm, col_name, clr in present:
            vals = top[col_name].fillna(0).values.astype(float)
            pos  = np.where(vals >= 0, vals, 0.0)
            neg  = np.where(vals <  0, vals, 0.0)
            ax.bar(x, pos, bottom=lefts_pos, label=nm, color=clr,
                   edgecolor="white", linewidth=0.4, zorder=3)
            ax.bar(x, neg, bottom=lefts_neg, color=clr,
                   edgecolor="white", linewidth=0.4, zorder=3)
            lefts_pos += pos
            lefts_neg += neg

        # TOTAL dots with error bars
        ax.scatter(x, top["TOTAL_Avg"].values,
                   color="#111111", s=22, zorder=5,
                   label="Total", marker="D")
        ax.errorbar(x, top["TOTAL_Avg"].values,
                    yerr=top["TOTAL_Std_Err"].values,
                    fmt="none", ecolor="#111111",
                    capsize=2.5, lw=0.9, zorder=6)

        ax.set_xticks(x)
        ax.set_xticklabels(top["label"], rotation=50, ha="right", fontsize=8.5)
        ax.axhline(0, color="#333333", lw=0.8)
        ax.set_ylabel(r"$\Delta G$ (kcal/mol)")
        ax.set_title(
            f"Per-Residue Energy Components — Top {n_top_res} Contributors ({key})",
            fontweight="bold",
        )
        ax.legend(loc="upper left", frameon=False, fontsize=8.5,
                  ncol=len(present) + 1)

        y_stack_top = max(
            float(lefts_pos.max()),
            # also accommodate TOTAL + error-bar caps (scatter overlay)
            float(np.nanmax(top["TOTAL_Avg"].values
                            + top["TOTAL_Std_Err"].fillna(0).values)),
        )
        y_stack_bot = min(
            float(lefts_neg.min()),
            float(np.nanmin(top["TOTAL_Avg"].values
                            - top["TOTAL_Std_Err"].fillna(0).values)),
        )
        y_span_stack = (y_stack_top - y_stack_bot) or 1.0
        # 0.28 top margin gives the upper-left legend room above the tallest bar.
        ax.set_ylim(y_stack_bot - 0.12 * y_span_stack,
                    y_stack_top + 0.28 * y_span_stack)

        _savefig(fig, f"04_component_stacked_{key}", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 05 – Component heatmap for top N residues
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_component_heatmap(decomp: dict, gb: bool, pb: bool,
                            n_top_res: int = 30,
                            output_dir=None, format: str = "pdf") -> None:
    models = [(k, lbl) for k, lbl in [("GB", "Generalized Born"),
                                        ("PB", "Poisson–Boltzmann")]
              if (k == "GB" and gb) or (k == "PB" and pb)]
    avail = [(k, l) for k, l in models
             if k in decomp and "Total" in decomp[k]]
    if not avail:
        return

    avg_col_map = {
        "VdW":         "van_der_Waals_Avg",
        "Electrost.":  "Electrostatic_Avg",
        "Polar Solv.": "Polar_Solvation_Avg",
        "Non-Polar":   "Non-Polar_Solv_Avg",
        "Internal":    "Internal_Avg",
        "TOTAL":       "TOTAL_Avg",
    }

    for key, label in avail:
        top = _top_contributors(decomp[key]["Total"], n=n_top_res)
        top = top.copy()
        top["label"] = top["Residue"].apply(_clean_top_resname)
        top = top.sort_values("TOTAL_Avg")  # order by total contribution

        present = {nm: col for nm, col in avg_col_map.items()
                   if col in top.columns}
        mat         = top[[v for v in present.values()]].values.T
        row_labels  = list(present.keys())
        col_labels  = top["label"].tolist()

        keep_idx   = [
            i for i, nm in enumerate(row_labels)
            if nm == "TOTAL" or np.nanmax(np.abs(mat[i])) >= _NEGLIGIBLE_COMPONENT
        ]
        mat = mat[keep_idx] 
        row_labels = [row_labels[i] for i in keep_idx]

        n_col = len(col_labels)
        fig_w = max(10, n_col * 0.45)
        fig, ax = plt.subplots(figsize=(fig_w, max(3.5, len(row_labels) * 0.65)),
                               constrained_layout=True)

        vmax = np.nanpercentile(np.abs(mat), 95)
        vmax = max(vmax, 0.1)   # guard against all-zero

        im = ax.imshow(
            mat, aspect="auto", cmap="RdBu_r",
            vmin=-vmax, vmax=vmax, origin="upper",
        )
        ax.set_xticks(range(n_col))
        ax.set_xticklabels(col_labels, rotation=55, ha="right", fontsize=8)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels, fontsize=9)
        ax.tick_params(length=0)
        ax.grid(False)

        # Cell annotations for TOTAL row only (last row)
        total_row = len(row_labels) - 1
        for j in range(n_col):
            val  = mat[total_row, j]
            txt  = f"{val:.2f}" if abs(val) >= 0.05 else ""
            tcol = "white" if abs(val) > vmax * 0.6 else "#222222"
            ax.text(j, total_row, txt,
                    ha="center", va="center", fontsize=6.5,
                    color=tcol, fontweight="bold")

        # Separate TOTAL row with a thin line
        ax.axhline(total_row - 0.5, color="white", lw=1.8)

        cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01, shrink=0.8)
        cb.set_label(r"$\Delta G$ (kcal/mol)", fontsize=9)
        cb.ax.tick_params(labelsize=8)

        ax.set_title(
            f"Energy Component Heatmap — Top {n_top_res} Residues ({key} · {label})",
            fontweight="bold",
        )
        _savefig(fig, f"05_heatmap_{key}", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 06 – Sidechain vs. Backbone scatter
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_sidechain_vs_backbone(decomp: dict, gb: bool, pb: bool,
                                output_dir=None, format: str = "pdf") -> None:
    models = [(k, lbl) for k, lbl in [("GB", "Generalized Born"),
                                        ("PB", "Poisson–Boltzmann")]
              if (k == "GB" and gb) or (k == "PB" and pb)]
    avail = [(k, l) for k, l in models
             if k in decomp
             and "Sidechain" in decomp[k]
             and "Backbone"  in decomp[k]]
    if not avail:
        return

    for key, label in avail:
        sc_df = decomp[key]["Sidechain"]
        bb_df = decomp[key]["Backbone"]

        sc = (sc_df[sc_df["Location"].str.startswith("R")]
              .set_index("Residue")["TOTAL_Avg"])
        bb = (bb_df[bb_df["Location"].str.startswith("R")]
              .set_index("Residue")["TOTAL_Avg"])
        idx = sc.index.intersection(bb.index)
        sc, bb = sc.loc[idx], bb.loc[idx]

        all_vals = np.concatenate([sc.values, bb.values])
        lim = np.nanmax(np.abs(all_vals)) * 1.15 or 1.0

        # Colour points by total contribution magnitude
        combined_abs = sc.abs() + bb.abs()
        norm = mcolors.Normalize(vmin=0, vmax=combined_abs.max())
        pt_colors = plt.get_cmap("viridis")(norm(combined_abs.values))

        fig, ax = plt.subplots(figsize=(6.5, 6.5),
                               constrained_layout=True)
        ax.scatter(bb, sc, c=pt_colors, s=28, alpha=0.75,
                   edgecolors="white", linewidth=0.4, zorder=3, rasterized=True)
        ax.axhline(0, color="#AAAAAA", lw=0.8, ls="--", zorder=1)
        ax.axvline(0, color="#AAAAAA", lw=0.8, ls="--", zorder=1)
        ax.plot([-lim, lim], [-lim, lim],
                color="#888888", lw=0.9, ls=":", zorder=1, label="y = x")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.01, shrink=0.85)
        cb.set_label(r"|SC| + |BB| $\Delta G$ (kcal/mol)", fontsize=9)
        cb.ax.tick_params(labelsize=8)

        # Annotate top 8 movers — prevent overlap by shifting systematically
        top8 = combined_abs.sort_values(ascending=False).head(8)
        already = []
        for res in top8.index:
            x0, y0 = bb[res], sc[res]
            # nudge label away from zero crossing if close to origin
            dx, dy = 0.0, lim * 0.045
            if abs(y0) < lim * 0.08:
                dy = lim * 0.07
            ax.annotate(
                _clean_top_resname(res),
                xy=(x0, y0), xytext=(x0 + dx, y0 + dy),
                fontsize=7.5, ha="center", color="#111111",
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#999999"),
            )

        ax.set_xlabel(r"Backbone $\Delta G$ (kcal/mol)")
        ax.set_ylabel(r"Sidechain $\Delta G$ (kcal/mol)")
        ax.set_title(
            f"Sidechain vs. Backbone Contributions ({key} · {label})",
            fontweight="bold",
        )
        ax.legend(frameon=False, fontsize=8)

        _savefig(fig, f"06_sc_vs_bb_{key}", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 07 – GB vs. PB per-residue scatter (only when both run)
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_gb_vs_pb(decomp: dict, gb: bool, pb: bool,
                   output_dir=None, format: str = "pdf") -> None:
    if not (gb and pb):
        return
    if "GB" not in decomp or "PB" not in decomp:
        return
    gb_tot = decomp["GB"].get("Total")
    pb_tot = decomp["PB"].get("Total")
    if gb_tot is None or pb_tot is None:
        return

    gb_s = (gb_tot[gb_tot["Location"].str.startswith("R")]
            .set_index("Residue")["TOTAL_Avg"])
    pb_s = (pb_tot[pb_tot["Location"].str.startswith("R")]
            .set_index("Residue")["TOTAL_Avg"])
    idx  = gb_s.index.intersection(pb_s.index)
    gb_s, pb_s = gb_s.loc[idx], pb_s.loc[idx]

    lim  = max(np.nanmax(np.abs(gb_s.values)),
               np.nanmax(np.abs(pb_s.values))) * 1.15 or 1.0
    diff = (pb_s - gb_s).abs()
    norm = mcolors.Normalize(vmin=0, vmax=diff.max())
    pt_colors = plt.get_cmap("plasma_r")(norm(diff.values))

    fig, ax = plt.subplots(figsize=(6.5, 6.5),
                           constrained_layout=True)
    ax.scatter(gb_s, pb_s, c=pt_colors, s=28, alpha=0.75,
               edgecolors="white", linewidth=0.4, zorder=3, rasterized=True)
    ax.plot([-lim, lim], [-lim, lim],
            color="#888888", lw=0.9, ls="--", zorder=1, label="y = x")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    r = np.corrcoef(gb_s.values, pb_s.values)[0, 1]
    ax.text(0.05, 0.95, f"$r = {r:.3f}$",
            transform=ax.transAxes, fontsize=10, va="top", color="#333333")

    sm = plt.cm.ScalarMappable(cmap="plasma_r", norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.01, shrink=0.85)
    cb.set_label(r"|PB − GB| (kcal/mol)", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    # Annotate the 6 biggest GB–PB disagreements
    for res in diff.sort_values(ascending=False).head(6).index:
        ax.annotate(
            _clean_top_resname(res),
            xy=(gb_s[res], pb_s[res]),
            xytext=(gb_s[res], pb_s[res] + lim * 0.05),
            fontsize=7.5, ha="center",
            arrowprops=dict(arrowstyle="-", lw=0.6, color="#999999"),
        )

    ax.set_xlabel(r"GB $\Delta G$ (kcal/mol)")
    ax.set_ylabel(r"PB $\Delta G$ (kcal/mol)")
    ax.set_title("Per-Residue GB vs. PB Contributions",
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=8)

    _savefig(fig, "07_gb_vs_pb", output_dir, format)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 08 – Ligand contribution summary
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_ligand_summary(decomp: dict, gb: bool, pb: bool,
                         output_dir=None, format: str = "pdf") -> None:
    models = [(k, lbl) for k, lbl in [("GB", "Generalized Born"),
                                        ("PB", "Poisson–Boltzmann")]
              if (k == "GB" and gb) or (k == "PB" and pb)]

    comp_col_map = [
        ("VdW",         "van_der_Waals_Avg",   "van_der_Waals_Std_Err"),
        ("Electrost.",  "Electrostatic_Avg",    "Electrostatic_Std_Err"),
        ("Polar Solv.", "Polar_Solvation_Avg",  "Polar_Solvation_Std_Err"),
        ("Non-Polar",   "Non-Polar_Solv_Avg",   "Non-Polar_Solv_Std_Err"),
        ("Internal",    "Internal_Avg",         "Internal_Std_Err"),
        ("TOTAL",       "TOTAL_Avg",            "TOTAL_Std_Err"),
    ]

    rows = []
    for key, label in models:
        if key not in decomp:
            continue
        for dtype in ("Total", "Sidechain", "Backbone"):
            df = decomp[key].get(dtype)
            if df is None:
                continue
            lig = df[df["Location"].str.startswith("L")]
            if lig.empty:
                continue
            row = {"Model": key, "Type": dtype}
            for nm, avg_col, err_col in comp_col_map:
                row[f"{nm}_avg"] = lig[avg_col].values[0] if avg_col in lig.columns else np.nan
                row[f"{nm}_err"] = lig[err_col].values[0] if err_col in lig.columns else np.nan
            rows.append(row)

    if not rows:
        return

    df_lig = pd.DataFrame(rows)
    # Only Total decomp is informative for ligand
    df_lig = df_lig[df_lig["Type"] == "Total"].reset_index(drop=True)
    if df_lig.empty:
        return

    comps   = [nm for nm, _, _ in comp_col_map]

    # "Internal" is the typical target (≈ 0 kcal/mol in standard runs).
    # A component is kept if *any* model has |avg| ≥ _NEGLIGIBLE_COMPONENT.
    comps = [
        c for c in comps
        if any(
            np.isfinite(row.get(f"{c}_avg", np.nan)) and
            abs(row.get(f"{c}_avg", 0.0)) >= _NEGLIGIBLE_COMPONENT
            for _, row in df_lig.iterrows()
        )
    ]

    n_model = len(df_lig)
    x       = np.arange(len(comps))
    width   = 0.35
    offsets = np.linspace(-width * (n_model - 1) / 2,
                          width * (n_model - 1) / 2, n_model)

    # Pre-compute the full data range (value ± error) across all models and
    # components so labels can be positioned relative to each bar's own error-bar cap
    _caps_pos, _caps_neg = [], []
    for _, _row in df_lig.iterrows():
        for c in comps:
            a = _row.get(f"{c}_avg", np.nan)
            e = _row.get(f"{c}_err", np.nan)
            if np.isfinite(a):
                e_val = e if np.isfinite(e) else 0.0
                _caps_pos.append(a + e_val)
                _caps_neg.append(a - e_val)
    _y_hi      = max(_caps_pos) if _caps_pos else  1.0
    _y_lo      = min(_caps_neg) if _caps_neg else -1.0
    _y_span    = (_y_hi - _y_lo) or 1.0
    _label_pad = _y_span * 0.025   # 2.5 % clearance beyond the error-bar cap

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for i, (_, row) in enumerate(df_lig.iterrows()):
        model  = row["Model"]
        avgs   = [row.get(f"{c}_avg", np.nan) for c in comps]
        errs   = [row.get(f"{c}_err", np.nan) for c in comps]
        col    = _MODEL_PAL.get(model, _DISC_COLORS[i])
        bars   = ax.bar(x + offsets[i], avgs, width * 0.85,
                        color=col, alpha=0.82, label=model,
                        edgecolor="white", linewidth=0.6, zorder=3)
        ax.errorbar(x + offsets[i], avgs, yerr=errs,
                    fmt="none", ecolor="#333333",
                    capsize=3, lw=1.0, zorder=4)

        # Add a value label for every bar, positioned just beyond its own
        # error-bar cap so it is never obscured.
        for xi, (avg, err) in enumerate(zip(avgs, errs)):
            if not np.isfinite(avg):
                continue
            e_val  = err if np.isfinite(err) else 0.0
            # Label sits above the positive cap or below the negative cap.
            lbl_y  = avg + e_val + _label_pad if avg >= 0 else avg - e_val - _label_pad
            ax.text(
                xi + offsets[i], lbl_y,
                f"{avg:.1f}",
                ha="center",
                va="bottom" if avg >= 0 else "top",
                fontsize=7, fontweight="bold", color=col,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(comps, rotation=15)
    ax.axhline(0, color="#333333", lw=0.8)
    ax.set_ylabel(r"$\Delta G$ (kcal/mol)")
    ax.set_title("Ligand Per-Component Binding Contribution",
                 fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    all_avgs = [row.get(f"{c}_avg", 0) for c in comps for _, row in df_lig.iterrows()]
    all_errs = [row.get(f"{c}_err", 0) for c in comps for _, row in df_lig.iterrows()]
    _bar_ylim(
        ax,
        [v for v in all_avgs if v is not None and np.isfinite(v)],
        errs=[v for v in all_errs if v is not None and np.isfinite(v)],
        margin=0.40,
    )

    _savefig(fig, "08_ligand_summary", output_dir, format)


# ---------------------------------------------------------------------------
# Master driver
# ---------------------------------------------------------------------------

from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig

def generate_mmpbsa_figures(
    cfg: MMPBSAConfig,
    outputs: dict,
) -> None:
    """
    Generate all publication-quality MMPBSA figures.
    """

    output_dir = cfg.common.output_dir
    gb = cfg.gb.run
    pb = cfg.pb.run

    dt_frame = cfg.figures.dt_frame * cfg.common.interval
    n_top_res = cfg.figures.n_top_res
    format = cfg.figures.format

    energy: dict = {}
    decomp: dict = {}

    if "energy" in outputs:
        energy = parse_energy_file(outputs["energy"])
        for model, sections in energy.items():
            for sec, df in sections.items():
                print(f"  [{model}][{sec}]: {len(df)} frames, "
                      f"cols = {list(df.columns)}")

    if "decomp" in outputs:
        decomp = parse_decomp_file(outputs["decomp"])
        for model, dtypes in decomp.items():
            for dtype, df in dtypes.items():
                print(f"  [{model}][{dtype}]: {len(df)} residues")

    n_top_res = 25

    steps = [
        ("Binding free-energy time-series",
         lambda: _plot_binding_timeseries(
             energy, gb=gb, pb=pb, dt_frame=dt_frame,
             output_dir=output_dir, format=format)),
        ("Mean ΔG component bars",
         lambda: _plot_delta_components(
             energy, gb=gb, pb=pb,
             output_dir=output_dir, format=format)),
        ("Per-residue TOTAL ΔG bars",
         lambda: _plot_per_residue_total(
             decomp, gb=gb, pb=pb, n_top_res=n_top_res,
             output_dir=output_dir, format=format)),
        ("Per-residue component stacked bars",
         lambda: _plot_component_stacked(
             decomp, gb=gb, pb=pb, n_top_res=n_top_res,
             output_dir=output_dir, format=format)),
        ("Component heatmap",
         lambda: _plot_component_heatmap(
             decomp, gb=gb, pb=pb, n_top_res=n_top_res,
             output_dir=output_dir, format=format)),
        ("Sidechain vs. backbone scatter",
         lambda: _plot_sidechain_vs_backbone(
             decomp, gb=gb, pb=pb,
             output_dir=output_dir, format=format)),
        ("GB vs. PB residue scatter",
         lambda: _plot_gb_vs_pb(
             decomp, gb=gb, pb=pb,
             output_dir=output_dir, format=format)),
        ("Ligand contribution summary",
         lambda: _plot_ligand_summary(
             decomp, gb=gb, pb=pb,
             output_dir=output_dir, format=format)),
    ]

    for name, fn in steps:
        print(f" Processing: {name}")
        try:
            fn()
        except Exception as exc:
            warnings.warn(f"    ✗ {name} failed: {exc}")

    print("\nDone.")
