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

from typing import Optional

from qgis.PyQt.QtCore import QObject

from quality_result_gui.layer_mapping import LayerMapping


class QualityResultManagerSettings(QObject):
    """
    Singleton for storing common properties.
    """

    _instance: Optional["QualityResultManagerSettings"] = None
    layer_mapping: LayerMapping = LayerMapping(layer_map=None)

    @staticmethod
    def get() -> "QualityResultManagerSettings":
        if QualityResultManagerSettings._instance is None:
            QualityResultManagerSettings._instance = QualityResultManagerSettings()
        return QualityResultManagerSettings._instance

    def set_layer_mapping(self, layer_mapping: LayerMapping) -> None:
        self.layer_mapping = layer_mapping
