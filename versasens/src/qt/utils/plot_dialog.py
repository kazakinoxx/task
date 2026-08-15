"""File containing the dialog showing the plot."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import override

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QWidget

from src.generated.ui.utils.plot_dialog import Ui_PlotDialog
from src.generated.ui.utils.plot_overlay import Ui_PauseOverlay
from src.utils.config import Config, get_or_create_config
from src.utils.constants import PLOT_REFRESH_RATE
from src.utils.logger import logger
from src.utils.typedefs import ClearSensorDataOnClose, PlotPause, ShouldUpdateGraph
from src.versa.sensor import Sensor

os.environ["QT_API"] = "PySide6"


class PauseOverlay(QWidget, Ui_PauseOverlay):
    """Semi-transparent overlay showing a 'PAUSED' label."""

    def __init__(self, parent: QWidget) -> None:
        """
        Create a new pause overlay.

        Args:
            parent: The parent of the overlay

        """
        super().__init__(parent)
        self.setupUi(self)

        # Let mouse events pass through to the graph underneath
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Start hidden
        self.setVisible(False)

        # Install event filter to resize automatically with the parent
        parent.installEventFilter(self)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Catch resize events from the parent to resize the overlay."""
        if watched == self.parent() and event.type() == QEvent.Type.Resize:
            self.resize(self.parent().size())  # pyright: ignore[reportAttributeAccessIssue]
        return super().eventFilter(watched, event)


class Graph(pg.GraphicsLayoutWidget):
    """Custom graph class to show our sensor graphs."""

    def __init__(
        self,
        sensor: Sensor,
        should_update: ShouldUpdateGraph,
        update_pause_callback: Callable[[PlotPause], None],
        config: Config,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a new graph for the given sensor.

        Args:
            sensor: The sensor for which we want a graph
            should_update: Whether to update the graph.
            update_pause_callback: Callback to set whether the plotting is paused or
                                   not.
            config: The config of the program.
            parent: The parent of the graph. Defaults to None.

        """
        super().__init__(parent)

        self.data = sensor
        self.update_pause_callback = update_pause_callback
        self.config = config

        self.curves = sensor.plot_graphics(self)

        self.timer: QTimer | None = None

        if should_update == ShouldUpdateGraph.YES:
            self.timer = QTimer(self)
            self.timer.setInterval(PLOT_REFRESH_RATE)
            self.timer.timeout.connect(self._update_plot)
            self.timer.start()

        # Get added plots
        self.plots: list[pg.PlotItem] = [
            item for item in self.items() if isinstance(item, pg.PlotItem)
        ]

        # Native ViewBox X linking maps scene coordinates. When linked plots have
        # different pixel widths (the ADS condition strip spans two columns), that
        # produces different numerical ranges and visible jitter. Exact followers
        # instead receive the master's numerical range directly.
        self.exact_x_range_links = sensor.exact_x_range_links()
        self.exact_x_range_followers = {
            id(follower) for _, follower in self.exact_x_range_links
        }
        self.x_range_sync_callbacks: list[Callable[..., None]] = []

        # Mouse interaction
        for plot in self.plots:
            if plot.vb is None:
                continue

            is_exact_follower = id(plot) in self.exact_x_range_followers
            plot.vb.setMouseEnabled(x=not is_exact_follower, y=False)
            plot.vb.enableAutoRange(x=not is_exact_follower, y=True)
            plot.vb.setAutoVisible(x=not is_exact_follower, y=True)

        for master, follower in self.exact_x_range_links:
            if master.vb is None or follower.vb is None:
                continue

            def sync_x_range(
                _view_box: pg.ViewBox,
                x_range: tuple[float, float],
                target: pg.PlotItem = follower,
            ) -> None:
                if target.vb is not None:
                    target.vb.setXRange(x_range[0], x_range[1], padding=0)

            master.vb.sigXRangeChanged.connect(sync_x_range)
            self.x_range_sync_callbacks.append(sync_x_range)
            sync_x_range(master.vb, master.vb.viewRange()[0])

    @Slot()
    def _update_plot(self) -> None:
        # Don't update if the context menu is open for one of the plots
        # This is needed so the values in the context menu are not automatically
        # overwritten
        for plot in self.plots:
            if plot.vb and plot.vb.menu and plot.vb.menu.isVisible():
                self.update_pause_callback(PlotPause.PAUSED)
                return

        self.update_pause_callback(PlotPause.RUNNING)

        self.data.update_plot_graphics(self.curves, self.config)

        for plot in self.plots:
            if plot.vb is None:
                continue

            # Force follow x axis
            if id(plot) in self.exact_x_range_followers:
                plot.vb.disableAutoRange(axis=pg.ViewBox.XAxis)
            else:
                plot.vb.enableAutoRange(x=True)

        # Also restore exact followers explicitly. This covers layout changes or
        # context-menu operations that do not emit a new master range signal.
        for master, follower in self.exact_x_range_links:
            if master.vb is None or follower.vb is None:
                continue
            x_range = master.vb.viewRange()[0]
            follower.vb.setXRange(x_range[0], x_range[1], padding=0)

    def stop(self) -> None:
        """Manually stop the internal timers."""
        if self.timer is not None:
            self.timer.stop()


class PlotDialog(QDialog, Ui_PlotDialog):
    """Dialog shown when plottig a sensor."""

    def __init__(  # noqa: PLR0913
        self,
        data: Sensor,
        should_update: ShouldUpdateGraph,
        config_path: Path,
        clear_sensor_data_on_close: ClearSensorDataOnClose = ClearSensorDataOnClose.NO,
        set_is_open: Callable[[bool], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a new dialog showing the plot of the given sensor.

        Args:
            data: The sensor to plot
            set_is_open: Function that sets whether the plot is open.
                         Defaults to None.
            should_update: Whether the graph needs to be updated.
            config_path: Path to the config file.
            clear_sensor_data_on_close: Whether the data of the sensor needs to be
                                        cleared when closing the dialog.
                                        Defaults to ClearSensorDataOnClose.NO.
            parent: The parent of the dialog. Defaults to None.

        """
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=True)

        self.setupUi(self)

        self.set_is_open = set_is_open
        if self.set_is_open is not None:
            self.set_is_open(True)

        self.clear_sensor_data = clear_sensor_data_on_close

        # Setup graph manually
        self.plot_pause_state = PlotPause.RUNNING

        config = get_or_create_config(config_path)
        self.graph = Graph(data, should_update, self._plot_pause, config, parent=self)
        self.base_layout.replaceWidget(self.placeholder, self.graph)

        self.overlay = PauseOverlay(self.graph)

        self.setWindowTitle(f"{data.name()} plots")
        self.data = data

    def _plot_pause(self, paused: PlotPause) -> None:
        # If state didn't change, return
        if paused == self.plot_pause_state:
            return

        logger.debug(f"Plot is {paused}")

        self.plot_pause_state = paused

        is_paused = paused == PlotPause.PAUSED
        self.overlay.setVisible(is_paused)

    @override
    def closeEvent(self, arg__1: QCloseEvent) -> None:
        if self.set_is_open is not None:
            self.set_is_open(False)

        if self.clear_sensor_data == ClearSensorDataOnClose.YES:
            self.data.clear()

        self.graph.stop()

        return super().closeEvent(arg__1)
