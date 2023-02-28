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
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot
from qgis.core import QgsLayerTree, QgsProject
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import QModelIndex, Qt
from qgis.PyQt.QtWidgets import QMenu

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorsByPriority,
)
from quality_result_gui.configuration import QualityLayerStyleConfig
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_errors_filters import (
    ATTRIBUTE_NAME_FILTER_MENU_LABEL,
    ERROR_TYPE_FILTER_MENU_LABEL,
    FEATURE_TYPE_FILTER_MENU_LABEL,
)
from quality_result_gui.style.default_style import DefaultErrorSymbol
from quality_result_gui.style.quality_layer_error_symbol import ErrorSymbol


@pytest.fixture()
def quality_result_manager(
    qgis_new_project: None, qtbot: QtBot, mock_api_client: QualityResultClient
) -> Generator[QualityResultManager, None, None]:
    manager = QualityResultManager(mock_api_client, None)
    qtbot.addWidget(manager.dock_widget)

    yield manager

    manager.unload()


@pytest.fixture()
def quality_result_manager_with_data(
    quality_result_manager: QualityResultManager,
    quality_errors: list[QualityErrorsByPriority],
    qtbot: QtBot,
) -> QualityResultManager:
    with qtbot.waitSignal(
        quality_result_manager._base_model.filterable_data_changed,
        timeout=200,
    ) as _:
        quality_result_manager._fetcher.results_received.emit(quality_errors)

    return quality_result_manager


@pytest.fixture()
def m_user_processed_callback() -> MagicMock:
    return MagicMock()


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
    mocker: MockerFixture, quality_result_manager: QualityResultManager
):
    assert quality_result_manager._fetcher._thread is None

    m_show_widget = mocker.spy(quality_result_manager.dock_widget, "show")

    quality_result_manager.show_dock_widget()

    m_show_widget.assert_called_once()
    assert len(list(QgsProject.instance().mapLayers().values())) == 1
    assert quality_result_manager._fetcher._thread is not None


@pytest.mark.skip("Checkbox values are not preseved anymore when dialog is closed")
def test_close_and_reopen_preserves_error_visibility_on_map(
    mock_api_client: QualityResultClient,
) -> None:

    quality_result_manager = QualityResultManager(mock_api_client, None)

    def _check_quality_layer_visibility(expected_visibility: bool) -> None:
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        quality_layer = (
            quality_result_manager.visualizer._quality_error_layer.find_layer_from_project()
        )
        assert quality_layer is not None
        tree_node = root.findLayer(quality_layer.id())
        assert tree_node is not None
        assert tree_node.itemVisibilityChecked() == expected_visibility

    show_errors_on_map_check_box = (
        quality_result_manager.dock_widget.show_errors_on_map_check_box
    )
    assert show_errors_on_map_check_box.isChecked() is True
    _check_quality_layer_visibility(True)

    #  Hide errors
    show_errors_on_map_check_box.setChecked(False)
    _check_quality_layer_visibility(False)

    # Close and reopen dialog
    quality_result_manager.unload()

    quality_result_manager = QualityResultManager(mock_api_client, None)

    assert not show_errors_on_map_check_box.isChecked()
    # Check that quality layer is not visible
    _check_quality_layer_visibility(False)

    quality_result_manager.unload()


@pytest.mark.parametrize(
    (
        "value",
        "role",
        "expected_check_state",
        "expected_callback_value",
        "callback_called",
    ),
    [
        (-1, Qt.EditRole, Qt.Unchecked, None, False),
        (Qt.Checked, Qt.CheckStateRole, Qt.Checked, True, True),
        (Qt.Unchecked, Qt.CheckStateRole, Qt.Unchecked, False, True),
    ],
)
def test_model_set_data_user_processed(
    quality_result_manager_with_data: QualityResultManager,
    m_user_processed_callback: MagicMock,
    value: int,
    role: Qt.ItemDataRole,
    expected_check_state: int,
    expected_callback_value: bool,
    callback_called: bool,
) -> None:

    quality_result_manager_with_data.error_checked.connect(m_user_processed_callback)

    model = quality_result_manager_with_data._styled_model
    first_error_row_index = model.index(
        0, 0, model.index(0, 0, model.index(0, 0, model.index(0, 0, QModelIndex())))
    )

    model.setData(first_error_row_index, value, role)
    check_state = model.data(first_error_row_index, Qt.CheckStateRole)
    assert check_state == expected_check_state

    if callback_called:
        m_user_processed_callback.assert_called_with("1", expected_callback_value)
    else:
        m_user_processed_callback.assert_not_called()


def test_override_quality_layer_style_changes_annotation_style(
    qtbot: QtBot,
    mock_api_client: QualityResultClient,
    single_quality_error: list[QualityErrorsByPriority],
):
    class MockStyle(QualityLayerStyleConfig):
        def create_error_symbol(self, quality_error: QualityError) -> ErrorSymbol:
            symbol = DefaultErrorSymbol(quality_error)
            symbol.style.marker_size = 500
            return symbol

    manager = QualityResultManager(mock_api_client, None, MockStyle())
    qtbot.addWidget(manager.dock_widget)

    with qtbot.waitSignal(
        manager._base_model.filterable_data_changed,
        timeout=200,
    ) as _:
        manager._fetcher.results_received.emit(single_quality_error)

    quality_layer = manager.visualizer._quality_error_layer
    annotation_layer = quality_layer.find_layer_from_project()
    assert annotation_layer is not None

    annotation_item = annotation_layer.items()[quality_layer._annotation_ids["1"][0]]

    assert annotation_item.symbol().size() == 500

    manager.dock_widget.deleteLater()


def test_shortcut_for_toggle_errors_is_unregistered_after_unload(
    quality_result_manager: QualityResultManager,
) -> None:

    quality_result_manager.show_dock_widget()

    shortcut_name = (
        quality_result_manager.dock_widget.shortcut_for_toggle_errors.objectName()
    )

    assert shortcut_name in [
        shortcut.objectName() for shortcut in QgsGui.shortcutsManager().listShortcuts()
    ]

    quality_result_manager.unload()

    assert shortcut_name not in [
        shortcut.objectName() for shortcut in QgsGui.shortcutsManager().listShortcuts()
    ]
