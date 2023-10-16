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
from typing import Optional, cast

import qgis_plugin_tools
import quality_result_gui
from qgis.core import QgsApplication, QgsProject
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, Qt, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.custom_logging import setup_loggers
from qgis_plugin_tools.tools.i18n import setup_translation, tr
from qgis_plugin_tools.tools.resources import resources_path
from quality_result_gui.env import IS_DEVELOPMENT_MODE, TEST_JSON_FILE_PATH
from quality_result_gui.quality_error_manager import QualityResultManager

import quality_result_gui_plugin
from quality_result_gui_plugin.dev_tools.dev_tools_dialog import DevToolsDialog
from quality_result_gui_plugin.dev_tools.mock_api_client import MockQualityResultClient

LOGGER = logging.getLogger(__name__)

iface = cast(QgisInterface, utils_iface)


class QualityResultGuiPlugin:
    def __init__(self) -> None:
        self._teardown_loggers = lambda: None

        self.quality_error_manager: Optional[QualityResultManager] = None

        # Initialize locale
        _, file_path = setup_translation()
        if file_path:
            self.translator = QTranslator()
            self.translator.load(file_path)
            QCoreApplication.installTranslator(self.translator)

        self._menu_name = tr("Quality result GUI")

        self.show_dev_tools_dialog_action: Optional[QAction] = None
        self.dev_tools_dialog: Optional[DevToolsDialog] = None
        self.dev_tool_action: Optional[QAction] = None
        self._test_json_file_path = ""

    def initGui(self) -> None:  # (qgis naming)
        self._teardown_loggers = setup_loggers(
            quality_result_gui.__name__,
            quality_result_gui_plugin.__name__,
            qgis_plugin_tools.__name__,
            message_log_name=tr("Quality result GUI"),
        )

        # Add action to show dev tools dialog to menu
        self.show_dev_tools_dialog_action = QAction(
            QgsApplication.getThemeIcon("/propertyicons/settings.svg"),
            tr("Development tools"),
            iface.mainWindow(),
        )
        self.show_dev_tools_dialog_action.triggered.connect(
            self._on_open_dev_tools_called
        )

        iface.addPluginToMenu(self._menu_name, self.show_dev_tools_dialog_action)

        # Add shortcut action to open qulity results form example json when in dev mode
        if IS_DEVELOPMENT_MODE and self.dev_tool_action is None:
            self._test_json_file_path = TEST_JSON_FILE_PATH or ""
            self.dev_tool_action = QAction(
                QIcon(resources_path("icons/quality_result_gui.svg")),
                "Test quality result GUI",
                iface.mainWindow(),
            )
            self.dev_tool_action.triggered.connect(
                self._toggle_quality_result_gui_in_dev_mode
            )
            iface.addToolBarIcon(self.dev_tool_action)

    def unload(self) -> None:
        iface.removePluginMenu(self._menu_name, self.show_dev_tools_dialog_action)

        self._unload_quality_error_manager_if_exists()

        self._teardown_loggers()
        self._teardown_loggers = lambda: None

        if self.dev_tool_action:
            iface.removeToolBarIcon(self.dev_tool_action)

    def _unload_quality_error_manager_if_exists(self) -> None:
        if self.quality_error_manager:
            iface.removeDockWidget(self.quality_error_manager.dock_widget)

            self.quality_error_manager.unload()
            self.quality_error_manager = None

    def _on_open_dev_tools_called(self) -> None:
        dialog = DevToolsDialog(iface.mainWindow())
        if dialog.exec_():
            self._test_json_file_path = (
                dialog.quality_errors_data_file_widget.filePath()
            )
            self._unload_quality_error_manager_if_exists()
            self._create_quality_result_gui_in_dev_mode()

    def _toggle_quality_result_gui_in_dev_mode(self) -> None:
        if self.quality_error_manager is None:
            return self._create_quality_result_gui_in_dev_mode()
        if self.quality_error_manager.dock_widget.isVisible():
            self.quality_error_manager.hide_dock_widget()
        else:
            self.quality_error_manager.show_dock_widget()

    def _create_quality_result_gui_in_dev_mode(self) -> None:
        api_client = MockQualityResultClient(Path(self._test_json_file_path))
        QgsProject.instance().setCrs(api_client.get_crs())

        self.quality_error_manager = QualityResultManager(
            api_client, iface.mainWindow()
        )
        self.quality_error_manager.closed.connect(
            self.quality_error_manager.hide_dock_widget
        )

        iface.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.quality_error_manager.dock_widget,
        )
        self.quality_error_manager.show_dock_widget()
