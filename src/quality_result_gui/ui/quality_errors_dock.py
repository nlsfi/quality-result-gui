#  Copyright (C) 2022-2023 National Land Survey of Finland
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

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from qgis.core import QgsApplication
from qgis.gui import QgsGui
from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDockWidget, QShortcut
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.ui.quality_errors_tree_filter_menu import (
    QualityErrorsTreeFilterMenu,
)

if TYPE_CHECKING:
    from qgis.PyQt.QtGui import QCloseEvent
    from qgis.PyQt.QtWidgets import QCheckBox, QLabel, QToolButton, QWidget

    from quality_result_gui.ui.quality_error_tree_view import QualityErrorTreeView


LOGGER = logging.getLogger(__name__)

DOCK_UI: "QWidget"
DOCK_UI, _ = uic.loadUiType(
    str(Path(__file__).parent.joinpath("quality_errors_dock.ui"))
)


class QualityErrorsDockWidget(QDockWidget, DOCK_UI):
    """
    Graphical user interface for quality errors dock widget.
    """

    SHORTCUT_TOGGLE_ERRORS_ON_MAP_FILTER = "Alt+Q"

    closed = pyqtSignal()

    # type necessary widgets that are provided from the .ui
    error_tree_view: "QualityErrorTreeView"
    filter_button: "QToolButton"
    info_label: "QLabel"
    filter_with_map_extent_check_box: "QCheckBox"
    show_errors_on_map_check_box: "QCheckBox"
    show_user_processed_errors_check_box: "QCheckBox"

    def __init__(self, parent: Optional["QWidget"] = None) -> None:
        super().__init__(parent)
        self.setupUi(self)

        self.shortcut_for_toggle_errors = QShortcut(self)
        self.shortcut_for_toggle_errors.setObjectName(
            "Toggle show errors on map filter"
        )
        self.shortcut_for_toggle_errors.setWhatsThis(
            tr("Toggle show errors on map filter")
        )
        self.shortcut_for_toggle_errors.activated.connect(
            self.show_errors_on_map_check_box.toggle
        )

        self.filter_menu = QualityErrorsTreeFilterMenu(self)
        self.filter_button.setIcon(QgsApplication.getThemeIcon("/mActionFilter2.svg"))
        self.filter_button.setMenu(self.filter_menu)

        self._update_filter_menu_icon_state()

    def _update_filter_menu_icon_state(self) -> None:
        if self.filter_menu.is_any_filter_active():
            self.filter_button.setDown(True)
        else:
            self.filter_button.setDown(False)

    def _register_shortcut(self) -> None:
        QgsGui.shortcutsManager().registerShortcut(
            self.shortcut_for_toggle_errors,
            self.SHORTCUT_TOGGLE_ERRORS_ON_MAP_FILTER,
        )

    def show(self) -> None:
        self._register_shortcut()
        return super().show()

    def closeEvent(self, event: "QCloseEvent") -> None:  # noqa: N802 (qt override)
        QgsGui.shortcutsManager().unregisterShortcut(self.shortcut_for_toggle_errors)

        self.closed.emit()
        return super().closeEvent(event)
