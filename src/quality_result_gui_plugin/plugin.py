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
from typing import Optional

import qgis_plugin_tools
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QTranslator
from qgis.PyQt.QtWidgets import QAction, QWidget
from qgis.utils import iface
from qgis_plugin_tools.tools.custom_logging import setup_loggers
from qgis_plugin_tools.tools.i18n import setup_translation, tr

import quality_result_gui
import quality_result_gui_plugin
from quality_result_gui_plugin.dev_tools.dev_tools_dialog import DevToolsDialog

LOGGER = logging.getLogger(__name__)


class QualityResultGuiPlugin(QWidget):
    def __init__(self) -> None:
        super().__init__(parent=None)

        self._teardown_loggers = lambda: None

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
            self.tr("Development tools"),
            iface.mainWindow(),
        )
        self.dev_tools_action.triggered.connect(self._on_open_dev_tools_called)

        iface.addPluginToMenu(self._menu_name, self.dev_tools_action)

    def unload(self) -> None:
        iface.removePluginMenu(self._menu_name, self.dev_tools_action)

        self._teardown_loggers()
        self._teardown_loggers = lambda: None

    def _on_open_dev_tools_called(self) -> None:
        if self.dev_tools_dialog is None:
            self.dev_tools_dialog = DevToolsDialog(iface.mainWindow())
        self.dev_tools_dialog.show()
