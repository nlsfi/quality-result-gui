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

from typing import TYPE_CHECKING

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import Qt
from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget

if TYPE_CHECKING:
    from qgis.PyQt.QtWidgets import QShortcut


@pytest.fixture()
def dock_widget(qtbot: QtBot) -> QualityErrorsDockWidget:
    dock_widget = QualityErrorsDockWidget()
    qtbot.addWidget(dock_widget)
    return dock_widget


def test_quality_errors_dock_opens_and_closes(dock_widget: QualityErrorsDockWidget):
    dock_widget.show()

    assert dock_widget.isVisible() is True

    dock_widget.close()

    assert dock_widget.isVisible() is False


@pytest.mark.parametrize(
    "has_filters_active",
    [True, False],
    ids=[
        "has active filters",
        "does not have active filters",
    ],
)
def test_update_filter_menu_icon_state(mocker: MockerFixture, has_filters_active: bool):
    dock_widget = QualityErrorsDockWidget()
    m_is_any_filter_active = mocker.patch.object(
        dock_widget.filter_menu,
        "is_any_filter_active",
        return_value=has_filters_active,
        autospec=True,
    )

    dock_widget._update_filter_menu_icon_state()

    m_is_any_filter_active.assert_called_once()

    assert dock_widget.filter_button.isDown() is has_filters_active


def test_shortcut_for_toggle_errors_toggles_checkbox(
    dock_widget: QualityErrorsDockWidget,
) -> None:
    dock_widget.show()

    shortcut = dock_widget.shortcut_for_toggle_errors
    checkbox = dock_widget.show_errors_on_map_check_box
    assert (
        shortcut.key().toString()
        == QualityErrorsDockWidget.SHORTCUT_TOGGLE_ERRORS_ON_MAP_FILTER
    )
    assert checkbox.checkState() == Qt.CheckState.Checked

    # Simulate shortcut activation
    shortcut.activated.emit()

    assert checkbox.checkState() == Qt.CheckState.Unchecked

    # Set checkbox manually
    checkbox.setChecked(True)
    assert checkbox.checkState() == Qt.CheckState.Checked

    # Simulate shortcut activation
    shortcut.activated.emit()
    assert checkbox.checkState() == Qt.CheckState.Unchecked


def test_shortcut_for_toggle_errors_works_when_dock_widget_is_reopened(
    dock_widget: QualityErrorsDockWidget,
) -> None:
    dock_widget.show()
    dock_widget.close()

    # Reopen
    dock_widget.show()

    # Simulate shortcut activation
    dock_widget.shortcut_for_toggle_errors.activated.emit()

    checkbox = dock_widget.show_errors_on_map_check_box
    assert checkbox.checkState() == Qt.CheckState.Unchecked


def test_customizing_shortcut_key_for_toggle_errors(
    dock_widget: QualityErrorsDockWidget,
) -> None:
    # Test default shortcut key
    dock_widget.show()

    registered_shortcut: QShortcut = next(
        iter(
            [
                shortcut
                for shortcut in QgsGui.shortcutsManager().listShortcuts()
                if shortcut.objectName()
                == dock_widget.shortcut_for_toggle_errors.objectName()
            ]
        )
    )
    assert (
        registered_shortcut.key().toString()
        == QualityErrorsDockWidget.SHORTCUT_TOGGLE_ERRORS_ON_MAP_FILTER
    )

    # Reopen with customized shortcut key
    dock_widget.close()
    dock_widget.SHORTCUT_TOGGLE_ERRORS_ON_MAP_FILTER = "Ctrl+Alt+L"
    dock_widget.show()

    registered_shortcut = next(
        iter(
            [
                shortcut
                for shortcut in QgsGui.shortcutsManager().listShortcuts()
                if shortcut.objectName()
                == dock_widget.shortcut_for_toggle_errors.objectName()
            ]
        )
    )
    assert registered_shortcut.key().toString() == "Ctrl+Alt+L"
