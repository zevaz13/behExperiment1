"""Shared helper for exporting pyqtgraph plots to PNG (M13)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget
from pyqtgraph import PlotWidget
from pyqtgraph.exporters import ImageExporter


def save_plot_widgets(parent: QWidget, plots: dict[str, PlotWidget], default_name: str) -> None:
    """Prompts for a filename, then exports each named plot as a PNG.

    A single plot is saved to the chosen path as-is; with several plots, each
    one's name is inserted before the extension (e.g. "run-hue_mean.png").
    """
    path, _ = QFileDialog.getSaveFileName(parent, "Save figure(s)", default_name, "PNG images (*.png)")
    if not path:
        return
    base = Path(path)
    items = list(plots.items())
    if len(items) == 1:
        targets = [(items[0][1], base)]
    else:
        suffix = base.suffix or ".png"
        targets = [(widget, base.with_name(f"{base.stem}-{name}{suffix}")) for name, widget in items]
    for widget, target in targets:
        ImageExporter(widget.plotItem).export(str(target))
