"""Quantify the two geometry curves embedded in Figure 5.

The comparison is symmetric: neither the photogrammetry result nor the
Carroll laser-scan result is treated as ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import numpy as np


FIGURE = Path(__file__).with_name("fig5_full_range_source.pdf")
R_OVER_R_MIN = 0.25
R_OVER_R_MAX = 0.90


def _polyline(drawing: dict, axes: fitz.Rect, y_max: float) -> tuple[np.ndarray, np.ndarray]:
    items = drawing["items"]
    if not items or any(item[0] != "l" for item in items):
        raise ValueError("Expected a line-only vector path in Figure 5")

    points = np.asarray(
        [(items[0][1].x, items[0][1].y)]
        + [(item[2].x, item[2].y) for item in items],
        dtype=float,
    )
    radius = (points[:, 0] - axes.x0) / axes.width
    value = (axes.y1 - points[:, 1]) / axes.height * y_max
    return radius, value


def _metrics(reference: tuple[np.ndarray, np.ndarray], measured: tuple[np.ndarray, np.ndarray]) -> dict:
    grid = np.linspace(R_OVER_R_MIN, R_OVER_R_MAX, 5001)
    reference_values = np.interp(grid, *reference)
    measured_values = np.interp(grid, *measured)
    difference = measured_values - reference_values

    return {
        "mean_absolute_difference": float(np.mean(np.abs(difference))),
        "root_mean_square_difference": float(np.sqrt(np.mean(difference**2))),
        "maximum_absolute_difference": float(np.max(np.abs(difference))),
        "mean_symmetric_relative_difference_percent": float(
            100
            * np.mean(
                2
                * np.abs(difference)
                / (np.abs(reference_values) + np.abs(measured_values))
            )
        ),
        "pearson_correlation": float(np.corrcoef(reference_values, measured_values)[0, 1]),
        "mean_signed_difference_photogrammetry_minus_carroll": float(np.mean(difference)),
    }


def main() -> None:
    page = fitz.open(FIGURE)[0]
    drawings = page.get_drawings()

    axes = sorted(
        [
            drawing["rect"]
            for drawing in drawings
            if drawing.get("fill") == (1.0, 1.0, 1.0)
            and drawing["rect"].width > 400
            and drawing["rect"].height > 100
            and drawing["rect"].height < 200
        ],
        key=lambda rect: rect.y0,
    )
    references = sorted(
        [
            drawing
            for drawing in drawings
            if drawing.get("dashes") not in (None, "[] 0")
            and drawing["rect"].width > 400
        ],
        key=lambda drawing: drawing["rect"].y0,
    )
    photogrammetry = sorted(
        [
            drawing
            for drawing in drawings
            if drawing.get("color") is not None
            and np.allclose(drawing["color"], (0.12156863, 0.35294118, 0.6), atol=1e-4)
            and np.isclose(drawing.get("width", 0), 2.0)
            and drawing["rect"].width > 400
        ],
        key=lambda drawing: drawing["rect"].y0,
    )
    if len(axes) != 2 or len(references) != 2 or len(photogrammetry) != 2:
        raise RuntimeError("Figure 5 vector structure has changed; inspect curve selection")

    result = {
        "source": str(FIGURE),
        "comparison_domain_r_over_R": [R_OVER_R_MIN, R_OVER_R_MAX],
        "normalization": "symmetric; pointwise mean of both curves",
        "chord_ratio": _metrics(
            _polyline(references[0], axes[0], 0.24),
            _polyline(photogrammetry[0], axes[0], 0.24),
        ),
        "pitch_angle_deg": _metrics(
            _polyline(references[1], axes[1], 25.0),
            _polyline(photogrammetry[1], axes[1], 25.0),
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
