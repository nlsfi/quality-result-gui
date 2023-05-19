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

from dataclasses import dataclass
from typing import Dict, Optional

from qgis.core import QgsField, QgsProject, QgsVectorLayer


@dataclass
class LayerMapping:
    layer_map: Optional[Dict[str, str]]

    def get_layer_alias(self, feature_type: str) -> str:
        layer = self._get_layer(feature_type)
        if layer is None:
            return feature_type
        return layer.name()

    def get_field_alias(self, feature_type: str, field_name: str) -> str:
        def predicate(field: QgsField) -> bool:
            return field.name() == field_name

        layer = self._get_layer(feature_type)
        if layer is None:
            return field_name
        attribute = next(filter(predicate, layer.fields()), None)
        if attribute is None:
            return field_name
        return attribute.displayName()

    def _get_layer(self, feature_type: str) -> Optional[QgsVectorLayer]:
        if not self.layer_map:
            return None
        layer_id = self.layer_map.get(feature_type)
        if not layer_id:
            return None
        return next(
            (
                layer
                for layer in QgsProject.instance().mapLayers().values()
                if layer.id() == layer_id
            ),
            None,
        )
