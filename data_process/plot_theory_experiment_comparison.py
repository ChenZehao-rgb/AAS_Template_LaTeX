"""Process the theory-experiment rotor lift comparison workbook and plot figures.

The workbook ``data/理论-实验对比结果.xlsx`` already contains the fully
processed comparison (calibration-corrected experimental thrust, rpm-corrected
theoretical interpolation, and repeat/branch averaging), organised in four
sheets:

``误差汇总_逐工况``
    One row per (rpm, disk angle of attack) condition with pre-computed
    error statistics (bias, RMSE, max error, MAPE, all already normalised).
``分档曲线_可直接作图``
    Binned advance-ratio curves ready for plotting: one row per nominal
    advance-ratio level per condition, with the mean and standard deviation
    of the repeated/branch-averaged experimental C_T and the matched
    theoretical C_T.
``重复性与迟滞``
    Per-condition hysteresis (rising-branch-mean minus falling-branch-mean,
    for each of the two repeats) and the between-repeat spread.
``逐点明细``
    The underlying per-sample records used to build the two sheets above.

This script does not re-derive the comparison; it reads the workbook as the
single source of truth and produces the manuscript figures, a statistics
table, and a JSON summary used to write the results section.

Outputs
-------
Image/fig8_rotor_model_comparison.{pdf,png}
Image/fig9_rotor_model_diagnostics.{pdf,png}
data_process/model_validation_metrics.csv
data_process/model_validation_table.tex
data_process/model_validation_summary.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = ROOT / "data" / "理论-实验对比结果.xlsx"
DEFAULT_IMAGE_DIR = ROOT / "Image"
DEFAULT_OUTPUT_DIR = ROOT / "data_process"

RPM_LEVELS = (3000, 4000, 5000)
ANGLE_LEVELS = (0, 15, 30, 45, 60, 75, 90)

# Seven samples from viridis: perceptually uniform and color-vision friendly.
ANGLE_COLORS = {
    angle: color
    for angle, color in zip(
        ANGLE_LEVELS,
        mpl.colormaps["viridis"](np.linspace(0.05, 0.95, len(ANGLE_LEVELS))),
    )
}
RPM_COLORS = {3000: "#0077BB", 4000: "#EE7733", 5000: "#009988"}
RPM_MARKERS = {3000: "o", 4000: "s", 5000: "^"}


def configure_matplotlib() -> None:
    """Set compact, publication-oriented matplotlib defaults."""
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "custom",
            "mathtext.rm": "Times New Roman",
            "mathtext.it": "Times New Roman:italic",
            "mathtext.bf": "Times New Roman:bold",
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "figure.dpi": 150,
            "savefig.dpi": 400,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "axes.linewidth": 0.7,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "xtick.minor.visible": True,
            "ytick.minor.visible": True,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.minor.width": 0.5,
            "ytick.minor.width": 0.5,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def load_sheets(workbook_path: Path) -> dict[str, pd.DataFrame]:
    """Read the four pre-processed sheets from the comparison workbook."""
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")
    xl = pd.ExcelFile(workbook_path)
    names = {
        "summary": "误差汇总_逐工况",
        "curves": "分档曲线_可直接作图",
        "hysteresis": "重复性与迟滞",
        "points": "逐点明细",
    }
    missing = [sheet for sheet in names.values() if sheet not in xl.sheet_names]
    if missing:
        raise KeyError(f"Missing expected sheets in workbook: {missing}")
    return {key: xl.parse(sheet) for key, sheet in names.items()}


def regression_stats(curves: pd.DataFrame) -> dict[str, float | int]:
    """Agreement statistics for the binned theory/experiment C_T pairs."""
    theory = curves["C_T_theory"].to_numpy(dtype=float)
    exp = curves["C_T_exp"].to_numpy(dtype=float)
    residual = exp - theory

    slope, intercept = np.polyfit(theory, exp, 1)
    pearson_r = float(np.corrcoef(theory, exp)[0, 1])
    sse = float(np.sum(residual**2))
    sst = float(np.sum((exp - exp.mean()) ** 2))
    r_squared = 1.0 - sse / sst
    covariance = float(np.mean((theory - theory.mean()) * (exp - exp.mean())))
    ccc = 2.0 * covariance / (
        float(np.var(theory)) + float(np.var(exp)) + float((theory.mean() - exp.mean()) ** 2)
    )

    return {
        "n": int(len(curves)),
        "slope": float(slope),
        "intercept": float(intercept),
        "pearson_r": pearson_r,
        "r_squared": float(r_squared),
        "ccc": float(ccc),
        "bias": float(np.mean(residual)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "negative_residual_fraction": float(np.mean(residual < 0)),
        "within_0_0005_fraction": float(np.mean(np.abs(residual) <= 0.0005)),
        "within_0_001_fraction": float(np.mean(np.abs(residual) <= 0.001)),
    }


def _pooled_point_stats(points: pd.DataFrame) -> dict[str, float | int]:
    """Pool per-sample errors the same way the workbook's per-condition rows do.

    Bias/RMSE/max-error use every sample in the group; MAPE follows the
    workbook convention of excluding samples flagged ``thrust_ok == False``
    (extrapolated beyond the theoretical advance-ratio range).
    """
    mape_subset = points.loc[points["thrust_ok"] == True, "err_rel_pct"]  # noqa: E712
    return {
        "n": int(len(points)),
        "bias_pct": float(points["err_norm_pct"].mean()),
        "rmse_norm_pct": float(np.sqrt(np.mean(points["err_norm_pct"].to_numpy(dtype=float) ** 2))),
        "maxerr_norm_pct": float(points["err_norm_pct"].abs().max()),
        "mape_pct": float(mape_subset.abs().mean()),
        "rmse_ct": float(np.sqrt(np.mean(points["err_abs"].to_numpy(dtype=float) ** 2))),
    }


def build_point_metrics(points: pd.DataFrame) -> pd.DataFrame:
    """Return one pooled-error row per rotational speed plus an overall row."""
    rows: list[dict[str, float | int | str]] = []
    for rpm in RPM_LEVELS:
        rows.append({"group": f"{rpm} rpm", **_pooled_point_stats(points.loc[points["rpm_nom"] == rpm])})
    rows.append({"group": "Overall", **_pooled_point_stats(points)})
    return pd.DataFrame(rows)


def repeatability_stats(hysteresis: pd.DataFrame) -> dict[str, float]:
    """Summarize repeat-to-repeat and rising/falling hysteresis spread."""
    return {
        "mean_abs_hysteresis_run1": float(hysteresis["hyst_run1"].abs().mean()),
        "mean_abs_hysteresis_run2": float(hysteresis["hyst_run2"].abs().mean()),
        "mean_run_diff_std": float(hysteresis["run_diff_std"].mean()),
        "max_run_diff_std": float(hysteresis["run_diff_std"].max()),
    }


def _save_figure(fig: mpl.figure.Figure, base_path: Path) -> None:
    fig.savefig(base_path.with_suffix(".pdf"))
    fig.savefig(base_path.with_suffix(".png"), dpi=400)
    plt.close(fig)


def plot_comparison(curves: pd.DataFrame, image_dir: Path) -> None:
    """Generate the two-row comparison figure.

    Row (a): three panels, one per rotational speed, each showing the
    theoretical C_T curves against the binned experimental means (error bars
    = SD across the four averaged branches), colored by disk angle of attack.
    Row (b): two pooled panels combining all three rotational speeds —
    (b1) an error-bar plot of the per-angle residual mean +/- SD for each
    rotational speed, and (b2) a single scatter of every binned point's
    residual against advance ratio.
    """
    curves = curves.assign(residual=curves["C_T_exp"] - curves["C_T_theory"])

    j_min, j_max = curves["J"].min(), curves["J"].max()
    ct_min = min(curves["C_T_exp"].min(), curves["C_T_theory"].min())
    ct_max = max(curves["C_T_exp"].max(), curves["C_T_theory"].max())
    ct_padding = 0.06 * (ct_max - ct_min)
    residual_limit = 1.08 * curves["residual"].abs().max()

    fig = plt.figure(figsize=(7.15, 5.55))
    gs = fig.add_gridspec(nrows=2, ncols=6, height_ratios=[1.12, 0.9], hspace=0.46, wspace=0.65)
    comparison_axes = [fig.add_subplot(gs[0, 2 * i : 2 * i + 2]) for i in range(3)]
    for ax in comparison_axes[1:]:
        ax.sharey(comparison_axes[0])
    errorbar_ax = fig.add_subplot(gs[1, 0:3])
    total_residual_ax = fig.add_subplot(gs[1, 3:6])

    # --- Row (a): C_T-J comparison, one panel per rotational speed ---
    for panel_index, (ax, rpm) in enumerate(zip(comparison_axes, RPM_LEVELS)):
        rpm_data = curves.loc[curves["rpm_nom"] == rpm]
        for angle in ANGLE_LEVELS:
            subset = rpm_data.loc[rpm_data["alpha_deg"] == angle].sort_values("J")
            if subset.empty:
                continue
            color = ANGLE_COLORS[angle]
            ax.plot(subset["J"], subset["C_T_theory"], color=color, linewidth=1.15, zorder=2)
            ax.errorbar(
                subset["J"],
                subset["C_T_exp"],
                yerr=subset["C_T_exp_std"],
                fmt="o",
                markersize=3.6,
                markerfacecolor="white",
                markeredgecolor=color,
                markeredgewidth=0.8,
                ecolor=color,
                elinewidth=0.55,
                capsize=1.4,
                capthick=0.55,
                zorder=3,
            )
        ax.set_xlim(j_min - 0.01, j_max + 0.01)
        ax.set_ylim(ct_min - ct_padding, ct_max + ct_padding)
        ax.grid(axis="y", color="0.88", linewidth=0.45, linestyle=":", zorder=0)
        ax.set_xlabel(r"Advance ratio, $J$")
        if panel_index == 0:
            ax.set_ylabel(r"$C_T$")
        else:
            plt.setp(ax.get_yticklabels(), visible=False)
        ax.text(0.06, 0.96, f"{rpm} rpm", transform=ax.transAxes, ha="left", va="top", fontsize=8.5)
    comparison_axes[0].text(
        -0.34, 1.05, "(a)", transform=comparison_axes[0].transAxes,
        ha="left", va="bottom", fontsize=10.5, fontweight="bold",
    )

    # --- Row (b1): per-angle residual mean +/- SD, one series per rotational speed ---
    for rpm in RPM_LEVELS:
        rpm_data = curves.loc[curves["rpm_nom"] == rpm]
        means = [rpm_data.loc[rpm_data["alpha_deg"] == angle, "residual"].mean() for angle in ANGLE_LEVELS]
        stds = [rpm_data.loc[rpm_data["alpha_deg"] == angle, "residual"].std(ddof=1) for angle in ANGLE_LEVELS]
        errorbar_ax.errorbar(
            ANGLE_LEVELS,
            means,
            yerr=stds,
            color=RPM_COLORS[rpm],
            marker=RPM_MARKERS[rpm],
            markersize=4.2,
            markerfacecolor="white",
            markeredgewidth=0.9,
            linewidth=1.15,
            capsize=2.2,
            capthick=0.7,
            elinewidth=0.7,
            label=f"{rpm} rpm",
        )
    errorbar_ax.axhline(0.0, color="0.25", linewidth=0.8, linestyle="--", zorder=1)
    errorbar_ax.set_xticks(ANGLE_LEVELS)
    errorbar_ax.set_xlabel(r"Disk angle of attack, $\alpha_p$ ($^\circ$)")
    errorbar_ax.set_ylabel(r"$C_{T,\mathrm{exp}}-C_{T,\mathrm{theory}}$")
    errorbar_ax.grid(axis="y", color="0.88", linewidth=0.45, linestyle=":", zorder=0)
    errorbar_ax.legend(frameon=False, loc="lower left", fontsize=7, handletextpad=0.4)
    errorbar_ax.text(
        0.04, 0.96, "Per-angle residual mean $\\pm$ SD", transform=errorbar_ax.transAxes,
        ha="left", va="top", fontsize=7.8,
    )

    # --- Row (b2): pooled residual scatter, all rotational speeds combined ---
    for angle in ANGLE_LEVELS:
        subset = curves.loc[curves["alpha_deg"] == angle]
        total_residual_ax.scatter(
            subset["J"],
            subset["residual"],
            s=14,
            facecolors=ANGLE_COLORS[angle],
            edgecolors="white",
            linewidths=0.2,
            alpha=0.85,
            zorder=2,
        )
    total_residual_ax.axhline(0.0, color="0.25", linewidth=0.8, linestyle="--", zorder=1)
    total_residual_ax.set_xlim(j_min - 0.01, j_max + 0.01)
    total_residual_ax.set_ylim(-residual_limit, residual_limit)
    total_residual_ax.set_xlabel(r"Advance ratio, $J$")
    total_residual_ax.set_ylabel(r"$C_{T,\mathrm{exp}}-C_{T,\mathrm{theory}}$")
    total_residual_ax.grid(axis="y", color="0.88", linewidth=0.45, linestyle=":", zorder=0)
    total_residual_ax.text(
        0.04, 0.96, "Pooled residuals, all rotational speeds", transform=total_residual_ax.transAxes,
        ha="left", va="top", fontsize=7.8,
    )
    errorbar_ax.text(
        -0.16, 1.08, "(b)", transform=errorbar_ax.transAxes,
        ha="left", va="bottom", fontsize=10.5, fontweight="bold",
    )

    angle_handles = [
        Line2D([0], [0], color=ANGLE_COLORS[angle], lw=1.8, label=rf"${angle}^\circ$")
        for angle in ANGLE_LEVELS
    ]
    style_handles = [
        Line2D([0], [0], color="0.15", lw=1.25, label="Theory"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="0.15",
            markerfacecolor="white",
            markeredgewidth=0.9,
            lw=0,
            label=r"Experiment mean $\pm$ SD",
        ),
    ]
    fig.legend(
        handles=angle_handles,
        title=r"Disk angle of attack, $\alpha_p$ (rows a and b2)",
        loc="lower center",
        bbox_to_anchor=(0.34, -0.03),
        ncol=4,
        frameon=False,
        columnspacing=1.2,
        handlelength=1.7,
        title_fontsize=7.5,
        fontsize=7.5,
    )
    fig.legend(
        handles=style_handles,
        loc="lower center",
        bbox_to_anchor=(0.83, -0.015),
        ncol=1,
        frameon=False,
        handlelength=1.8,
        labelspacing=0.35,
        fontsize=7.5,
    )
    fig.subplots_adjust(left=0.085, right=0.985, top=0.97, bottom=0.185)
    _save_figure(fig, image_dir / "fig8_rotor_model_comparison")


def plot_diagnostics(
    curves: pd.DataFrame, regression: dict[str, float | int], image_dir: Path
) -> None:
    """Generate the theory-experiment parity plot."""
    fig, parity_ax = plt.subplots(figsize=(3.6, 3.15))

    for rpm in RPM_LEVELS:
        subset = curves.loc[curves["rpm_nom"] == rpm]
        parity_ax.scatter(
            subset["C_T_theory"],
            subset["C_T_exp"],
            s=15,
            marker=RPM_MARKERS[rpm],
            facecolors="none",
            edgecolors=RPM_COLORS[rpm],
            linewidths=0.65,
            alpha=0.72,
            label=f"{rpm} rpm",
        )

    lower = min(curves["C_T_theory"].min(), curves["C_T_exp"].min())
    upper = max(curves["C_T_theory"].max(), curves["C_T_exp"].max())
    padding = 0.05 * (upper - lower)
    line_limits = (lower - padding, upper + padding)
    parity_ax.plot(line_limits, line_limits, color="0.2", lw=1.0, linestyle="--", label="1:1 line")
    parity_ax.set_xlim(line_limits)
    parity_ax.set_ylim(line_limits)
    parity_ax.set_aspect("equal", adjustable="box")
    parity_ax.set_xlabel(r"Theoretical $C_T$")
    parity_ax.set_ylabel(r"Experimental $C_T$")
    parity_ax.grid(color="0.88", linewidth=0.45, linestyle=":")
    parity_ax.legend(frameon=False, loc="upper left", handletextpad=0.4)

    parity_ax.text(
        0.98,
        0.03,
        "\n".join(
            [
                rf"$C_{{T,\mathrm{{exp}}}}={regression['slope']:.3f}C_{{T,\mathrm{{theory}}}}{regression['intercept']:+.4f}$",
                rf"$R^2={regression['r_squared']:.3f}$, CCC$={regression['ccc']:.3f}$",
                rf"$N={int(regression['n'])}$",
            ]
        ),
        transform=parity_ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.3,
        bbox={"facecolor": "white", "edgecolor": "0.75", "linewidth": 0.5, "alpha": 0.9},
    )

    fig.subplots_adjust(left=0.17, right=0.97, top=0.96, bottom=0.17)
    _save_figure(fig, image_dir / "fig9_rotor_model_diagnostics")


def write_outputs(
    sheets: dict[str, pd.DataFrame],
    point_metrics: pd.DataFrame,
    regression: dict[str, float | int],
    repeatability: dict[str, float],
    output_dir: Path,
) -> None:
    """Write auditable numeric summaries and the LaTeX table body."""
    point_metrics.to_csv(output_dir / "model_validation_metrics.csv", index=False, encoding="utf-8-sig")
    sheets["curves"].to_csv(
        output_dir / "model_validation_four_branch_mean.csv", index=False, encoding="utf-8-sig"
    )

    overall = point_metrics.loc[point_metrics["group"] == "Overall"].iloc[0]
    summary = {
        "source_workbook": str(DEFAULT_WORKBOOK.relative_to(ROOT)),
        "n_conditions": int(len(sheets["summary"])),
        "n_curve_points": int(len(sheets["curves"])),
        "n_raw_samples": int(len(sheets["points"])),
        "pooled_point_metrics_overall": {
            k: (int(v) if k == "n" else float(v)) for k, v in overall.items() if k != "group"
        },
        "regression_on_binned_curves": regression,
        "repeatability": repeatability,
    }
    (output_dir / "model_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for _, row in point_metrics.iterrows():
        label = "全部" if row["group"] == "Overall" else row["group"].replace(" rpm", "")
        rows.append(
            f"{label} & {int(row['n'])} & {row['bias_pct']:.2f}\\% & {row['rmse_norm_pct']:.2f}\\% & "
            f"{row['maxerr_norm_pct']:.2f}\\% & {row['mape_pct']:.2f}\\% & {row['rmse_ct']:.5f} \\\\"
        )
    table_tex = "\n".join(
        [
            r"\begin{center}",
            r"\vbox{\centering{\small 表4\quad 旋翼升力模型精度统计",
            r"\\ Table\,4 \quad Accuracy statistics of the rotor lift model}\vskip2mm",
            r"{\scriptsize\centering",
            r"\resizebox{\columnwidth}{!}{%",
            r"\begin{tabular}{crrrrrr}",
            r"\toprule",
            r"转速/(r/min) & $N$ & Bias & RMSE$_{\mathrm{norm}}$ & MaxErr$_{\mathrm{norm}}$ & MAPE & RMSE($C_T$) \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}}}",
            r"}",
            r"\end{center}",
        ]
    )
    (output_dir / "model_validation_table.tex").write_text(table_tex + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK, help="Input xlsx workbook")
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR, help="Figure output directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Numeric/table output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workbook_path = args.workbook.resolve()
    image_dir = args.image_dir.resolve()
    output_dir = args.output_dir.resolve()
    image_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    configure_matplotlib()
    sheets = load_sheets(workbook_path)

    regression = regression_stats(sheets["curves"])
    point_metrics = build_point_metrics(sheets["points"])
    repeatability = repeatability_stats(sheets["hysteresis"])

    plot_comparison(sheets["curves"], image_dir)
    plot_diagnostics(sheets["curves"], regression, image_dir)
    write_outputs(sheets, point_metrics, regression, repeatability, output_dir)

    print(point_metrics.to_string(index=False))
    print(json.dumps(regression, indent=2))
    print(json.dumps(repeatability, indent=2))
    print(f"Figures written to: {image_dir}")
    print(f"Tables and summaries written to: {output_dir}")


if __name__ == "__main__":
    main()
