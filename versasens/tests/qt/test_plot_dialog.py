import pytest
from pytestqt.qtbot import QtBot

from src.qt.utils.plot_dialog import Graph
from src.utils.config import Config
from src.utils.typedefs import PlotPause, ShouldUpdateGraph
from src.versa.sensors.ads import ADS


def test_ads_condition_uses_exact_channel_x_range(
    qtbot: QtBot,
    config: Config,
) -> None:
    ads = ADS()
    sample_count = 750
    ads.time_list = list(range(64_000, 64_000 + sample_count * 8, 8))
    ads.idx_list = [(index * 4) & 0xFF for index in range(sample_count)]
    ads.condition_id_list = [
        int(index >= sample_count // 2) for index in range(sample_count)
    ]
    ads.loff_statp_list = [0] * sample_count
    ads.loff_stat_x_list = [condition << 2 for condition in ads.condition_id_list]
    for channel in ads._channels_data():
        channel.extend([0.0] * sample_count)

    pauses: list[PlotPause] = []
    graph = Graph(
        ads,
        ShouldUpdateGraph.NO,
        pauses.append,
        config,
    )
    qtbot.addWidget(graph)
    graph.resize(1000, 650)
    graph.show()

    graph._update_plot()
    qtbot.wait(50)

    channel_range = ads.plots[0].vb.viewRange()[0]
    condition_range = ads.plots[-1].vb.viewRange()[0]
    assert condition_range == pytest.approx(channel_range)
