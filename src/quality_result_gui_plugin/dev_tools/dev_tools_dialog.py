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

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qgis.core import QgsCoordinateReferenceSystem, QgsProject
from qgis.gui import QgsFileWidget
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QWidget
from qgis.utils import iface
from qgis_plugin_tools.tools.decorations import log_if_fails

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import QualityErrorsByPriority
from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget
from quality_result_gui_plugin.dev_tools.response_parser import QualityErrorResponse

FORM_CLASS: QWidget
FORM_CLASS, _ = uic.loadUiType(
    str(Path(__file__).parent.joinpath("dev_tools_dialog.ui"))
)

LOGGER = logging.getLogger(__name__)


@dataclass
class MockQualityResultClient(QualityResultClient):
    json_file_path: Path

    def get_results(self) -> Optional[List[QualityErrorsByPriority]]:
        """
        Retrieve latest quality errors from API

        Returns:
            None: if no results available
            List[QualityErrorsByPriority]: if results available

        Raises:
            QualityResultClientError: if request fails
            QualityResultServerError: if check failed in backend
        """
        return QualityErrorResponse(
            json.loads(self.json_file_path.read_text())
        ).errors_by_priority

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem("EPSG:3067")


class DevToolsDialog(QDialog, FORM_CLASS):

    quality_errors_data_file_widget: QgsFileWidget
    btn_open_quality_errors_dialog: QPushButton

    button_box: QDialogButtonBox

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setupUi(self)

        # Setup for quality errors dialog:
        self.quality_errors_data_file_widget.setDefaultRoot(
            str((Path(__file__).parent / "example_quality_errors").resolve())
        )
        self.quality_errors_data_file_widget.setFilter("*.json")
        self.quality_errors_data_file_widget.fileChanged.connect(
            self._enable_open_quality_errors_dialog_button
        )
        self.btn_open_quality_errors_dialog.setEnabled(False)
        self.btn_open_quality_errors_dialog.clicked.connect(
            self._load_quality_errors_data
        )

    def _enable_open_quality_errors_dialog_button(self) -> None:
        self.btn_open_quality_errors_dialog.setEnabled(True)

    @log_if_fails
    def _load_quality_errors_data(self) -> None:
        quality_errors_json = self.quality_errors_data_file_widget.filePath()
        api_client = MockQualityResultClient(Path(quality_errors_json))
        QgsProject.instance().setCrs(api_client.get_crs())

        quality_errors_dialog = QualityErrorsDockWidget(api_client, iface.mainWindow())
        quality_errors_dialog.show()
        iface.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, quality_errors_dialog
        )
