import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter


# ---------------------------------------------------------------------------
# Global aesthetics
# ---------------------------------------------------------------------------

# Colorblind-safe discrete palette (10 distinct, no hot primaries)
_DISC_COLORS = [
    "#4477AA",  # blue
    "#EE6677",  # rose
    "#228833",  # green
    "#CCBB44",  # yellow-olive
    "#66CCEE",  # sky
    "#AA3377",  # purple
    "#BBBBBB",  # gray
    "#EE8866",  # orange-salmon
    "#44BB99",  # teal
    "#AAAA00",  # olive
]


def _apply_base_style() -> None:
    """Apply a clean, journal-ready rcParams globally."""
    mpl.rcParams.update({
        # ── fonts ──────────────────────────────────────────────────────────
        "font.family":           "sans-serif",
        "font.sans-serif":       ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size":             11,
        "axes.titlesize":        13,
        "axes.labelsize":        12,
        "xtick.labelsize":       10,
        "ytick.labelsize":       10,
        "legend.fontsize":       9,
        "legend.title_fontsize": 10,
        # ── lines ──────────────────────────────────────────────────────────
        "lines.linewidth":       1.6,
        "lines.solid_capstyle":  "round",
        # ── axes ───────────────────────────────────────────────────────────
        "axes.spines.top":       False,
        "axes.spines.right":     False,
        "axes.linewidth":        0.9,
        "axes.grid":             True,
        "grid.color":            "#DDDDDD",
        "grid.linewidth":        0.6,
        "grid.linestyle":        "--",
        # ── ticks ──────────────────────────────────────────────────────────
        "xtick.direction":       "out",
        "ytick.direction":       "out",
        "xtick.major.size":      4,
        "ytick.major.size":      4,
        "xtick.minor.size":      2,
        "ytick.minor.size":      2,
        "xtick.major.width":     0.9,
        "ytick.major.width":     0.9,
        # ── figure / save ──────────────────────────────────────────────────
        "figure.facecolor":      "white",
        "axes.facecolor":        "white",
        "savefig.dpi":           300,
        "savefig.bbox":          "tight",
        "savefig.facecolor":     "white",
        # ── mathtext ───────────────────────────────────────────────────────
        "mathtext.fontset":      "dejavuserif",
    })

_apply_base_style()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _savefig(fig: plt.Figure, name: str, output_dir: str | None, format: str) -> None:
    if output_dir is None:
        plt.show()
    else:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        path = Path(output_dir) / f"{name}.{format}"
        fig.savefig(path)
        print(f"  Saved → {path}")
    plt.close(fig)


def _load_cpptraj(path: str | Path,
                  **kwargs) -> np.ndarray:
    """Load a cpptraj .dat file (comment lines start with '#')."""
    return np.loadtxt(path, comments="#", **kwargs)


def _rolling(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple rolling mean preserving array length (edge-pad with NaN)."""
    out = np.full_like(arr, np.nan, dtype=float)
    half = window // 2
    for i in range(len(arr)):
        lo = max(0, i - half)
        hi = min(len(arr), i + half + 1)
        out[i] = arr[lo:hi].mean()
    return out


def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=float)
    half = window // 2
    for i in range(len(arr)):
        lo = max(0, i - half)
        hi = min(len(arr), i + half + 1)
        out[i] = arr[lo:hi].std()
    return out


def _frames_to_ns(frames: np.ndarray, dt_frame: float) -> np.ndarray:
    return frames * dt_frame * 1e-3   # ps → ns


def _smart_ylim(ax: plt.Axes, margin: float = 0.15) -> None:
    """Set y-limits with symmetric margin around data range (avoids zero floor)."""
    lines = ax.get_lines()
    yvals = np.concatenate([l.get_ydata() for l in lines if len(l.get_ydata()) > 0])
    yvals = yvals[np.isfinite(yvals)]
    if len(yvals) == 0:
        return
    lo, hi = yvals.min(), yvals.max()
    span = hi - lo if hi != lo else abs(lo) * 0.2 or 1.0
    ax.set_ylim(lo - margin * span, hi + margin * span)


# ---------------------------------------------------------------------------
# 1. RMSD  – time-series with rolling average + side KDE
# ---------------------------------------------------------------------------

def plot_rmsd(outputs: dict, dt_frame: float = 2.0,
              output_dir=None, format="pdf") -> None:
    if "rmsd_out" not in outputs:
        return
    data    = _load_cpptraj(outputs["rmsd_out"])
    frames  = data[:, 0]
    rmsd    = data[:, 1]
    time_ns = _frames_to_ns(frames, dt_frame)

    window  = max(5, len(rmsd) // 50)
    avg     = _rolling(rmsd, window)
    std     = _rolling_std(rmsd, window)

    fig = plt.figure(figsize=(11, 4))
    gs  = gridspec.GridSpec(1, 2, width_ratios=[5, 1], wspace=0.06)
    ax  = fig.add_subplot(gs[0])
    ax_kde = fig.add_subplot(gs[1], sharey=ax)

    ax.plot(time_ns, rmsd, color="#BBCCDD", lw=0.8, alpha=0.7, label="Raw")
    ax.plot(time_ns, avg,  color=_DISC_COLORS[0], lw=1.8, label=f"Rolling avg ({window} fr)")
    ax.fill_between(time_ns, avg - std, avg + std,
                    color=_DISC_COLORS[0], alpha=0.18, label=r"$\pm$1 SD")

    ax.set_xlabel(r"Simulation Time (ns)")
    ax.set_ylabel(r"RMSD ($\AA$)")
    ax.set_title("Backbone RMSD")
    ax.legend(frameon=False, loc="upper left", ncol=3)
    _smart_ylim(ax)

    # side KDE
    kde    = gaussian_kde(rmsd)
    y_grid = np.linspace(rmsd.min(), rmsd.max(), 300)
    ax_kde.fill_betweenx(y_grid, 0, kde(y_grid),
                         color=_DISC_COLORS[0], alpha=0.35)
    ax_kde.plot(kde(y_grid), y_grid, color=_DISC_COLORS[0], lw=1.4)
    ax_kde.set_xlabel("Density")
    ax_kde.tick_params(labelleft=False)
    ax_kde.spines["left"].set_visible(False)
    ax_kde.grid(False)

    fig.suptitle("RMSD Analysis", fontsize=14, fontweight="bold", y=1.01)
    _savefig(fig, "01_rmsd", output_dir, format)


# ---------------------------------------------------------------------------
# 2. RMSF  – per-residue with residue-averaged colour map
# ---------------------------------------------------------------------------

def plot_rmsf(outputs: dict, dt_frame: float = 2.0,
              output_dir=None, format="pdf") -> None:
    if "rmsf_out" not in outputs:
        return
    data = _load_cpptraj(outputs["rmsf_out"])
    res  = data[:, 0].astype(int)
    rmsf = data[:, 1]

    norm  = mcolors.Normalize(vmin=rmsf.min(), vmax=rmsf.max())
    cmap  = plt.get_cmap("viridis")

    fig, ax = plt.subplots(figsize=(13, 4))
    for i in range(len(res) - 1):
        ax.fill_between([res[i], res[i+1]], 0, [rmsf[i], rmsf[i+1]],
                        color=cmap(norm((rmsf[i]+rmsf[i+1])/2)), alpha=0.65)
    ax.plot(res, rmsf, color="#333333", lw=1.0)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.01, fraction=0.015)
    cbar.set_label(r"RMSF ($\AA$)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    ax.set_xlabel("Residue Number")
    ax.set_ylabel(r"RMSF ($\AA$)")
    ax.set_title("Per-Residue Backbone Atomic Fluctuation")
    ax.set_xlim(res[0], res[-1])
    ax.set_ylim(bottom=0)
    _savefig(fig, "02_rmsf", output_dir, format)


# ---------------------------------------------------------------------------
# 3. DSSP  – stacked area (totalout) + per-residue heatmap (sumout)
# ---------------------------------------------------------------------------

def plot_dssp(outputs: dict, dt_frame: float = 2.0,
              output_dir=None, format="pdf") -> None:
    if "ss_totalout" not in outputs or "ss_sumout" not in outputs:
        return

    # ── A: per-frame stacked area (focus on Extended, Helix, Other) ─────────
    tot = _load_cpptraj(outputs["ss_totalout"])
    frames  = tot[:, 0]
    time_ns = _frames_to_ns(frames, dt_frame)
    #  cols: Extended[1] Bridge[2] 3-10[3] Alpha[4] Pi[5] Turn[6] Bend[7]
    ext   = tot[:, 1]
    helix = tot[:, 3] + tot[:, 4] + tot[:, 5]   # Alpha + Pi + 3-10
    other = tot[:, 2] + tot[:, 6] + tot[:, 7]   # Bridge + Turn + Bend

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    ax = axes[0]

    window = max(5, len(time_ns) // 60)
    palette_ss = {"Extended": "#4477AA", "Helix": "#EE6677", "Other": "#88CCEE"}
    for label, series, col in [
        ("Extended", ext,   palette_ss["Extended"]),
        ("Helix",    helix, palette_ss["Helix"]),
        ("Other",    other, palette_ss["Other"]),
    ]:
        sm  = _rolling(series, window)
        std = _rolling_std(series, window)
        ax.plot(time_ns, sm,  color=col, lw=1.6, label=label)
        ax.fill_between(time_ns, sm - std, sm + std, color=col, alpha=0.18)

    ax.set_xlabel(r"Simulation Time (ns)")
    ax.set_ylabel("Fractional Population")
    ax.set_title("Secondary Structure Time Evolution", fontweight="bold")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, ncol=3)

    # ── B: per-residue heatmap (sumout) ─────────────────────────────────────
    sumdata = _load_cpptraj(outputs["ss_sumout"])
    res = sumdata[:, 0].astype(int)
    #  cols: Extended[1] Bridge[2] 3-10[3] Alpha[4] Pi[5] Turn[6] Bend[7]
    ext_r   = sumdata[:, 1]
    helix_r = sumdata[:, 3] + sumdata[:, 4] + sumdata[:, 5]
    other_r = sumdata[:, 2] + sumdata[:, 6] + sumdata[:, 7]

    heatmap = np.vstack([helix_r, ext_r, other_r])   # shape (3, n_res)
    ax2 = axes[1]
    im  = ax2.imshow(heatmap, aspect="auto", cmap="Blues",
                     extent=[res[0]-0.5, res[-1]+0.5, -0.5, 2.5],
                     vmin=0, vmax=1, origin="lower")
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(["Other", "Extended", "Helix"])
    ax2.set_xlabel("Residue Number")
    ax2.set_title("Per-Residue Secondary Structure Occupancy", fontweight="bold")
    ax2.grid(False)
    cb = fig.colorbar(im, ax=ax2, fraction=0.025, pad=0.01)
    cb.set_label("Fraction of Trajectory", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    fig.suptitle("DSSP Secondary Structure Analysis", fontsize=14, fontweight="bold")
    _savefig(fig, "03_dssp", output_dir, format)


# ---------------------------------------------------------------------------
# 4. Hydrogen bonds time-series panel (PP / PL / Bridge)
# ---------------------------------------------------------------------------

def plot_hbond_timeseries(outputs: dict, dt_frame: float = 2.0,
                          output_dir=None, format="pdf") -> None:
    series_map = {
        "PP_hbvtime":    ("Protein-Protein",  _DISC_COLORS[0]),
        "BB_hbvtime":    ("Protein Backbone",  _DISC_COLORS[1]),
        "PL_all_hbvtime":("Protein-Ligand",   _DISC_COLORS[2]),
    }
    available = [(k, *v) for k, v in series_map.items() if k in outputs]
    if not available:
        return

    n  = len(available)
    fig, axes = plt.subplots(n, 1, figsize=(12, 3.2 * n),
                             constrained_layout=True, sharex=False)
    if n == 1:
        axes = [axes]

    window = None
    for ax, (key, label, col) in zip(axes, available):
        dat     = _load_cpptraj(outputs[key])
        frames  = dat[:, 0]
        hb      = dat[:, 1].astype(float)
        time_ns = _frames_to_ns(frames, dt_frame)

        if window is None:
            window = max(5, len(hb) // 50)

        avg = _rolling(hb, window)
        std = _rolling_std(hb, window)

        ax.plot(time_ns, hb,  color=col, lw=0.6, alpha=0.45)
        ax.plot(time_ns, avg, color=col, lw=1.8)
        ax.fill_between(time_ns, avg - std, avg + std, color=col, alpha=0.22)

        mean_v = np.nanmean(hb)
        ax.axhline(mean_v, color="#555555", lw=1.0, ls="--", alpha=0.8)
        ax.text(time_ns[-1] * 0.98, mean_v,
                rf"$\mu={mean_v:.1f}$", ha="right", va="bottom",
                fontsize=9, color="#333333")

        ax.set_ylabel("H-bond count")
        ax.set_title(label, fontsize=11, fontweight="bold")
        _smart_ylim(ax)

    axes[-1].set_xlabel(r"Simulation Time (ns)")
    fig.suptitle("Hydrogen Bond Dynamics", fontsize=14, fontweight="bold")
    _savefig(fig, "04_hbond_timeseries", output_dir, format)


# ---------------------------------------------------------------------------
# 5. Hydrogen bond frequency bar charts (PP_avg, PL)
# ---------------------------------------------------------------------------

def _parse_hb_avg(path: str | Path, top_n: int = 20,
                  frac_max: float = 1.0) -> pd.DataFrame:
    """
    Parse cpptraj hbond avgout file.
    Column layout (0-based): Acceptor[0] DonorH[1] Donor[2] Frames/Count[3] Frac[4] ...
    frac_max: clip fractions above this
    Returns top_n rows sorted by occupancy fraction.
    """
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                frac = float(parts[4])
            except ValueError:
                continue
            # Clip fractions that represent solvent-contact counts (>1) to 1
            frac = min(frac, frac_max)
            acc   = parts[0]
            donor = parts[2]
            label = f"{acc}↔{donor}"
            rows.append({"label": label, "frac": frac})
    df = pd.DataFrame(rows).sort_values("frac", ascending=False).head(top_n)
    return df.reset_index(drop=True)


def plot_hbond_frequency(outputs: dict, dt_frame: float = 2.0,
                         output_dir=None, format="pdf") -> None:
    panels = [
        ("PP_avg",   "Protein-Protein H-bond Occupancy",  _DISC_COLORS[0]),
        ("BB_avg",   "Protein Backbone H-bond Occupancy",    _DISC_COLORS[3]),
    ]
    # Combine PtoL and LtoP into one dataset
    pl_rows = []
    for key in ("PtoL_avg", "LtoP_avg"):
        if key in outputs:
            try:
                df = _parse_hb_avg(outputs[key], top_n=30, frac_max=1.0)
                pl_rows.append(df)
            except Exception:
                pass
    if pl_rows:
        pl_df = pd.concat(pl_rows).sort_values("frac", ascending=False).head(20)
        panels.append(("_PL_combined", "Protein–Ligand H-bond Occupancy", _DISC_COLORS[1]))

    available = [(k, l, c) for k, l, c in panels if k in outputs or k == "_PL_combined"]
    if not available:
        return

    # Dynamic per-panel height: 0.30 in per bar + 2 in overhead, max 8 in
    def _panel_h(n_bars):
        return max(3.5, min(8.0, n_bars * 0.30 + 2.0))

    panel_data = []
    for k, l, c in available:
        if k == "_PL_combined":
            df = pl_df if pl_rows else pd.DataFrame()
        else:
            try:
                df = _parse_hb_avg(outputs[k], top_n=20, frac_max=1.0)
            except Exception as e:
                warnings.warn(f"Could not parse {k}: {e}")
                df = pd.DataFrame()
        panel_data.append((k, l, c, df))

    heights = [_panel_h(len(d)) for _, _, _, d in panel_data]
    fig, axes = plt.subplots(len(panel_data), 1,
                             figsize=(12, sum(heights)),
                             gridspec_kw={"height_ratios": heights},
                             constrained_layout=True)
    if len(panel_data) == 1:
        axes = [axes]

    for ax, (key, label, col, df) in zip(axes, panel_data):
        if df.empty:
            ax.axis("off")
            continue

        norm   = mcolors.Normalize(vmin=0, vmax=1)
        cmap_b = (plt.get_cmap("Blues")  if col == _DISC_COLORS[0] else
                  plt.get_cmap("Greens") if col == _DISC_COLORS[2] else
                  plt.get_cmap("Reds"))
        bar_colors = [cmap_b(norm(f)) for f in df["frac"]]

        bars = ax.barh(range(len(df)), df["frac"], color=bar_colors,
                       edgecolor="white", linewidth=0.5)
        ax.set_yticks(range(len(df)))
        ax.set_yticklabels(df["label"], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Occupancy (fraction of trajectory)")
        ax.set_title(label, fontweight="bold")
        xlim_max = min(df["frac"].max() * 1.18, 1.05)
        ax.set_xlim(0, xlim_max)
        ax.axvline(0.5, color="#AAAAAA", lw=0.9, ls="--")
        ax.grid(axis="x")
        ax.grid(axis="y", visible=False)

        for i, (bar, frac) in enumerate(zip(bars, df["frac"])):
            ax.text(min(frac + 0.015, xlim_max * 0.96), i,
                    f"{frac:.2f}", va="center", ha="left",
                    fontsize=7.5, color="#333333")

    fig.suptitle("Hydrogen Bond Occupancy Summary", fontsize=14, fontweight="bold")
    _savefig(fig, "05_hbond_frequency", output_dir, format)


# ---------------------------------------------------------------------------
# 6. PCA  – Free Energy Landscape (FEL) + time evolution + cluster overlay
# ---------------------------------------------------------------------------

def _boltzmann_fel(pc1: np.ndarray, pc2: np.ndarray,
                   bins: int = 80,
                   kT: float = 0.596) -> tuple:
    """
    Compute 2D free energy landscape from PCA data.
    F = -kT * ln(P)  (kT ≈ 0.596 kcal/mol at 300 K, or use 1 for dimensionless)
    """
    hist, xedges, yedges = np.histogram2d(pc1, pc2, bins=bins, density=True)
    hist = hist.T          # shape (bins, bins) with [pc2, pc1]
    hist = gaussian_filter(hist, sigma=1.5)

    with np.errstate(divide="ignore", invalid="ignore"):
        fel = -kT * np.log(np.where(hist > 0, hist, np.nan))
    fel -= np.nanmin(fel)  # set global minimum to 0

    xc = 0.5 * (xedges[:-1] + xedges[1:])
    yc = 0.5 * (yedges[:-1] + yedges[1:])
    return fel, xc, yc


def plot_pca(outputs: dict, dt_frame: float = 2.0,
             output_dir=None, format="pdf") -> None:
    if "pca_out" not in outputs:
        return
    data    = _load_cpptraj(outputs["pca_out"])
    frames  = data[:, 0]
    pc1     = data[:, 1]
    pc2     = data[:, 2]
    time_ns = _frames_to_ns(frames, dt_frame)

    fig = plt.figure(figsize=(16, 5.5))
    gs  = gridspec.GridSpec(1, 2, wspace=0.38, left=0.07, right=0.96)

    # ── Panel A: Free Energy Landscape ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    fel, xc, yc = _boltzmann_fel(pc1, pc2, bins=80, kT=0.596)
    XX, YY = np.meshgrid(xc, yc)

    # Smooth contourf + black isolines
    n_levels = 20
    vmax = np.nanpercentile(fel, 97)
    cf = ax1.contourf(XX, YY, fel,
                      levels=np.linspace(0, vmax, n_levels),
                      cmap="viridis_r", extend="max")
    ax1.contour(XX, YY, fel,
                levels=np.linspace(0, vmax, 8),
                colors="white", linewidths=0.6, alpha=0.5)

    # Mark global minimum
    min_idx = np.unravel_index(np.nanargmin(fel), fel.shape)
    ax1.scatter(xc[min_idx[1]], yc[min_idx[0]],
                marker="*", s=180, c="white", zorder=5,
                edgecolors="#333333", linewidth=0.5)
    ax1.text(xc[min_idx[1]], yc[min_idx[0]] + (pc2.max()-pc2.min())*0.04,
             "Min", ha="center", fontsize=8, color="black",
             fontweight="bold")

    cb2 = fig.colorbar(cf, ax=ax1, pad=0.02, fraction=0.046)
    cb2.set_label(r"$\Delta G$ (kcal/mol)", fontsize=9)
    cb2.ax.tick_params(labelsize=8)
    ax1.set_xlabel(r"PC1 ($\AA$)")
    ax1.set_ylabel(r"PC2 ($\AA$)")
    ax1.set_title("Free Energy Landscape", fontweight="bold")
    ax1.grid(False)

    # ── Panel B: Cluster overlay ─────────────────────────────────────────────
    clusters = None
    if "cnumvtime" in outputs:
        try:
            cdat     = _load_cpptraj(outputs["cnumvtime"], dtype=int)
            clusters = cdat[:, 1]
            n_clusters = int(clusters.max()) + 1
        except Exception:
            clusters = None

    ax2 = fig.add_subplot(gs[1])
    if clusters is not None and n_clusters <= 10:
        # Use high-contrast, perceptually distinct palette
        cluster_palette = [
            "#4477AA", "#EE6677", "#228833",
            "#CCBB44", "#66CCEE", "#AA3377",
            "#BBBBBB", "#EE8866", "#44BB99", "#AAAA00"
        ][:n_clusters]
        for cid in range(n_clusters):
            mask = clusters == cid
            ax2.scatter(pc1[mask], pc2[mask],
                        color=cluster_palette[cid],
                        s=5, alpha=0.75, edgecolors="none",
                        rasterized=True, label=f"C{cid}")
            cx, cy = np.median(pc1[mask]), np.median(pc2[mask])
            n_fr   = mask.sum()
            ax2.annotate(f"C{cid}\nn={n_fr}",
                         xy=(cx, cy),
                         fontsize=8, ha="center", va="center",
                         fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.25",
                                   fc=cluster_palette[cid],
                                   ec="white", alpha=0.85, lw=0.8),
                         color="white")
        ax2.legend(frameon=False, markerscale=2.5, fontsize=8,
                   loc="upper right", ncol=2)
    else:
        # Density fallback
        kde_vals = gaussian_kde(np.vstack([pc1, pc2]))(np.vstack([pc1, pc2]))
        sc3 = ax2.scatter(pc1, pc2, c=kde_vals, cmap="magma",
                          s=4, alpha=0.8, edgecolors="none", rasterized=True)
        cb3 = fig.colorbar(sc3, ax=ax2, pad=0.02, fraction=0.046)
        cb3.set_label("KDE density", fontsize=9)

    ax2.set_xlabel(r"PC1 ($\AA$)")
    ax2.set_ylabel(r"PC2 ($\AA$)")
    ax2.set_title("Cluster Assignments", fontweight="bold")

    fig.suptitle("Principal Component Analysis", fontsize=14, fontweight="bold")
    _savefig(fig, "06_pca", output_dir, format)


# ---------------------------------------------------------------------------
# 7. Clustering – population over time + pie summary
# ---------------------------------------------------------------------------

def plot_clustering(outputs: dict, dt_frame: float = 2.0,
                    output_dir=None, format="pdf") -> None:
    if "cpopvtime" not in outputs:
        return

    df = pd.read_csv(outputs["cpopvtime"], sep=r"\s+", comment="#")
    n_clusters = df.shape[1] - 1
    time_ns    = df.iloc[:, 0].values * dt_frame * 1e-3

    cluster_palette = [
        "#4477AA", "#EE6677", "#228833",
        "#CCBB44", "#66CCEE", "#AA3377",
        "#BBBBBB", "#EE8866", "#44BB99", "#AAAA00"
    ][:n_clusters]

    fig = plt.figure(figsize=(14, 5))
    gs  = gridspec.GridSpec(1, 2, width_ratios=[3, 1], wspace=0.3,
                            left=0.07, right=0.95)
    ax_pop = fig.add_subplot(gs[0])
    ax_pie = fig.add_subplot(gs[1])

    window = max(5, len(time_ns) // 60)
    for i in range(n_clusters):
        pop    = df.iloc[:, i + 1].values
        sm_pop = _rolling(pop, window)
        ax_pop.plot(time_ns, sm_pop, color=cluster_palette[i],
                    lw=2.0, label=f"Cluster {i}")
        ax_pop.fill_between(time_ns, 0, sm_pop,
                             color=cluster_palette[i], alpha=0.12)

    ax_pop.set_xlabel(r"Simulation Time (ns)")
    ax_pop.set_ylabel("Fractional Population")
    ax_pop.set_title("Cluster Population Dynamics", fontweight="bold")
    ax_pop.set_ylim(-0.02, 1.05)
    ax_pop.legend(frameon=False, ncol=2, loc="upper right")

    # Summary pie
    if "csummary" in outputs:
        try:
            cs = _load_cpptraj(outputs["csummary"])
            fracs = cs[:, 2][:n_clusters]
            labels = [f"C{i}\n({f:.1%})" for i, f in enumerate(fracs)]
            wedge_props = dict(linewidth=1.2, edgecolor="white")
            ax_pie.pie(fracs, labels=labels, colors=cluster_palette,
                       wedgeprops=wedge_props, textprops={"fontsize": 9},
                       labeldistance=1.12, startangle=90,
                       counterclock=False)
            ax_pie.set_title("Overall\nOccupancy", fontweight="bold", fontsize=10)
        except Exception:
            ax_pie.axis("off")
    else:
        ax_pie.axis("off")

    fig.suptitle("Cluster Analysis", fontsize=14, fontweight="bold")
    _savefig(fig, "07_clustering", output_dir, format)

# ---------------------------------------------------------------------------
# Master driver
# ---------------------------------------------------------------------------

from nexus.md.analyze.analyze_config import AnalyzeConfig

def generate_analysis_figures(cfg: AnalyzeConfig,
                     outputs: dict) -> None:
    """
    Generate all publication-quality figures from cpptraj outputs dictionary.
    """
    
    output_dir = cfg.common.output_dir
    dt_frame = cfg.figures.dt_frame
    format = cfg.figures.format

    steps = [
        ("RMSD + side KDE",                   plot_rmsd),
        ("RMSF coloured profile",             plot_rmsf),
        ("DSSP stacked area + heatmap",       plot_dssp),
        ("H-bond time-series panel",          plot_hbond_timeseries),
        ("H-bond occupancy bar charts",       plot_hbond_frequency),
        ("PCA Free energy landscape",         plot_pca),
        ("Cluster population dynamics",       plot_clustering),
    ]
    for name, fn in steps:
        print(f" Processing: {name}")
        try:
            fn(outputs, dt_frame=dt_frame, output_dir=output_dir, format=format)
        except Exception as exc:
            warnings.warn(f"    ✗ {name} failed: {exc}")

    print("\nDone.")
