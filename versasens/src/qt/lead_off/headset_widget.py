"""Custom widget drawing the headset electrode contact (lead-off) map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from src.versa.sensors.ads import LeadOffStatus

# Reference coordinate system the layout is authored in; painted scaled-to-fit.
REF_W = 400.0
REF_H = 470.0

# Window lightness below which the viewer is treated as using a dark theme.
_DARK_LIGHTNESS = 0.5

# Electrode states
OK = "ok"
OFF = "off"
NODATA = "nodata"

# Colour-blind-safe glyphs: check mark, ballot X, hyphen.
GLYPH = {OK: "✓", OFF: "✗", NODATA: "-"}


@dataclass(frozen=True)
class Electrode:
    """One electrode marker on the head diagram."""

    key: str          # "ch1".."ch8", "ref", "bias"
    site: str         # label shown inside the node (placeholder montage)
    label: str        # label shown below the node
    x: float
    y: float
    kind: str         # "eeg" | "ref" | "bias"


# NOTE: channel -> scalp positions are a placeholder montage. Adjust x/y/site
# here to match the real headset layout; nothing else needs to change.
ELECTRODES: list[Electrode] = [
    Electrode("ch1", "Fp1", "CH1", 158, 126, "eeg"),
    Electrode("ch2", "Fp2", "CH2", 242, 126, "eeg"),
    Electrode("ch3", "C3", "CH3", 118, 236, "eeg"),
    Electrode("ch4", "C4", "CH4", 282, 236, "eeg"),
    Electrode("ch5", "P3", "CH5", 150, 332, "eeg"),
    Electrode("ch6", "P4", "CH6", 250, 332, "eeg"),
    Electrode("ch7", "O1", "CH7", 172, 402, "eeg"),
    Electrode("ch8", "O2", "CH8", 228, 402, "eeg"),
    Electrode("ref", "REF", "Reference", 92, 360, "ref"),
    Electrode("bias", "BIAS", "Bias (RLD)", 308, 360, "bias"),
]


class HeadsetStatusWidget(QWidget):
    """Top-down head diagram whose electrode nodes turn green/red/grey."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the widget with every electrode in the "no data" state."""
        super().__init__(parent)
        self.setMinimumSize(320, 380)
        self._states: dict[str, str] = {e.key: NODATA for e in ELECTRODES}

    # ------------------------------------------------------------------ API
    def set_status(
        self,
        status: LeadOffStatus | None,
        *,
        stale: bool = False,
    ) -> None:
        """
        Update the displayed electrode states and repaint.

        Args:
            status: The decoded lead-off status, or None if no data is available.
            stale: When True, show every electrode as "no data" (stream stopped
                   or no fresh sample), regardless of ``status``.

        """
        if status is None or stale:
            self._states = {e.key: NODATA for e in ELECTRODES}
        else:
            new: dict[str, str] = {}
            for i in range(8):
                new[f"ch{i + 1}"] = OFF if status.channels[i] else OK
            new["ref"] = OFF if status.reference else OK
            new["bias"] = OFF if status.bias else OK
            self._states = new
        self.update()

    # --------------------------------------------------------------- colors
    def _is_dark(self) -> bool:
        return self.palette().window().color().lightnessF() < _DARK_LIGHTNESS

    def _colors(self) -> dict[str, QColor]:
        if self._is_dark():
            return {
                OK: QColor("#2ec27e"),
                OFF: QColor("#ff5b62"),
                NODATA: QColor("#5d6c77"),
                "head": QColor("#14202a"),
                "border": QColor("#293742"),
                "band": QColor("#2bb7c4"),
                "text": QColor("#e8eef2"),
                "muted": QColor("#93a6b3"),
                "surface": QColor("#151f27"),
            }
        return {
            OK: QColor("#12a568"),
            OFF: QColor("#e0403f"),
            NODATA: QColor("#93a2ad"),
            "head": QColor("#f3f6f9"),
            "border": QColor("#d5dee6"),
            "band": QColor("#0e7c86"),
            "text": QColor("#16212b"),
            "muted": QColor("#5c6c7b"),
            "surface": QColor("#ffffff"),
        }

    # ---------------------------------------------------------------- paint
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802, ARG002
        """Render the head outline and every electrode node."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        scale = min(w / REF_W, h / REF_H)
        ox = (w - REF_W * scale) / 2.0
        oy = (h - REF_H * scale) / 2.0

        def tx(x: float) -> float:
            return ox + x * scale

        def ty(y: float) -> float:
            return oy + y * scale

        c = self._colors()

        # --- headset band (product cue) ---
        band = QPainterPath()
        band.moveTo(tx(64), ty(168))
        band.quadTo(tx(200), ty(34), tx(336), ty(168))
        band_pen = QPen(c["band"], 9 * scale)
        band_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        band_col = QColor(c["band"])
        band_col.setAlphaF(0.35)
        band_pen.setColor(band_col)
        p.setPen(band_pen)
        p.drawPath(band)

        # --- ears / earcups ---
        p.setPen(QPen(c["border"], 2 * scale))
        p.setBrush(c["surface"])
        for ex in (34.0, 340.0):
            p.drawRoundedRect(
                QRectF(tx(ex), ty(212), 26 * scale, 66 * scale),
                12 * scale,
                12 * scale,
            )

        # --- head outline ---
        p.setPen(QPen(c["border"], 2 * scale))
        p.setBrush(c["head"])
        head_rect = QRectF(tx(50), ty(50), 300 * scale, 384 * scale)
        p.drawEllipse(head_rect)

        # --- nose ---
        nose = QPainterPath()
        nose.moveTo(tx(184), ty(56))
        nose.lineTo(tx(200), ty(30))
        nose.lineTo(tx(216), ty(56))
        nose.closeSubpath()
        p.drawPath(nose)

        # --- "FRONT" marker ---
        p.setPen(c["muted"])
        f = QFont()
        f.setPixelSize(max(8, int(10 * scale)))
        p.setFont(f)
        p.drawText(
            QRectF(tx(150), ty(8), 100 * scale, 16 * scale),
            Qt.AlignmentFlag.AlignCenter,
            "FRONT",
        )

        # --- electrode nodes ---
        for e in ELECTRODES:
            self._draw_node(p, e, scale, tx(e.x), ty(e.y), c)

        p.end()

    def _draw_node(  # noqa: PLR0913
        self,
        p: QPainter,
        e: Electrode,
        scale: float,
        cx: float,
        cy: float,
        c: dict[str, QColor],
    ) -> None:
        state = self._states[e.key]
        fill = c[state]
        r = 25 * scale

        p.setPen(QPen(c["surface"], 2.5 * scale))
        p.setBrush(fill)
        if e.kind == "eeg":
            p.drawEllipse(QPointF(cx, cy), r, r)
        else:
            side = 42 * scale
            p.drawRoundedRect(
                QRectF(cx - side / 2, cy - side / 2, side, side),
                8 * scale,
                8 * scale,
            )

        # site label centered inside the node
        p.setPen(QColor("#ffffff"))
        f_site = QFont()
        f_site.setBold(True)
        f_site.setPixelSize(max(9, int(12.5 * scale)))
        p.setFont(f_site)
        p.drawText(
            QRectF(cx - r, cy - r, 2 * r, 2 * r),
            Qt.AlignmentFlag.AlignCenter,
            e.site,
        )

        # channel label below the node
        p.setPen(c["muted"])
        f_ch = QFont()
        f_ch.setPixelSize(max(8, int(9.5 * scale)))
        p.setFont(f_ch)
        p.drawText(
            QRectF(cx - r, cy + r + 1 * scale, 2 * r, 14 * scale),
            Qt.AlignmentFlag.AlignCenter,
            e.label,
        )

        # small state badge (colour-blind-safe glyph) at the top-right
        br = 9 * scale
        bx = cx + r - br * 0.7
        by = cy - r + br * 0.7
        badge = QColor(fill).darker(118)
        p.setPen(QPen(c["surface"], 1.5 * scale))
        p.setBrush(badge)
        p.drawEllipse(QPointF(bx, by), br, br)
        p.setPen(QColor("#ffffff"))
        f_g = QFont()
        f_g.setBold(True)
        f_g.setPixelSize(max(8, int(11 * scale)))
        p.setFont(f_g)
        p.drawText(
            QRectF(bx - br, by - br, 2 * br, 2 * br),
            Qt.AlignmentFlag.AlignCenter,
            GLYPH[state],
        )
