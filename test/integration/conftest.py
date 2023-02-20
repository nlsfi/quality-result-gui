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

from typing import TYPE_CHECKING, Generator, List

import pytest
from pytestqt.qtbot import QtBot

if TYPE_CHECKING:
    from quality_result_gui.api.quality_api_client import QualityResultClient
    from quality_result_gui.api.types.quality_error import QualityErrorsByPriority
    from quality_result_gui.quality_error_manager import QualityResultManager


@pytest.fixture()
def quality_result_manager(
    qgis_new_project: None,
    bypass_log_if_fails: None,
    qtbot: QtBot,
    mock_api_client: "QualityResultClient",
) -> Generator["QualityResultManager", None, None]:
    from quality_result_gui.quality_error_manager import QualityResultManager

    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    manager.dock_widget.show()

    yield manager
    manager.unload()


@pytest.fixture()
def quality_result_manager_with_data(
    quality_result_manager: "QualityResultManager",
    quality_errors: List["QualityErrorsByPriority"],
    qtbot: QtBot,
) -> "QualityResultManager":
    with qtbot.waitSignal(
        quality_result_manager._base_model.filterable_data_changed,
        timeout=200,
    ) as _:
        quality_result_manager._fetcher.results_received.emit(quality_errors)

    return quality_result_manager
