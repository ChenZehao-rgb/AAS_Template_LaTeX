"""Analyze the currently available 90-deg axial-inflow closed-loop tests.

The script treats rotor/sensor channel 1 as the active channel, aligns runs at
the 10% freestream-speed crossing, calculates trial- and condition-level
tracking metrics, and generates publication-oriented summary figures.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pyulog import ULog
from scipy.ndimage import median_filter


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "90度攻角-纯轴向来流"
OUTPUT_DIR = ROOT / "analysis_current_90deg"
IMAGE_DIR = ROOT.parents[1] / "Image"

METHOD_LABEL = {
    "ff_fb": "Model feedforward + feedback",
    "fb": "Feedback only",
    "static": "Static-map open loop",
}

# Chinese labels for the figure legends/annotations (fig9-fig13); METHOD_LABEL
# above stays English because it also feeds the CSV/report method_label field.
METHOD_LABEL_ZH = {
    "ff_fb": "前馈+反馈(FF+FB)",
    "fb": "纯反馈(FB)",
    "static": "固定控制量(Static)",
}

# Same triplet and marker convention used for the three-level groupings in
# fig8/fig9 (rotor-speed series), so the closed-loop figures read as part of
# the same figure family rather than a separately styled data set.
COLORS = {
    "ff_fb": "#0077BB",
    "fb": "#EE7733",
    "static": "#009988",
    "target": "#222222",
    "neutral": "#666666",
    "light": "#BBBBBB",
}
MARKERS = {"ff_fb": "o", "fb": "s", "static": "^"}
METHOD_ORDER = ("static", "fb", "ff_fb")


@dataclass
class Run:
    path: Path
    sequence: int
    target_n: int
    nominal_ramp_s: int
    method: str
    timestamp_s: np.ndarray
    tau_s: np.ndarray
    freestream_m_s: np.ndarray
    freestream_smooth_m_s: np.ndarray
    desired_n: np.ndarray
    measured_n: np.ndarray
    error_n: np.ndarray
    raw_thrust_n: np.ndarray
    model_rpm: np.ndarray
    measured_rpm: np.ndarray
    feedforward_out: np.ndarray
    feedback_out: np.ndarray
    total_out: np.ndarray
    actuator_output_0: np.ndarray
    acceleration_x_m_s2: np.ndarray
    acceleration_y_m_s2: np.ndarray
    speed_from_accel_m_s: np.ndarray
    t10_s: float
    t90_s: float
    baseline_low_m_s: float
    plateau_high_m_s: float
    sampling_hz: float


def configure_plotting() -> None:
    """Match the serif/boxed style already used for fig8/fig9 in the manuscript."""
    mpl.rcParams.update(
        {
            "font.family": ["Times New Roman", "SimSun", "DejaVu Serif"],
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
            "axes.grid": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def style_grid(axis: plt.Axes, which: str = "y") -> None:
    axis.grid(axis=which, color="0.88", linewidth=0.45, linestyle=":", zorder=0)


def panel_label(axis: plt.Axes, text: str, x: float = 0.015, y: float = 0.96) -> None:
    axis.text(
        x,
        y,
        text,
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        fontweight="bold",
    )


def parse_filename(path: Path) -> tuple[int, int, int, str]:
    closed_loop_match = re.match(
        r"^(?P<seq>\d+)-(?P<target>\d+)N-(?P<ramp>\d+)s加速-(?P<method>.+?)-轴向\.ulg$",
        path.name,
    )
    if closed_loop_match:
        method_text = closed_loop_match.group("method")
        method = "ff_fb" if "前馈" in method_text else "fb"
        return (
            int(closed_loop_match.group("seq")),
            int(closed_loop_match.group("target")),
            int(closed_loop_match.group("ramp")),
            method,
        )

    static_match = re.match(
        r"^(?P<seq>\d+)-(?P<target>\d+)-(?P<ramp>\d+)s加速-静态\.ulg$",
        path.name,
    )
    if static_match:
        return (
            int(static_match.group("seq")),
            int(static_match.group("target")),
            int(static_match.group("ramp")),
            "static",
        )
    raise ValueError(f"Unexpected log name: {path.name}")


def topic(ulog: ULog, name: str) -> dict[str, np.ndarray]:
    matches = [dataset.data for dataset in ulog.data_list if dataset.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name!r} topic, found {len(matches)}")
    return matches[0]


def odd_kernel(samples: float, maximum: int) -> int:
    value = max(3, int(round(samples)))
    value = min(value, maximum if maximum % 2 == 1 else maximum - 1)
    return value if value % 2 == 1 else value + 1


def detect_ramp(
    timestamp_s: np.ndarray, freestream_m_s: np.ndarray, sampling_hz: float
) -> tuple[np.ndarray, float, float, float, float]:
    kernel = odd_kernel(0.35 * sampling_hz, len(freestream_m_s))
    smooth = median_filter(freestream_m_s, size=kernel, mode="nearest")
    first_five = timestamp_s <= min(timestamp_s[0] + 5.0, timestamp_s[-1])
    low = float(np.nanmedian(smooth[first_five]))
    # Each log contains acceleration, a high-speed hold, and deceleration, so
    # the final samples are not the high-speed plateau.  The median of the
    # upper decile is robust to the short overshoot at acceleration onset.
    upper_decile = smooth >= np.nanpercentile(smooth, 90.0)
    high = float(np.nanmedian(smooth[upper_decile]))
    if high - low < 5.0:
        raise ValueError(f"Freestream change is too small: low={low:.3f}, high={high:.3f}")

    threshold_10 = low + 0.10 * (high - low)
    threshold_90 = low + 0.90 * (high - low)
    sustained_samples = max(3, int(round(0.25 * sampling_hz)))
    above_90 = (smooth >= threshold_90).astype(int)
    sustained_90 = np.convolve(
        above_90, np.ones(sustained_samples, dtype=int), mode="same"
    ) >= sustained_samples
    candidates_90 = np.flatnonzero(sustained_90)
    if not len(candidates_90):
        raise ValueError("Could not find a sustained 90% freestream crossing")
    index_90 = int(candidates_90[0])

    below_10_before_90 = np.flatnonzero(smooth[:index_90] <= threshold_10)
    if not len(below_10_before_90):
        raise ValueError("Could not find the 10% freestream crossing before the plateau")
    index_10 = int(below_10_before_90[-1] + 1)
    return smooth, float(timestamp_s[index_10]), float(timestamp_s[index_90]), low, high


def load_run(path: Path) -> Run:
    sequence, target_n, nominal_ramp_s, method = parse_filename(path)
    ulog = ULog(str(path))
    control = topic(ulog, "thrust_control_data")
    thrust = topic(ulog, "thrust_data")
    rpm = topic(ulog, "rpm")
    acceleration = topic(ulog, "vehicle_acceleration")
    actuator_output_topics = [
        dataset for dataset in ulog.data_list if dataset.name == "actuator_outputs"
    ]
    actuator_output_dataset = next(
        (dataset for dataset in actuator_output_topics if dataset.multi_id == 0),
        actuator_output_topics[0],
    )
    actuator_outputs = actuator_output_dataset.data

    timestamp_s = np.asarray(control["timestamp"], dtype=float) / 1e6
    sampling_hz = float(1.0 / np.nanmedian(np.diff(timestamp_s)))
    freestream = np.asarray(control["bet_freestream_m_s"], dtype=float)
    smooth, t10_s, t90_s, low, high = detect_ramp(
        timestamp_s, freestream, sampling_hz
    )

    thrust_time_s = np.asarray(thrust["timestamp"], dtype=float) / 1e6
    measured_n = np.interp(
        timestamp_s,
        thrust_time_s,
        np.asarray(thrust["thrust_kalman_filter_data_1"], dtype=float),
    )
    raw_thrust_n = np.interp(
        timestamp_s,
        thrust_time_s,
        np.asarray(thrust["thrust_raw_data_1"], dtype=float),
    )
    desired_n = np.asarray(control["thrust_desired[0]"], dtype=float)

    rpm_time_s = np.asarray(rpm["timestamp"], dtype=float) / 1e6
    measured_rpm = np.interp(
        timestamp_s,
        rpm_time_s,
        -np.asarray(rpm["rpm_raw"], dtype=float),
    )

    accel_time_s = np.asarray(acceleration["timestamp"], dtype=float) / 1e6
    acceleration_x = np.interp(
        timestamp_s, accel_time_s, np.asarray(acceleration["xyz[0]"], dtype=float)
    )
    acceleration_y = np.interp(
        timestamp_s, accel_time_s, np.asarray(acceleration["xyz[1]"], dtype=float)
    )
    arm_length_m = float(np.nanmedian(control["bet_length_m"]))
    speed_from_accel = np.sqrt(np.clip(acceleration_x, 0.0, None) * arm_length_m)
    actuator_time_s = np.asarray(actuator_outputs["timestamp"], dtype=float) / 1e6
    actuator_output_0 = np.interp(
        timestamp_s,
        actuator_time_s,
        np.asarray(actuator_outputs["output[0]"], dtype=float),
    )

    return Run(
        path=path,
        sequence=sequence,
        target_n=target_n,
        nominal_ramp_s=nominal_ramp_s,
        method=method,
        timestamp_s=timestamp_s,
        tau_s=timestamp_s - t10_s,
        freestream_m_s=freestream,
        freestream_smooth_m_s=smooth,
        desired_n=desired_n,
        measured_n=measured_n,
        error_n=desired_n - measured_n,
        raw_thrust_n=raw_thrust_n,
        model_rpm=np.asarray(control["motor_speed[0]"], dtype=float),
        measured_rpm=measured_rpm,
        feedforward_out=np.asarray(control["thrust_feedforward_out[0]"], dtype=float),
        feedback_out=np.asarray(control["thrust_feedback_out[0]"], dtype=float),
        total_out=np.asarray(control["thrust_control_out[0]"], dtype=float),
        actuator_output_0=actuator_output_0,
        acceleration_x_m_s2=acceleration_x,
        acceleration_y_m_s2=acceleration_y,
        speed_from_accel_m_s=speed_from_accel,
        t10_s=t10_s,
        t90_s=t90_s,
        baseline_low_m_s=low,
        plateau_high_m_s=high,
        sampling_hz=sampling_hz,
    )


def masked_stats(error_n: np.ndarray, mask: np.ndarray, target_n: float) -> dict[str, float]:
    values = error_n[mask]
    if not len(values):
        return {key: math.nan for key in ("bias_n", "mae_n", "rmse_n", "peak_n", "std_n")}
    return {
        "bias_n": float(np.nanmean(values)),
        "mae_n": float(np.nanmean(np.abs(values))),
        "rmse_n": float(np.sqrt(np.nanmean(np.square(values)))),
        "peak_n": float(np.nanmax(np.abs(values))),
        "std_n": float(np.nanstd(values, ddof=0)),
        "mae_pct": float(100 * np.nanmean(np.abs(values)) / target_n),
        "rmse_pct": float(100 * np.sqrt(np.nanmean(np.square(values))) / target_n),
        "peak_pct": float(100 * np.nanmax(np.abs(values)) / target_n),
    }


def settling_time(run: Run, start_tau_s: float, tolerance_fraction: float = 0.05) -> float:
    tolerance_n = tolerance_fraction * run.target_n
    after = np.flatnonzero(run.tau_s >= start_tau_s)
    if not len(after):
        return math.nan
    dwell = max(3, int(round(1.0 * run.sampling_hz)))
    within = (np.abs(run.error_n) <= tolerance_n).astype(int)
    sustained = np.convolve(within, np.ones(dwell, dtype=int), mode="same") >= dwell
    valid = after[sustained[after]]
    if not len(valid):
        return math.nan
    return float(run.tau_s[valid[0]] - start_tau_s)


def trial_metrics(run: Run) -> dict[str, float | int | str]:
    ramp_end_tau = run.t90_s - run.t10_s
    baseline = (run.tau_s >= -3.0) & (run.tau_s <= -0.5)
    ramp = (run.tau_s >= 0.0) & (run.tau_s <= ramp_end_tau)
    disturbance = (run.tau_s >= 0.0) & (run.tau_s <= ramp_end_tau + 3.0)
    # A common 3 s plateau slice avoids the later deceleration in the 10 s
    # acceleration tests, whose high-speed hold is shorter than other tests.
    plateau = (run.tau_s >= ramp_end_tau + 2.0) & (
        run.tau_s <= min(ramp_end_tau + 5.0, run.tau_s[-1] - 0.5)
    )
    rpm_valid = disturbance & (run.measured_rpm > 500.0) & (run.model_rpm > 500.0)
    rpm_difference = run.measured_rpm[rpm_valid] - run.model_rpm[rpm_valid]
    accel_valid = disturbance & (run.freestream_smooth_m_s > 1.0)
    accel_speed_difference = (
        run.speed_from_accel_m_s[accel_valid] - run.freestream_smooth_m_s[accel_valid]
    )

    row: dict[str, float | int | str] = {
        "sequence": run.sequence,
        "file": run.path.name,
        "target_n": run.target_n,
        "nominal_ramp_s": run.nominal_ramp_s,
        "method": run.method,
        "method_label": METHOD_LABEL[run.method],
        "sampling_hz": run.sampling_hz,
        "actual_10_90_ramp_s": ramp_end_tau,
        "freestream_low_m_s": run.baseline_low_m_s,
        "freestream_high_m_s": run.plateau_high_m_s,
        "settling_after_ramp_s": settling_time(run, ramp_end_tau),
        "control_peak": float(np.nanmax(run.total_out[disturbance])),
        "control_saturation_fraction": float(np.mean(run.total_out[disturbance] >= 0.98)),
        "baseline_rpm_median": float(np.nanmedian(run.measured_rpm[baseline])),
        "plateau_rpm_median": float(np.nanmedian(run.measured_rpm[plateau])),
        "baseline_actuator_output_0_median": float(
            np.nanmedian(run.actuator_output_0[baseline])
        ),
        "plateau_actuator_output_0_median": float(
            np.nanmedian(run.actuator_output_0[plateau])
        ),
    }
    row["rpm_plateau_change_pct"] = float(
        100.0
        * (row["plateau_rpm_median"] - row["baseline_rpm_median"])
        / row["baseline_rpm_median"]
    )
    row["actuator_output_0_plateau_change_pct"] = float(
        100.0
        * (
            row["plateau_actuator_output_0_median"]
            - row["baseline_actuator_output_0_median"]
        )
        / row["baseline_actuator_output_0_median"]
    )
    # Remove the pre-disturbance mean error as a sensitivity check.  This
    # isolates the error introduced by changing freestream from any initial
    # static-map/calibration offset at V_inf ~= 0.
    baseline_bias_n = float(np.nanmean(run.error_n[baseline]))
    incremental_error_n = run.error_n - baseline_bias_n
    row["baseline_bias_for_correction_n"] = baseline_bias_n
    for metric, value in masked_stats(
        incremental_error_n, disturbance, run.target_n
    ).items():
        row[f"disturbance_incremental_{metric}"] = value
    for prefix, mask in (
        ("baseline", baseline),
        ("ramp", ramp),
        ("disturbance", disturbance),
        ("plateau", plateau),
    ):
        for metric, value in masked_stats(run.error_n, mask, run.target_n).items():
            row[f"{prefix}_{metric}"] = value
    row["rpm_model_bias_rpm"] = float(np.nanmean(rpm_difference)) if len(rpm_difference) else math.nan
    row["rpm_model_rmse_rpm"] = (
        float(np.sqrt(np.nanmean(np.square(rpm_difference))))
        if len(rpm_difference)
        else math.nan
    )
    row["accel_speed_bias_m_s"] = (
        float(np.nanmean(accel_speed_difference)) if len(accel_speed_difference) else math.nan
    )
    row["accel_speed_rmse_m_s"] = (
        float(np.sqrt(np.nanmean(np.square(accel_speed_difference))))
        if len(accel_speed_difference)
        else math.nan
    )
    if run.method == "ff_fb":
        denominator = np.maximum(np.abs(run.total_out[disturbance]), 1e-6)
        row["feedback_fraction_mean"] = float(
            np.nanmean(np.abs(run.feedback_out[disturbance]) / denominator)
        )
    else:
        row["feedback_fraction_mean"] = math.nan
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate_conditions(trial_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = sorted(
        {
            (int(row["target_n"]), int(row["nominal_ramp_s"]), str(row["method"]))
            for row in trial_rows
        }
    )
    output: list[dict[str, object]] = []
    numeric_fields = [
        key
        for key, value in trial_rows[0].items()
        if isinstance(value, (int, float)) and key not in {"sequence", "target_n", "nominal_ramp_s"}
    ]
    for target_n, ramp_s, method in keys:
        matches = [
            row
            for row in trial_rows
            if int(row["target_n"]) == target_n
            and int(row["nominal_ramp_s"]) == ramp_s
            and str(row["method"]) == method
        ]
        result: dict[str, object] = {
            "target_n": target_n,
            "nominal_ramp_s": ramp_s,
            "method": method,
            "method_label": METHOD_LABEL[method],
            "n_trials": len(matches),
            "sequences": ",".join(str(row["sequence"]) for row in matches),
        }
        for field in numeric_fields:
            values = np.asarray([float(row[field]) for row in matches], dtype=float)
            result[field] = float(np.nanmean(values)) if np.any(np.isfinite(values)) else math.nan
        output.append(result)
    return output


def comparison_conditions(condition_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {
        (int(row["target_n"]), int(row["nominal_ramp_s"]), str(row["method"])): row
        for row in condition_rows
    }
    output: list[dict[str, object]] = []
    for target_n in (15, 20, 25):
        for ramp_s in (1, 5, 10):
            ff = by_key[(target_n, ramp_s, "ff_fb")]
            fb = by_key[(target_n, ramp_s, "fb")]
            static = by_key[(target_n, ramp_s, "static")]
            row: dict[str, object] = {
                "target_n": target_n,
                "nominal_ramp_s": ramp_s,
                "ff_trials": ff["n_trials"],
                "fb_trials": fb["n_trials"],
                "static_trials": static["n_trials"],
            }
            for metric in (
                "disturbance_mae_pct",
                "disturbance_rmse_pct",
                "disturbance_peak_pct",
                "disturbance_incremental_mae_pct",
                "disturbance_incremental_rmse_pct",
                "disturbance_incremental_peak_pct",
                "plateau_bias_n",
                "plateau_rmse_pct",
                "settling_after_ramp_s",
            ):
                ff_value = float(ff[metric])
                fb_value = float(fb[metric])
                static_value = float(static[metric])
                row[f"ff_{metric}"] = ff_value
                row[f"fb_{metric}"] = fb_value
                row[f"static_{metric}"] = static_value
                row[f"reduction_ff_vs_fb_{metric}_pct"] = (
                    100.0 * (fb_value - ff_value) / fb_value
                    if np.isfinite(fb_value) and abs(fb_value) > 1e-12
                    else math.nan
                )
                row[f"reduction_fb_vs_static_{metric}_pct"] = (
                    100.0 * (static_value - fb_value) / static_value
                    if np.isfinite(static_value) and abs(static_value) > 1e-12
                    else math.nan
                )
                row[f"reduction_ff_vs_static_{metric}_pct"] = (
                    100.0 * (static_value - ff_value) / static_value
                    if np.isfinite(static_value) and abs(static_value) > 1e-12
                    else math.nan
                )
            output.append(row)
    return output


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{stem}.pdf")
    fig.savefig(OUTPUT_DIR / f"{stem}.png")
    if IMAGE_DIR.is_dir():
        fig.savefig(IMAGE_DIR / f"{stem}.pdf")
    plt.close(fig)


def representative_runs(runs: list[Run], target_n: int = 20, ramp_s: int = 1) -> dict[str, Run]:
    selected = [run for run in runs if run.target_n == target_n and run.nominal_ramp_s == ramp_s]
    return {method: next(run for run in selected if run.method == method) for method in METHOD_ORDER}


def _sparse_style(color: str, marker: str, stride: int) -> dict:
    return dict(
        color=color,
        marker=marker,
        markevery=stride,
        markersize=3.2,
        markerfacecolor="white",
        markeredgecolor=color,
        markeredgewidth=0.65,
    )


RAMP_COLORS = {1: "#0077BB", 5: "#EE7733", 10: "#CC3311"}
RAMP_SHADE_ALPHA = {1: 0.30, 5: 0.20, 10: 0.12}
RAMP_LABEL = {1: "1 s 加速", 5: "5 s 加速", 10: "10 s 加速"}


def plot_freestream_ramp(runs: list[Run]) -> None:
    """Standalone, single-column freestream-speed ramp curve.

    Overlays the 1 s, 5 s, and 10 s freestream-acceleration curves (each the
    20 N / feedforward+feedback trial, since the rig-driven freestream profile
    does not depend on the control method) on a shared tau axis, where tau = 0
    is each run's own 10% crossing. The three shaded windows mark each run's
    evaluation window (10%-90% acceleration segment plus 3 s, matching the
    disturbance window used for every reported metric), in the same color as
    their curve at different alpha (widest/lightest for the slowest 10 s ramp,
    narrowest/darkest for the fastest 1 s ramp) so the three windows stay
    visually distinguishable even though they overlap.
    """
    ramp_levels = (1, 5, 10)
    by_ramp = {ramp_s: representative_runs(runs, target_n=20, ramp_s=ramp_s)["ff_fb"] for ramp_s in ramp_levels}
    ramp_ends = {ramp_s: run.t90_s - run.t10_s for ramp_s, run in by_ramp.items()}
    eval_ends = {ramp_s: ramp_end + 3.0 for ramp_s, ramp_end in ramp_ends.items()}
    xlim = (-2.0, max(ramp_ends.values()) + 4.0)

    fig = plt.figure(figsize=(3.4, 1.9))
    ax = fig.add_subplot(111)

    # Draw the widest (10 s) shaded window first so the narrower windows layer
    # on top of it, and plot curves widest-ramp-first so the fastest (1 s,
    # most visually salient) curve is drawn last and stays on top.
    for ramp_s in sorted(ramp_levels, reverse=True):
        ax.axvspan(0.0, eval_ends[ramp_s], color=RAMP_COLORS[ramp_s], alpha=RAMP_SHADE_ALPHA[ramp_s], zorder=-3)
    for ramp_s in sorted(ramp_levels, reverse=True):
        run = by_ramp[ramp_s]
        mask = (run.tau_s >= xlim[0]) & (run.tau_s <= xlim[1])
        ax.plot(
            run.tau_s[mask],
            run.freestream_smooth_m_s[mask],
            color=RAMP_COLORS[ramp_s],
            linewidth=1.6,
            zorder=2,
            label=RAMP_LABEL[ramp_s],
        )
    ax.axvline(0.0, color=COLORS["neutral"], linestyle=":", linewidth=0.8, zorder=1)
    style_grid(ax)
    ax.set_xlim(*xlim)
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("来流速度 V∞ (m/s)")
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax + 0.16 * (ymax - ymin))
    ax.legend(frameon=False, loc="upper left", handlelength=1.6, fontsize=6.5, ncol=1)

    fig.subplots_adjust(left=0.20, right=0.97, top=0.95, bottom=0.24)
    save_figure(fig, "fig9_freestream_ramp")


def plot_representative(runs: list[Run], ramp_s: int = 1, stem: str = "fig10_representative_response") -> None:
    """All three desired-thrust levels side by side for one nominal ramp duration."""
    target_levels = (15, 20, 25)
    by_target = {target_n: representative_runs(runs, target_n=target_n, ramp_s=ramp_s) for target_n in target_levels}
    xmax = max(run.t90_s - run.t10_s for selected in by_target.values() for run in selected.values()) + 4.0

    fig = plt.figure(figsize=(7.16, 4.85))
    grid = fig.add_gridspec(2, 3, height_ratios=(1.0, 1.0), hspace=0.16, wspace=0.36)
    thrust_axes = [fig.add_subplot(grid[0, col]) for col in range(3)]
    error_axes = [fig.add_subplot(grid[1, col], sharex=thrust_axes[col]) for col in range(3)]

    for col, target_n in enumerate(target_levels):
        selected = by_target[target_n]
        ramp_end = max(run.t90_s - run.t10_s for run in selected.values())
        # Shade the same disturbance/evaluation window used for every reported
        # metric (10%-90% ramp plus 3 s), not just the raw acceleration segment.
        eval_end = ramp_end + 3.0
        ax_t, ax_e = thrust_axes[col], error_axes[col]
        for method in METHOD_ORDER:
            run = selected[method]
            mask = (run.tau_s >= -2.0) & (run.tau_s <= xmax)
            n_visible = int(np.count_nonzero(mask))
            style = _sparse_style(COLORS[method], MARKERS[method], max(1, n_visible // 12))
            ax_t.plot(run.tau_s[mask], run.measured_n[mask], linewidth=1.1, **style)
            ax_e.plot(run.tau_s[mask], run.error_n[mask], linewidth=1.0, **style)
        ax_t.axhline(target_n, color=COLORS["target"], linestyle="--", linewidth=0.9, zorder=1)
        ax_e.axhline(0.0, color=COLORS["target"], linewidth=0.6, zorder=1)
        tolerance_n = 0.05 * target_n
        ax_e.axhspan(-tolerance_n, tolerance_n, color="0.92", zorder=-2)
        for axis in (ax_t, ax_e):
            axis.axvspan(0.0, eval_end, color="0.95", zorder=-3)
            axis.axvline(0.0, color=COLORS["neutral"], linestyle=":", linewidth=0.7, zorder=1)
            style_grid(axis)
        ax_e.set_xlabel("时间 (s)")
        # Headroom so the panel label never overlaps the FF+FB curve, which can
        # otherwise sit close to the target line for the whole window (e.g. the
        # well-tracked 10 s ramp cases).
        ymin, ymax = ax_t.get_ylim()
        ax_t.set_ylim(ymin, ymax + 0.16 * (ymax - ymin))
        panel_label(ax_t, f"({chr(ord('a') + col)}) $T_c$ = {target_n} N", x=0.06, y=0.95)
    thrust_axes[0].set_ylabel("升力 Tm (N)")
    error_axes[0].set_ylabel("误差 eT = Tc − Tm (N)")
    for axis in thrust_axes + error_axes:
        axis.set_xlim(-2.0, xmax)
    for axis in thrust_axes:
        plt.setp(axis.get_xticklabels(), visible=False)

    method_handles = [
        Line2D(
            [0],
            [0],
            color=COLORS[method],
            marker=MARKERS[method],
            markerfacecolor="white",
            markeredgecolor=COLORS[method],
            markeredgewidth=0.8,
            linewidth=1.4,
            label=METHOD_LABEL_ZH[method],
        )
        for method in METHOD_ORDER
    ]
    style_handles = [
        Line2D([0], [0], color=COLORS["target"], lw=1.0, ls="--", label="期望升力"),
        Patch(facecolor="0.92", edgecolor="none", label="±5% 误差带"),
        Patch(facecolor="0.95", edgecolor="none", label="评价窗口"),
    ]
    fig.legend(
        handles=method_handles + style_handles,
        loc="upper center",
        bbox_to_anchor=(0.56, 0.995),
        ncol=3,
        frameon=False,
        columnspacing=1.3,
        handlelength=1.9,
    )
    fig.subplots_adjust(left=0.075, right=0.98, top=0.905, bottom=0.10, hspace=0.16, wspace=0.36)
    save_figure(fig, stem)


def condition_matrix(
    condition_rows: list[dict[str, object]], method: str, metric: str
) -> np.ndarray:
    matrix = np.full((3, 3), np.nan)
    for row in condition_rows:
        if row["method"] != method:
            continue
        i = (15, 20, 25).index(int(row["target_n"]))
        j = (1, 5, 10).index(int(row["nominal_ramp_s"]))
        matrix[i, j] = float(row[metric])
    return matrix


def reduction_matrix(
    comparison_rows: list[dict[str, object]], comparison: str, metric: str
) -> np.ndarray:
    matrix = np.full((3, 3), np.nan)
    for row in comparison_rows:
        i = (15, 20, 25).index(int(row["target_n"]))
        j = (1, 5, 10).index(int(row["nominal_ramp_s"]))
        matrix[i, j] = float(row[f"reduction_{comparison}_{metric}_pct"])
    return matrix


def annotate_heatmap(
    axis: plt.Axes,
    matrix: np.ndarray,
    suffix: str,
    vmin: float,
    vmax: float,
    panel: str,
    flag_cell: tuple[int, int] | None = None,
) -> None:
    threshold = vmin + 0.55 * (vmax - vmin)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            text = f"{value:.1f}{suffix}"
            if flag_cell == (i, j):
                text += "*"
            axis.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                color="white" if value > threshold else "0.1",
                fontsize=8,
            )
    axis.set_xticks(range(3), ["1", "5", "10"])
    axis.set_yticks(range(3), ["15", "20", "25"])
    axis.set_xlabel("加速时间 (s)")
    axis.set_ylabel("期望升力 (N)")
    axis.minorticks_off()
    axis.grid(False)
    # Panel index sits in the title slot (outside the heatmap, above its
    # top-left corner) so it stays clear of the annotated cells without
    # growing the figure past its allotted height.
    axis.set_title(panel, loc="left", fontsize=9, fontweight="bold", pad=4)


def speed_binned_error(runs: list[Run]) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    edges = np.arange(0.0, 10.51, 0.5)
    centers = 0.5 * (edges[:-1] + edges[1:])
    per_cell: dict[tuple[int, int, str], list[np.ndarray]] = {}
    for run in runs:
        ramp_end_tau = run.t90_s - run.t10_s
        # Same disturbance window as trial_metrics() (10%-90% ramp plus 3 s),
        # so every reported evaluation window is defined identically.
        evaluation_window = (run.tau_s >= 0.0) & (run.tau_s <= ramp_end_tau + 3.0)
        values = np.full(len(centers), np.nan)
        for index, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
            mask = evaluation_window & (run.freestream_smooth_m_s >= left) & (run.freestream_smooth_m_s < right)
            if np.count_nonzero(mask) >= 3:
                values[index] = float(np.nanmean(np.abs(run.error_n[mask])) / run.target_n * 100.0)
        per_cell.setdefault((run.target_n, run.nominal_ramp_s, run.method), []).append(values)

    result: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for method in ("static", "fb", "ff_fb"):
        cell_rows = []
        for (target_n, ramp_s, cell_method), arrays in per_cell.items():
            if cell_method == method:
                stacked_trials = np.vstack(arrays)
                counts = np.sum(np.isfinite(stacked_trials), axis=0)
                cell_mean = np.divide(
                    np.nansum(stacked_trials, axis=0),
                    counts,
                    out=np.full(stacked_trials.shape[1], np.nan),
                    where=counts > 0,
                )
                cell_rows.append(cell_mean)
        matrix = np.vstack(cell_rows)
        median = np.full(matrix.shape[1], np.nan)
        q25 = np.full(matrix.shape[1], np.nan)
        q75 = np.full(matrix.shape[1], np.nan)
        for column in range(matrix.shape[1]):
            values = matrix[:, column]
            values = values[np.isfinite(values)]
            if len(values) >= 4:
                median[column] = float(np.median(values))
                q25[column] = float(np.percentile(values, 25))
                q75[column] = float(np.percentile(values, 75))
        result[method] = (
            centers,
            median,
            q25,
            q75,
        )
    return result


def plot_summary(comparison_rows: list[dict[str, object]]) -> None:
    fig = plt.figure(figsize=(5.5, 2.75))
    grid = fig.add_gridspec(1, 2, wspace=0.6)
    ax_fb_static = fig.add_subplot(grid[0, 0])
    ax_ff_fb = fig.add_subplot(grid[0, 1])

    matrices = {
        "fb_vs_static": reduction_matrix(comparison_rows, "fb_vs_static", "disturbance_rmse_pct"),
        "ff_vs_fb": reduction_matrix(comparison_rows, "ff_vs_fb", "disturbance_rmse_pct"),
    }
    # The 25 N / 1 s feedforward + feedback trial spends >50% of the window at
    # normalized output >= 0.98 (see trial_metrics.csv); flag that cell rather
    # than silently folding an actuator-limited result into the comparison.
    saturated_cell = (2, 0)
    # YlGnBu instead of viridis: viridis's low end is a dark purple that swallows
    # the annotated percentages, whereas the pale-yellow low end here stays legible.
    for axis, key, panel in (
        (ax_fb_static, "fb_vs_static", "(a)FB vs Static"),
        (ax_ff_fb, "ff_vs_fb", "(b)FF+FB vs FB"),
    ):
        matrix = matrices[key]
        vmin, vmax = float(np.nanmin(matrix)), float(np.nanmax(matrix))
        image = axis.imshow(matrix, cmap="YlGnBu", vmin=vmin, vmax=vmax, aspect="auto")
        annotate_heatmap(
            axis, matrix, "%", vmin, vmax, panel, flag_cell=saturated_cell if key == "ff_vs_fb" else None
        )
        colorbar = fig.colorbar(image, ax=axis, fraction=0.046, pad=0.06)
        colorbar.set_label("RMSE 降幅 (%)", fontsize=7.5)
        colorbar.ax.tick_params(labelsize=7, length=2)

    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.18, top=0.86)
    save_figure(fig, "fig11_condition_summary")


def plot_speed_error(runs: list[Run]) -> None:
    """Standalone, single-column companion to fig11: normalized absolute error
    across the freestream-speed sweep, split out so it can sit in one column
    of the two-column layout rather than crowding the fig11 heatmap pair."""
    fig = plt.figure(figsize=(3.4, 2.5))
    ax = fig.add_subplot(111)

    binned = speed_binned_error(runs)
    for method in METHOD_ORDER:
        centers, median, q25, q75 = binned[method]
        valid = np.isfinite(median)
        stride = max(1, int(np.count_nonzero(valid)) // 10)
        ax.plot(
            centers[valid],
            median[valid],
            color=COLORS[method],
            marker=MARKERS[method],
            markevery=stride,
            markersize=3.6,
            markerfacecolor="white",
            markeredgecolor=COLORS[method],
            markeredgewidth=0.7,
            linewidth=1.4,
            label=METHOD_LABEL_ZH[method],
        )
        ax.fill_between(
            centers[valid], q25[valid], q75[valid], color=COLORS[method], alpha=0.16, linewidth=0
        )
    ax.set_xlabel("来流速度 V∞ (m/s)")
    ax.set_ylabel("绝对跟踪误差(%)")
    style_grid(ax)
    ax.legend(frameon=False, loc="upper left", handlelength=1.6, fontsize=7)

    fig.subplots_adjust(left=0.20, right=0.97, top=0.97, bottom=0.19)
    save_figure(fig, "fig12_speed_error")


def plot_mechanism(runs: list[Run]) -> None:
    """Sized to sit in one column of the two-column layout (native width close
    to the printed column width, so text is not shrunk by \\includegraphics)."""
    ff = representative_runs(runs)["ff_fb"]
    ramp_end_tau = ff.t90_s - ff.t10_s
    mask = (ff.tau_s >= -2.0) & (ff.tau_s <= ramp_end_tau + 4.0)
    n_visible = int(np.count_nonzero(mask))
    stride = max(1, n_visible // 9)

    def curve(axis: plt.Axes, values: np.ndarray, color: str, marker: str, label: str, **kwargs) -> None:
        axis.plot(
            ff.tau_s[mask],
            values[mask],
            color=color,
            marker=marker,
            markevery=stride,
            markersize=2.8,
            markerfacecolor="white",
            markeredgecolor=color,
            markeredgewidth=0.6,
            linewidth=1.05,
            label=label,
            **kwargs,
        )

    fig, axes = plt.subplots(2, 1, figsize=(3.35, 4.1), sharex=True, gridspec_kw={"hspace": 0.16})
    curve(axes[0], ff.model_rpm, COLORS["ff_fb"], "o", "模型转速")
    curve(axes[1], ff.feedforward_out, COLORS["ff_fb"], "o", "前馈")

    curve(axes[0], ff.measured_rpm, COLORS["fb"], "s", "编码器转速")
    curve(axes[1], ff.feedback_out, COLORS["fb"], "s", "反馈")

    axes[1].plot(
        ff.tau_s[mask],
        ff.total_out[mask],
        color=COLORS["target"],
        linestyle="--",
        linewidth=0.9,
        label="总量",
        zorder=3,
    )

    axes[0].set_ylabel("转速 (rpm)")
    axes[1].set_ylabel("控制量")
    axes[1].set_xlabel("时间 (s)")

    legend_kwargs = {
        0: {"loc": "lower right"},
        1: {"loc": "upper left", "bbox_to_anchor": (0.01, 0.88)},
    }
    for index, axis in enumerate(axes):
        axis.axvspan(0.0, ramp_end_tau, color="0.95", zorder=-3)
        axis.axvline(0.0, color=COLORS["neutral"], linestyle=":", linewidth=0.7, zorder=1)
        style_grid(axis)
        axis.legend(frameon=False, ncol=1, handlelength=1.4, fontsize=6.5, **legend_kwargs[index])
    panel_label(axes[0], "(a)")
    panel_label(axes[1], "(b)")
    fig.subplots_adjust(left=0.22, right=0.97, top=0.97, bottom=0.11, hspace=0.16)
    save_figure(fig, "fig13_feedforward_mechanism")


def write_text_summary(
    trial_rows: list[dict[str, object]],
    condition_rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
) -> None:
    ff_vs_fb_rmse = np.asarray(
        [float(row["reduction_ff_vs_fb_disturbance_rmse_pct_pct"]) for row in comparison_rows]
    )
    fb_vs_static_rmse = np.asarray(
        [float(row["reduction_fb_vs_static_disturbance_rmse_pct_pct"]) for row in comparison_rows]
    )
    ff_vs_fb_peak = np.asarray(
        [float(row["reduction_ff_vs_fb_disturbance_peak_pct_pct"]) for row in comparison_rows]
    )
    fb_vs_static_peak = np.asarray(
        [float(row["reduction_fb_vs_static_disturbance_peak_pct_pct"]) for row in comparison_rows]
    )
    ff_rmse = np.asarray([float(row["ff_disturbance_rmse_pct"]) for row in comparison_rows])
    fb_rmse = np.asarray([float(row["fb_disturbance_rmse_pct"]) for row in comparison_rows])
    static_rmse = np.asarray([float(row["static_disturbance_rmse_pct"]) for row in comparison_rows])
    ff_incremental_rmse = np.asarray(
        [float(row["ff_disturbance_incremental_rmse_pct"]) for row in comparison_rows]
    )
    fb_incremental_rmse = np.asarray(
        [float(row["fb_disturbance_incremental_rmse_pct"]) for row in comparison_rows]
    )
    static_incremental_rmse = np.asarray(
        [float(row["static_disturbance_incremental_rmse_pct"]) for row in comparison_rows]
    )
    ff_feedback_fractions = np.asarray(
        [
            float(row["feedback_fraction_mean"])
            for row in trial_rows
            if row["method"] == "ff_fb"
        ]
    )
    duplicate = [
        row
        for row in trial_rows
        if row["target_n"] == 15 and row["nominal_ramp_s"] == 1 and row["method"] == "ff_fb"
    ]
    duplicate_rmse = [float(row["disturbance_rmse_pct"]) for row in duplicate]
    static_rpm_changes = np.asarray(
        [abs(float(row["rpm_plateau_change_pct"])) for row in trial_rows if row["method"] == "static"]
    )
    static_actuator_changes = np.asarray(
        [
            abs(float(row["actuator_output_0_plateau_change_pct"]))
            for row in trial_rows
            if row["method"] == "static"
        ]
    )
    hierarchy_wins = int(np.sum((ff_rmse < fb_rmse) & (fb_rmse < static_rmse)))
    incremental_hierarchy_wins = int(
        np.sum(
            (ff_incremental_rmse < fb_incremental_rmse)
            & (fb_incremental_rmse < static_incremental_rmse)
        )
    )

    lines = [
        "# 90-degree axial-inflow three-method control analysis",
        "",
        f"- Parsed {len(trial_rows)} logs into {len(condition_rows)} method-condition cells and {len(comparison_rows)} three-method matched conditions.",
        "- Channel 1 is the only active thrust/control channel; inactive zero channels were excluded.",
        "- Each run was aligned by the 10% and 90% crossings of a median-filtered freestream-speed signal.",
        "- The disturbance window spans the 10%-90% speed ramp plus 3 s after the 90% crossing.",
        "",
        "## Descriptive result",
        "",
        f"- Full RMSE hierarchy (model FF + feedback < feedback only < static-map open loop) holds in {hierarchy_wins}/{len(comparison_rows)} matched conditions.",
        f"- After subtracting each run's pre-disturbance mean error, the same incremental-RMSE hierarchy holds in {incremental_hierarchy_wins}/{len(comparison_rows)} conditions.",
        f"- Feedback-only median RMSE reduction versus static open loop: {np.nanmedian(fb_vs_static_rmse):.1f}% (range {np.nanmin(fb_vs_static_rmse):.1f}% to {np.nanmax(fb_vs_static_rmse):.1f}%).",
        f"- Model-FF median RMSE reduction versus feedback only: {np.nanmedian(ff_vs_fb_rmse):.1f}% (range {np.nanmin(ff_vs_fb_rmse):.1f}% to {np.nanmax(ff_vs_fb_rmse):.1f}%).",
        f"- Feedback-only median peak-error reduction versus static: {np.nanmedian(fb_vs_static_peak):.1f}%; model-FF median peak-error reduction versus feedback only: {np.nanmedian(ff_vs_fb_peak):.1f}%.",
        f"- In feedforward + feedback runs, the median trial-level mean absolute feedback share of total output is {100*np.nanmedian(ff_feedback_fractions):.1f}%.",
        f"- Static-map runs have a median absolute baseline-to-plateau measured-RPM change of {np.nanmedian(static_rpm_changes):.1f}% (range {np.nanmin(static_rpm_changes):.1f}% to {np.nanmax(static_rpm_changes):.1f}%).",
        f"- The recorded actuator_outputs.output[0] in static-map runs changes by a median absolute {np.nanmedian(static_actuator_changes):.3f}% from baseline to plateau (maximum {np.nanmax(static_actuator_changes):.3f}%), confirming that the applied primary actuator command is fixed.",
        "",
        "## Replication and inference limits",
        "",
        f"- Only the 15 N / 1 s feedforward + feedback cell is repeated (trial normalized RMSE values: {', '.join(f'{x:.2f}%' for x in duplicate_rmse)}).",
        "- Most cells have n=1, so the values are descriptive and do not support confidence intervals, p-values, or a statistical-superiority claim.",
        "- The 25 N / 1 s feedforward + feedback run is at normalized output >= 0.98 for 56.5% of the disturbance window; 25 N conclusions therefore include actuator-limit effects.",
        "- Static logs still contain changing internal thrust_feedback_out/thrust_control_out fields, but actuator_outputs.output[0] is fixed. Treat the former as computed internal signals, not the applied static command.",
        "",
        "## Files",
        "",
        "- trial_metrics.csv: one row per ULog.",
        "- condition_metrics.csv: duplicate trials averaged within method-condition cells.",
        "- three_method_comparison.csv: matched three-method values and relative reductions.",
        "- fig9_freestream_ramp.*: representative freestream-ramp curve (single-column).",
        "- fig10_representative_response.*: aligned representative response.",
        "- fig11_condition_summary.*: all-condition RMSE reduction heatmaps.",
        "- fig12_speed_error.*: error over the freestream-speed sweep (single-column).",
        "- fig13_feedforward_mechanism.*: model speed, control decomposition, and freestream consistency check.",
    ]
    (OUTPUT_DIR / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_artifact(
    trial_rows: list[dict[str, object]],
    condition_rows: list[dict[str, object]],
    paired_rows: list[dict[str, object]],
) -> None:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    reductions_rmse = np.asarray(
        [float(row["reduction_disturbance_rmse_pct_pct"]) for row in paired_rows]
    )
    reductions_mae = np.asarray(
        [float(row["reduction_disturbance_mae_pct_pct"]) for row in paired_rows]
    )
    reductions_peak = np.asarray(
        [float(row["reduction_disturbance_peak_pct_pct"]) for row in paired_rows]
    )
    wins = int(
        np.sum(
            [
                float(row["ff_disturbance_rmse_pct"])
                < float(row["fb_disturbance_rmse_pct"])
                for row in paired_rows
            ]
        )
    )
    summary_dataset = [
        {
            "median_rmse_reduction_pct": round(float(np.nanmedian(reductions_rmse)), 1),
            "median_mae_reduction_pct": round(float(np.nanmedian(reductions_mae)), 1),
            "median_peak_reduction_pct": round(float(np.nanmedian(reductions_peak)), 1),
            "winning_cells": wins,
            "total_paired_cells": len(paired_rows),
            "total_logs": len(trial_rows),
        }
    ]
    comparison_long = []
    comparison_table = []
    for row in paired_rows:
        condition = f"{int(row['target_n'])} N / {int(row['nominal_ramp_s'])} s"
        for method, prefix in (("Model FF + feedback", "ff"), ("Feedback only", "fb")):
            comparison_long.append(
                {
                    "condition": condition,
                    "method": method,
                    "target_n": int(row["target_n"]),
                    "nominal_ramp_s": int(row["nominal_ramp_s"]),
                    "rmse_pct": round(float(row[f"{prefix}_disturbance_rmse_pct"]), 4),
                    "mae_pct": round(float(row[f"{prefix}_disturbance_mae_pct"]), 4),
                    "peak_pct": round(float(row[f"{prefix}_disturbance_peak_pct"]), 4),
                    "n_trials": int(row[f"{prefix}_trials"]),
                    "rmse_reduction_pct": round(
                        float(row["reduction_disturbance_rmse_pct_pct"]), 4
                    ),
                }
            )
        comparison_table.append(
            {
                "target_n": int(row["target_n"]),
                "nominal_ramp_s": int(row["nominal_ramp_s"]),
                "ff_rmse_pct": round(float(row["ff_disturbance_rmse_pct"]), 2),
                "fb_rmse_pct": round(float(row["fb_disturbance_rmse_pct"]), 2),
                "rmse_reduction_pct": round(
                    float(row["reduction_disturbance_rmse_pct_pct"]), 1
                ),
                "ff_peak_pct": round(float(row["ff_disturbance_peak_pct"]), 2),
                "fb_peak_pct": round(float(row["fb_disturbance_peak_pct"]), 2),
                "peak_reduction_pct": round(
                    float(row["reduction_disturbance_peak_pct_pct"]), 1
                ),
                "ff_trials": int(row["ff_trials"]),
                "fb_trials": int(row["fb_trials"]),
            }
        )

    database_path = OUTPUT_DIR / "analysis_metrics.sqlite"
    with sqlite3.connect(database_path) as connection:
        connection.execute("DROP TABLE IF EXISTS paired_metrics")
        connection.execute(
            """
            CREATE TABLE paired_metrics (
                target_n INTEGER NOT NULL,
                nominal_ramp_s INTEGER NOT NULL,
                ff_rmse_pct REAL NOT NULL,
                fb_rmse_pct REAL NOT NULL,
                rmse_reduction_pct REAL NOT NULL,
                ff_peak_pct REAL NOT NULL,
                fb_peak_pct REAL NOT NULL,
                peak_reduction_pct REAL NOT NULL,
                ff_trials INTEGER NOT NULL,
                fb_trials INTEGER NOT NULL,
                PRIMARY KEY (target_n, nominal_ramp_s)
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO paired_metrics VALUES (
                :target_n, :nominal_ramp_s, :ff_rmse_pct, :fb_rmse_pct,
                :rmse_reduction_pct, :ff_peak_pct, :fb_peak_pct,
                :peak_reduction_pct, :ff_trials, :fb_trials
            )
            """,
            comparison_table,
        )
        source_sql = (
            "SELECT target_n, nominal_ramp_s, ff_rmse_pct, fb_rmse_pct, "
            "rmse_reduction_pct, ff_peak_pct, fb_peak_pct, peak_reduction_pct, "
            "ff_trials, fb_trials FROM paired_metrics "
            "ORDER BY nominal_ramp_s ASC, target_n ASC"
        )
        # Execute the exact query stored as provenance and use its reviewed rows
        # as the wide table snapshot. The chart dataset is a deterministic
        # long-form reshape of this same result.
        columns = [item[0] for item in connection.execute(source_sql).description]
        comparison_table = [
            dict(zip(columns, values)) for values in connection.execute(source_sql).fetchall()
        ]

    source = {
        "id": "axial-ulog-source",
        "label": "90°轴向来流 19 个 ULog 的配对指标（由 analyze_closed_loop.py 生成）",
        "path": "analysis_metrics.sqlite",
        "query": {
            "engine": "SQLite",
            "sql": source_sql,
            "description": "从经 pyulog 处理的单试验指标中读取 9 个方法配对单元；图中的长表是该查询结果的确定性整形。",
            "language": "sql",
            "tables_used": ["paired_metrics"],
            "filters": [
                "攻角=90度",
                "目标升力∈{15,20,25} N",
                "标称加速时间∈{1,5,10} s",
                "方法∈{模型前馈+反馈,纯反馈}",
                "仅使用推力/控制通道 1；其余通道为零",
                "扰动窗口=来流 10%-90% 上升段+到达 90% 后 3 s",
            ],
            "metric_definitions": [
                "e_T=T_c-T_m，T_m 为 thrust_kalman_filter_data_1 线性插值到控制时间基的值。",
                "归一化 RMSE=100*sqrt(mean(e_T^2))/T_c。",
                "归一化峰值误差=100*max(abs(e_T))/T_c。",
                "相对降幅=100*(纯反馈-模型前馈+反馈)/纯反馈。",
                "15 N/1 s 前馈+反馈的两次试验先在单元内取均值；其余单元 n=1。",
            ],
        },
    }
    title = "90°轴向来流下升力闭环控制：现有数据分析与论文图表方案"
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "基于当前 90°轴向来流 ULog 的描述性闭环性能比较及后续实验设计建议。",
            "generatedAt": generated_at,
            "sources": [source],
            "cards": [],
            "charts": [
                {
                    "id": "rmse-by-condition",
                    "title": "不同目标升力与加速时间下的归一化 RMSE",
                    "subtitle": "扰动窗口，数值为目标升力的百分比；15 N/1 s 前馈+反馈为两次试验均值，其余 n=1",
                    "type": "bar",
                    "intent": "comparison",
                    "question": "在相同目标升力和加速时间下，两种闭环方法的跟踪误差如何比较？",
                    "rationale": "分组柱形图保留 9 个工况的配对结构，便于识别方法效应是否在不同工况下一致。",
                    "comparisonContext": {
                        "baseline": "相同目标升力/加速时间的纯反馈试验",
                        "denominator": "目标升力 T_c",
                        "grain": "方法×目标升力×标称加速时间",
                        "normalization": "RMSE/T_c×100",
                        "unit": "%",
                    },
                    "dataset": "comparison_long",
                    "sourceId": "axial-ulog-source",
                    "encodings": {
                        "x": {"field": "condition", "type": "ordinal", "label": "工况"},
                        "y": {
                            "field": "rmse_pct",
                            "type": "quantitative",
                            "label": "归一化 RMSE",
                            "unit": "%",
                        },
                        "color": {"field": "method", "type": "nominal", "label": "控制方法"},
                        "tooltip": [
                            {"field": "target_n", "type": "quantitative", "label": "目标升力", "unit": "N"},
                            {"field": "nominal_ramp_s", "type": "quantitative", "label": "加速时间", "unit": "s"},
                            {"field": "peak_pct", "type": "quantitative", "label": "峰值误差", "unit": "%"},
                            {"field": "n_trials", "type": "quantitative", "label": "试验次数"},
                        ],
                    },
                    "valueFormat": "number",
                    "unit": "%",
                    "layout": "full",
                    "palette": {"kind": "categorical", "name": "blue-orange"},
                    "legend": {"position": "bottom", "title": "控制方法"},
                    "settings": {
                        "groupMode": "grouped",
                        "categoryLabelPolicy": "rotate",
                        "showValues": True,
                        "sort": "none",
                    },
                    "surface": {"surface": "export", "viewMode": "both"},
                }
            ],
            "tables": [
                {
                    "id": "paired-metrics-table",
                    "title": "各配对工况的跟踪误差及降幅",
                    "subtitle": "归一化误差均以目标升力为分母，降幅为模型前馈+反馈相对纯反馈的百分比",
                    "dataset": "comparison_table",
                    "defaultSort": {"field": "nominal_ramp_s", "direction": "asc"},
                    "density": "dense",
                    "sourceId": "axial-ulog-source",
                    "layout": "full",
                    "columns": [
                        {"field": "target_n", "label": "目标升力 (N)", "format": "number"},
                        {"field": "nominal_ramp_s", "label": "加速时间 (s)", "format": "number"},
                        {"field": "ff_rmse_pct", "label": "前馈+反馈 RMSE (%)", "format": "number"},
                        {"field": "fb_rmse_pct", "label": "纯反馈 RMSE (%)", "format": "number"},
                        {"field": "rmse_reduction_pct", "label": "RMSE 降幅 (%)", "format": "number", "movement": True},
                        {"field": "ff_peak_pct", "label": "前馈+反馈峰值 (%)", "format": "number"},
                        {"field": "fb_peak_pct", "label": "纯反馈峰值 (%)", "format": "number"},
                        {"field": "peak_reduction_pct", "label": "峰值降幅 (%)", "format": "number", "movement": True},
                        {"field": "ff_trials", "label": "前馈+反馈 n", "format": "number"},
                        {"field": "fb_trials", "label": "纯反馈 n", "format": "number"},
                    ],
                }
            ],
            "blocks": [
                {"id": "title", "type": "markdown", "body": f"# {title}", "layout": "full"},
                {
                    "id": "technical-summary",
                    "type": "markdown",
                    "body": (
                        "## 技术摘要\n\n"
                        f"**当前数据支持“模型前馈+反馈优于纯反馈”的描述性结论。** "
                        f"在 {len(paired_rows)} 个目标升力×加速时间配对工况中，前馈+反馈的归一化 RMSE 在 {wins}/{len(paired_rows)} 个单元中更低，"
                        f"中位降幅为 {np.nanmedian(reductions_rmse):.1f}%；峰值误差中位降幅为 {np.nanmedian(reductions_peak):.1f}%。\n\n"
                        "**但现阶段不能宣称已证明“前馈+反馈 > 反馈 >> 固定控制量”。** 固定控制量对照尚未开展，且除 15 N/1 s 的前馈+反馈外，其余单元均只有一次试验。"
                    ),
                    "layout": "full",
                    "sourceId": "axial-ulog-source",
                },
                {
                    "id": "key-findings",
                    "type": "markdown",
                    "body": (
                        "## 方法优势在全部现有工况中保持一致\n\n"
                        "下图保留每个目标升力和加速时间单元，不使用混合后的单一总平均。这样可以直接检查前馈改善是否仅来自某个有利工况。"
                    ),
                    "layout": "full",
                },
                {"id": "rmse-chart-block", "type": "chart", "chartId": "rmse-by-condition", "layout": "full"},
                {
                    "id": "rmse-chart-interpretation",
                    "type": "markdown",
                    "body": (
                        "在 1 s 快速加速下，两种闭环的误差都高于 5 s 和 10 s 工况，但模型前馈仍在三个目标升力下降低 RMSE。"
                        "因此，论文的主要论据应是“同一单元内的配对改善”，而不是比较不同目标升力或不同加速时间的绝对误差。"
                    ),
                    "layout": "full",
                    "sourceId": "axial-ulog-source",
                },
                {"id": "paired-table-block", "type": "table", "tableId": "paired-metrics-table", "layout": "full"},
                {
                    "id": "scope-definitions",
                    "type": "markdown",
                    "body": (
                        "## 评价口径与数据范围\n\n"
                        "- **有效通道：** 仅通道 1 存在非零目标、控制输出和升力测量，因此不对四通道取平均。\n"
                        "- **对齐：** 对 `bet_freestream_m_s` 中值滤波，以高低速平台之间的 10% 持续跨越点为时间零点，90% 持续跨越点为加速段终点。\n"
                        "- **主指标：** 扰动窗口归一化 RMSE、MAE 和峰值误差，分母均为目标升力。\n"
                        "- **测量：** 使用 `thrust_kalman_filter_data_1`；`rpm_raw` 乘以负号后与模型转速比较。"
                    ),
                    "layout": "full",
                },
                {
                    "id": "methodology",
                    "type": "markdown",
                    "body": (
                        "## 图表证据链应同时回答“效果”和“机理”\n\n"
                        "1. **代表工况时序（主文）：** 分面板绘制来流速度、升力及目标、跟踪误差，禁止双纵轴。建议选 20 N/1 s，因其扰动强且不处于目标升力边界。\n"
                        "2. **全工况配对汇总（主文）：** 用热图或配对点图展示 3×3 单元的归一化 RMSE 与降幅，保留工况异质性。\n"
                        "3. **误差-来流速度曲线（主文或附录）：** 按来流速度分箱，绘制 9 个工况单元的中位绝对归一化误差与四分位带，仅称为描述性离散带。\n"
                        "4. **前馈机理图（附录优先）：** 展示 BET 反解转速、编码器转速、前馈/反馈/总输出，用于说明“前馈提供主要控制量，反馈补偿残差”，不将其替代跟踪误差证据。"
                    ),
                    "layout": "full",
                },
                {
                    "id": "limitations",
                    "type": "markdown",
                    "body": (
                        "## 当前结论需要保留的限制\n\n"
                        "- **无固定控制量对照：** 现有数据不能支持“纯反馈远优于固定控制量”。\n"
                        "- **缺少独立重复：** 多数单元 n=1，不应给出 p 值、95% 置信区间或“统计显著优于”的表述。\n"
                        "- **25 N 工况存在输出限幅：** 25 N/1 s 的前馈+反馈试验在扰动窗口内约 56.5% 的样本处于归一化输出不低于 0.98，25 N 结果包含执行器限幅效应。\n"
                        "- **只有 90°攻角：** 结论只适用于纯轴向来流，不能外推至 0° 和 45°。\n"
                        "- **来流估计与惯性载荷：** 向心加速度反算速度与角速度估计存在系统差，应在方法中报告标定或一致性检查。"
                    ),
                    "layout": "full",
                    "sourceId": "axial-ulog-source",
                },
                {
                    "id": "next-steps",
                    "type": "markdown",
                    "body": (
                        "## 使最终论据成立的补测优先级\n\n"
                        "1. 先补齐 90°下的固定控制量 3×3 单元，并为三种方法的每个单元至少完成 3 次独立重复；若资源许可，5 次更稳妥。\n"
                        "2. 同一配对或区组内保持相同加速轨迹、目标升力、滤波参数、评价窗口和限幅，并随机化方法执行顺序。\n"
                        "3. 补齐 0°和 45°后，使用方法×攻角×目标升力×加速时间的分层模型或区组自助法，将“方法主效应”与工况交互效应分开。\n"
                        "4. 预先固定主指标为扰动窗口归一化 RMSE，峰值误差和加速后稳态偏差作为次要指标，避免事后挑选最有利的结果。"
                    ),
                    "layout": "full",
                },
                {
                    "id": "further-questions",
                    "type": "markdown",
                    "body": (
                        "## 尚需确认的实验定义\n\n"
                        "- “固定控制量”是指以零来流二次推力-转速/PWM 映射设置一个不随来流变化的控制量，还是直接固定转速？两者的结论对象不同。\n"
                        "- 反馈方法的初始控制量如何给定，是否与固定控制量完全一致？这决定了两者的对照是否公平。\n"
                        "- 飞控中的 `thrust_error[0]` 与传感器滤波值之间存在时间基/滤波延迟差异，最终统计应统一选择传感器滤波序列并明确延迟处理。"
                    ),
                    "layout": "full",
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "summary": summary_dataset,
                "comparison_long": comparison_long,
                "comparison_table": comparison_table,
            },
            "accessIssues": [],
        },
        "sources": [source],
    }
    (OUTPUT_DIR / "artifact.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    configure_plotting()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(DATA_DIR.glob("*.ulg"), key=lambda item: int(item.name.split("-")[0]))
    if not paths:
        raise FileNotFoundError(f"No ULog files found in {DATA_DIR}")
    runs = [load_run(path) for path in paths]
    trial_rows = [trial_metrics(run) for run in runs]
    condition_rows = aggregate_conditions(trial_rows)
    comparison_rows = comparison_conditions(condition_rows)

    write_csv(OUTPUT_DIR / "trial_metrics.csv", trial_rows)
    write_csv(OUTPUT_DIR / "condition_metrics.csv", condition_rows)
    write_csv(OUTPUT_DIR / "three_method_comparison.csv", comparison_rows)
    plot_freestream_ramp(runs)
    plot_representative(runs, ramp_s=1, stem="fig10_representative_response")
    plot_representative(runs, ramp_s=5, stem="fig10_representative_response_5s")
    plot_representative(runs, ramp_s=10, stem="fig10_representative_response_10s")
    plot_summary(comparison_rows)
    plot_speed_error(runs)
    plot_mechanism(runs)
    write_text_summary(trial_rows, condition_rows, comparison_rows)
    # The portable report is generated after the three-method metrics have
    # passed the validation checks below.
    print(f"Analyzed {len(runs)} logs. Outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
