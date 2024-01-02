#  Copyright (C) 2023-2024 National Land Survey of Finland
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

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from pytestqt.qtbot import QtBot
from qgis.core import QgsField, QgsProject, QgsVectorLayer, edit
from qgis.PyQt.QtCore import QVariant

if TYPE_CHECKING:
    from quality_result_gui.api.quality_api_client import QualityResultClient
    from quality_result_gui.api.types.quality_error import QualityError
    from quality_result_gui.quality_error_manager import QualityResultManager
    from quality_result_gui.ui.quality_errors_tree_filter_menu import (
        QualityErrorsTreeFilterMenu,
    )


@pytest.fixture()
def quality_result_manager(
    qgis_new_project: None,
    _bypass_log_if_fails: None,
    qtbot: QtBot,
    mock_api_client: "QualityResultClient",
    monkeypatch: pytest.MonkeyPatch,
) -> Generator["QualityResultManager", None, None]:
    from quality_result_gui.quality_error_manager import QualityResultManager

    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    monkeypatch.setenv("IS_DEVELOPMENT_MODE", "f")
    manager.dock_widget.show()

    yield manager
    manager.unload()


@pytest.fixture()
def quality_result_manager_with_data(
    quality_result_manager: "QualityResultManager",
    quality_errors: list["QualityError"],
    qtbot: QtBot,
) -> "QualityResultManager":
    with qtbot.waitSignal(
        quality_result_manager._base_model.filterable_data_changed,
        timeout=200,
    ) as _:
        quality_result_manager._fetcher.results_received.emit(quality_errors)

    return quality_result_manager


@pytest.fixture()
def quality_result_manager_with_data_and_layer_mapping(
    quality_result_manager: "QualityResultManager",
    quality_errors: list["QualityError"],
    qtbot: QtBot,
) -> Generator["QualityResultManager", None, None]:
    layer = QgsVectorLayer("NoGeometry", "mock", "memory")
    with edit(layer):
        field = QgsField("height_relative", QVariant.String)
        field.setAlias("height relative alias")
        layer.setName("chimney point alias")
        layer.dataProvider().addAttributes([field])
    QgsProject.instance().addMapLayer(layer, False)
    quality_result_manager.set_layer_mapping({"chimney_point": layer.id()})
    with qtbot.waitSignal(
        quality_result_manager._base_model.filterable_data_changed,
        timeout=200,
    ) as _:
        quality_result_manager._fetcher.results_received.emit(quality_errors)

    yield quality_result_manager
    quality_result_manager.set_layer_mapping({})
    QgsProject.instance().removeMapLayer(layer.id())


@pytest.fixture()
def filter_menu_with_chimney_point_alias(
    quality_result_manager_with_data_and_layer_mapping: "QualityResultManager",
) -> "QualityErrorsTreeFilterMenu":
    return quality_result_manager_with_data_and_layer_mapping.dock_widget.filter_menu
