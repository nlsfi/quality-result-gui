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
from typing import Optional

from qgis.gui import QgsFileWidget
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QWidget

FORM_CLASS: QWidget
FORM_CLASS, _ = uic.loadUiType(
    str(Path(__file__).parent.joinpath("dev_tools_dialog.ui"))
)


LOGGER = logging.getLogger(__name__)


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
        self.btn_open_quality_errors_dialog.clicked.connect(self.accept)

    def _enable_open_quality_errors_dialog_button(self) -> None:
        self.btn_open_quality_errors_dialog.setEnabled(True)
