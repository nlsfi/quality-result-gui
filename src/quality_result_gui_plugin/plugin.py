#  Copyright (C) 2022 National Land Survey of Finland
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
from qgis.core import QgsApplication, QgsProject
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, Qt, QTranslator
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.custom_logging import setup_loggers
from qgis_plugin_tools.tools.i18n import setup_translation, tr

import quality_result_gui
import quality_result_gui_plugin
from quality_result_gui.quality_error_manager import QualityResultManager
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

        self.dev_tools_action: Optional[QAction] = None
        self.dev_tools_dialog: Optional[DevToolsDialog] = None

    def initGui(self) -> None:  # noqa: N802 (qgis naming)
        self._teardown_loggers = setup_loggers(
            quality_result_gui.__name__,
            quality_result_gui_plugin.__name__,
            qgis_plugin_tools.__name__,
            message_log_name=tr("Quality result GUI"),
        )

        # Add action
        self.dev_tools_action = QAction(
            QgsApplication.getThemeIcon("/propertyicons/settings.svg"),
            tr("Development tools"),
            iface.mainWindow(),
        )
        self.dev_tools_action.triggered.connect(self._on_open_dev_tools_called)

        iface.addPluginToMenu(self._menu_name, self.dev_tools_action)

    def unload(self) -> None:
        iface.removePluginMenu(self._menu_name, self.dev_tools_action)

        self._unload_quality_error_manager_if_exists()

        self._teardown_loggers()
        self._teardown_loggers = lambda: None

    def _unload_quality_error_manager_if_exists(self) -> None:
        if self.quality_error_manager:
            iface.removeDockWidget(self.quality_error_manager.dock_widget)

            self.quality_error_manager.unload()
            self.quality_error_manager = None

    def _on_open_dev_tools_called(self) -> None:
        dialog = DevToolsDialog(iface.mainWindow())
        if dialog.exec_():
            self._unload_quality_error_manager_if_exists()

            quality_errors_json = dialog.quality_errors_data_file_widget.filePath()
            api_client = MockQualityResultClient(Path(quality_errors_json))
            QgsProject.instance().setCrs(api_client.get_crs())

            self.quality_error_manager = QualityResultManager(
                api_client, iface.mainWindow()
            )
            self.quality_error_manager.closed.connect(
                self._unload_quality_error_manager_if_exists
            )

            iface.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea,
                self.quality_error_manager.dock_widget,
            )
            self.quality_error_manager.show_dock_widget()
