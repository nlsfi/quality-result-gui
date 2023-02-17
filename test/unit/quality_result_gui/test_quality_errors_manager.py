#  Copyright (C) 2023 National Land Survey of Finland
#  (https://www.maanmittauslaitos.fi/en).
#
#
#  This file is part of quality-result-gui.
#
#  quality-result-gui is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  quality-result-gui is distributed in the hope that it will be
#  useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with quality-result-gui. If not, see <https://www.gnu.org/licenses/>.

from typing import Callable, Generator, Optional

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QMenu

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_errors_filters import (
    ATTRIBUTE_NAME_FILTER_MENU_LABEL,
    ERROR_TYPE_FILTER_MENU_LABEL,
    FEATURE_TYPE_FILTER_MENU_LABEL,
)


@pytest.fixture()
def quality_errors_manager(
    qgis_new_project: None, qtbot: QtBot, mock_api_client: QualityResultClient
) -> Generator[QualityResultManager, None, None]:
    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    yield manager

    manager.unload()


def test_quality_result_manager_inits_correctly(
    qtbot: QtBot,
    mock_api_client: QualityResultClient,
    is_action_present: Callable[[QMenu, str], Optional[QMenu]],
):
    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    # filter menu + 3 filters + reset all filters action
    assert len(manager.dock_widget.filter_menu.actions()) == 5

    for action_name in [
        FEATURE_TYPE_FILTER_MENU_LABEL,
        ERROR_TYPE_FILTER_MENU_LABEL,
        ATTRIBUTE_NAME_FILTER_MENU_LABEL,
        "Reset filters",
    ]:
        assert is_action_present(manager.dock_widget.filter_menu, action_name)

    assert len(list(QgsProject.instance().mapLayers().values())) == 1
    assert manager._fetcher._thread is None

    manager.dock_widget.deleteLater()


def test_quality_result_manager_unloads_correctly(
    qtbot: QtBot, mock_api_client: QualityResultClient
):
    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    manager.unload()

    assert len(list(QgsProject.instance().mapLayers().values())) == 0
    assert manager._fetcher._thread is None


def test_show_dock_widget_starts_fetcher_and_shows_widget(
    mocker: MockerFixture, quality_errors_manager: QualityResultManager
):
    assert quality_errors_manager._fetcher._thread is None

    m_show_widget = mocker.spy(quality_errors_manager.dock_widget, "show")

    quality_errors_manager.show_dock_widget()

    m_show_widget.assert_called_once()
    assert len(list(QgsProject.instance().mapLayers().values())) == 1
    assert quality_errors_manager._fetcher._thread is not None
