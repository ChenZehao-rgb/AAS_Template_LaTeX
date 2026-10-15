"""Rebuild Figure 5 over the validated comparison interval.

The original full-span vector figure is retained as the immutable extraction
source. This script recovers the two reference curves, the photogrammetry
points, and the smoothed photogrammetry curves before plotting only
0.25 <= r/R <= 0.90.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).with_name("fig5_full_range_source.pdf")
OUTPUT = ROOT / "Image" / "fig5_chord_pitch_comparison.pdf"

R_OVER_R_MIN = 0.25
R_OVER_R_MAX = 0.90
BLUE = "#1F5A99"
DARK = "#333333"
GRID = "#D9D9D9"

# The figure is drawn at FIG_WIDTH_IN but placed in the document at
# DISPLAY_WIDTH_CM (see \includegraphics[width=9cm,...] in template.tex), so
# any point size set here is shrunk by that ratio once typeset. Scale the
# in-figure font size up so the text reads at BODY_FONT_PT (the document's
# \normalsize, \zihao{5} = 10.5bp) once the figure is placed.
FIG_WIDTH_IN = 6.82
DISPLAY_WIDTH_CM = 9.0
BODY_FONT_PT = 10.5
FONT_SCALE = FIG_WIDTH_IN / (DISPLAY_WIDTH_CM / 2.54)
SIZE_ADJUST = 0.7  # requested: 30% smaller than the body-text match
BASE_FONTSIZE = BODY_FONT_PT * FONT_SCALE * SIZE_ADJUST


def _is_blue(color: tuple[float, ...] | None) -> bool:
    return color is not None and np.allclose(
        color, (0.12156863, 0.35294118, 0.6), atol=1e-4
    )


def _polyline(
    drawing: dict, axes: fitz.Rect, y_max: float
) -> tuple[np.ndarray, np.ndarray]:
    items = drawing["items"]
    if not items or any(item[0] != "l" for item in items):
        raise ValueError("Expected a line-only vector path in the source figure")

    points = np.asarray(
        [(items[0][1].x, items[0][1].y)]
        + [(item[2].x, item[2].y) for item in items],
        dtype=float,
    )
    radius = (points[:, 0] - axes.x0) / axes.width
    value = (axes.y1 - points[:, 1]) / axes.height * y_max
    return radius, value


def _markers(
    drawings: list[dict],
    stop_index: int,
    axes: fitz.Rect,
    y_max: float,
) -> tuple[np.ndarray, np.ndarray]:
    centers = []
    for drawing in drawings[:stop_index]:
        rect = drawing["rect"]
        item_types = {item[0] for item in drawing["items"]}
        if (
            _is_blue(drawing.get("color"))
            and drawing.get("fill") == (1.0, 1.0, 1.0)
            and np.isclose(drawing.get("width", 0), 0.7, atol=1e-3)
            and 2.3 <= rect.width <= 2.6
            and 2.3 <= rect.height <= 2.6
            and item_types in ({"c"}, {"re"})
            and axes.x0 <= (rect.x0 + rect.x1) / 2 <= axes.x1
            and axes.y0 <= (rect.y0 + rect.y1) / 2 <= axes.y1
        ):
            centers.append(((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2))

    points = np.asarray(centers, dtype=float)
    radius = (points[:, 0] - axes.x0) / axes.width
    value = (axes.y1 - points[:, 1]) / axes.height * y_max
    order = np.argsort(radius)
    return radius[order], value[order]


def _clip_curve(radius: np.ndarray, value: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(radius)
    radius = radius[order]
    value = value[order]
    interior = (radius > R_OVER_R_MIN) & (radius < R_OVER_R_MAX)
    clipped_radius = np.concatenate(
        ([R_OVER_R_MIN], radius[interior], [R_OVER_R_MAX])
    )
    clipped_value = np.interp(clipped_radius, radius, value)
    return clipped_radius, clipped_value


def _extract_source() -> list[dict[str, tuple[np.ndarray, np.ndarray]]]:
    page = fitz.open(SOURCE)[0]
    drawings = page.get_drawings()

    axes = sorted(
        [
            drawing["rect"]
            for drawing in drawings
            if drawing.get("fill") == (1.0, 1.0, 1.0)
            and drawing["rect"].width > 400
            and 100 < drawing["rect"].height < 200
        ],
        key=lambda rect: rect.y0,
    )
    reference_items = [
        (index, drawing)
        for index, drawing in enumerate(drawings)
        if drawing.get("dashes") not in (None, "[] 0")
        and drawing["rect"].width > 400
    ]
    fitted_items = [
        (index, drawing)
        for index, drawing in enumerate(drawings)
        if _is_blue(drawing.get("color"))
        and np.isclose(drawing.get("width", 0), 2.0)
        and drawing["rect"].width > 400
    ]
    reference_items.sort(key=lambda item: item[1]["rect"].y0)
    fitted_items.sort(key=lambda item: item[1]["rect"].y0)
    if len(axes) != 2 or len(reference_items) != 2 or len(fitted_items) != 2:
        raise RuntimeError("The full-range source figure structure has changed")

    panels = []
    for panel_index, y_max in enumerate((0.24, 25.0)):
        fitted_index, fitted_drawing = fitted_items[panel_index]
        panels.append(
            {
                "reference": _polyline(
                    reference_items[panel_index][1], axes[panel_index], y_max
                ),
                "raw": _markers(drawings, fitted_index, axes[panel_index], y_max),
                "fitted": _polyline(fitted_drawing, axes[panel_index], y_max),
            }
        )
    return panels


def _configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": ["Times New Roman", "SimSun"],
            "mathtext.fontset": "custom",
            "mathtext.rm": "SimSun",
            "mathtext.it": "Times New Roman:italic",
            "mathtext.bf": "Times New Roman:bold",
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
        }
    )


def main() -> None:
    panels = _extract_source()
    _configure_style()

    figure, axes = plt.subplots(2, 1, figsize=(6.82, 5.28), sharex=True)
    figure.subplots_adjust(
        left=0.13, right=0.985, top=0.975, bottom=0.115, hspace=0.12
    )

    for panel_index, (axis, panel) in enumerate(zip(axes, panels, strict=True)):
        reference_radius, reference_value = _clip_curve(*panel["reference"])
        fitted_radius, fitted_value = _clip_curve(*panel["fitted"])
        raw_radius, raw_value = panel["raw"]
        raw_mask = (raw_radius >= R_OVER_R_MIN) & (raw_radius <= R_OVER_R_MAX)

        axis.plot(
            reference_radius,
            reference_value,
            color=DARK,
            linewidth=1.7,
            linestyle=(0, (4.0, 2.5)),
            label="参考值(Carrol[18])",
            zorder=2,
        )
        axis.plot(
            raw_radius[raw_mask],
            raw_value[raw_mask],
            linestyle="none",
            marker="o" if panel_index == 0 else "s",
            markersize=2.8,
            markerfacecolor="white",
            markeredgecolor=BLUE,
            markeredgewidth=0.7,
            label="三维模型原始提取值",
            zorder=3,
        )
        axis.plot(
            fitted_radius,
            fitted_value,
            color=BLUE,
            linewidth=2.0,
            label="三维模型平滑拟合",
            zorder=4,
        )

        axis.set_xlim(R_OVER_R_MIN, R_OVER_R_MAX)
        axis.grid(True, color=GRID, linewidth=0.65)
        axis.tick_params(
            direction="in",
            top=True,
            right=True,
            length=3.0,
            width=0.8,
            labelsize=BASE_FONTSIZE,
        )
        for spine in axis.spines.values():
            spine.set_color("black")
            spine.set_linewidth(0.8)
        axis.text(
            0.015,
            0.91,
            f"({chr(ord('a') + panel_index)})",
            transform=axis.transAxes,
            fontsize=BASE_FONTSIZE,
        )

    axes[0].set_ylim(0.0, 0.24)
    axes[0].set_yticks(np.arange(0.0, 0.241, 0.04))
    axes[0].set_ylabel(r"$\mathrm{弦长比}\ \ c/R$", fontsize=BASE_FONTSIZE)
    axes[0].legend(
        loc="lower left", frameon=False, fontsize=BASE_FONTSIZE, handlelength=3.0
    )

    axes[1].set_ylim(0.0, 25.0)
    axes[1].set_yticks(np.arange(0.0, 25.1, 5.0))
    axes[1].set_ylabel(r"$\mathrm{安装角}\ \ \theta\ (^{\circ})$", fontsize=BASE_FONTSIZE)
    axes[1].set_xlabel(r"$\mathrm{径向位置}\ \ r/R$", fontsize=BASE_FONTSIZE)
    x_ticks = np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    axes[1].set_xticks(x_ticks)
    axes[1].set_xticklabels([f"{value:.2f}" for value in x_ticks])

    figure.savefig(
        OUTPUT,
        format="pdf",
        facecolor="white",
        metadata={
            "Title": "Blade geometry comparison over 0.25 <= r/R <= 0.90",
            "Subject": (
                "Figure 5, reproducibly extracted from the full-range vector source"
            ),
        },
    )
    plt.close(figure)

    print(
        json.dumps(
            {
                "source": str(SOURCE),
                "output": str(OUTPUT),
                "display_domain_r_over_R": [R_OVER_R_MIN, R_OVER_R_MAX],
                "raw_points_in_domain": [
                    int(
                        np.count_nonzero(
                            (panel["raw"][0] >= R_OVER_R_MIN)
                            & (panel["raw"][0] <= R_OVER_R_MAX)
                        )
                    )
                    for panel in panels
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
