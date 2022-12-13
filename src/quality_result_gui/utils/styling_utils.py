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

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Union

from qgis.core import (
    QgsDrawSourceEffect,
    QgsEffectStack,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsOuterGlowEffect,
    QgsProperty,
    QgsPropertyCollection,
    QgsSymbol,
    QgsSymbolLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor


class BaseSymbol(ABC):
    @abstractmethod
    def _to_qgs_symbol(self, geometry_type: QgsWkbTypes.GeometryType) -> QgsSymbol:
        """
        Implement logic to generate the relevant symbol for the given geometry type.
        """
        raise NotImplementedError()

    @staticmethod
    def color_to_rgba_string(color: Union[str, QColor]) -> str:
        return ",".join(map(str, QColor(color).getRgb()))


class BaseSymbolByType(BaseSymbol, ABC):
    def _to_qgs_symbol(self, geometry_type: QgsWkbTypes.GeometryType) -> QgsSymbol:
        if geometry_type == QgsWkbTypes.PolygonGeometry:
            return self.get_polygon_symbol()
        if geometry_type == QgsWkbTypes.LineGeometry:
            return self.get_line_symbol()
        if geometry_type == QgsWkbTypes.PointGeometry:
            return self.get_point_symbol()
        raise NotImplementedError()

    @abstractmethod
    def get_polygon_symbol(self) -> QgsFillSymbol:
        raise NotImplementedError()

    @abstractmethod
    def get_line_symbol(self) -> QgsLineSymbol:
        raise NotImplementedError()

    @abstractmethod
    def get_point_symbol(self) -> QgsMarkerSymbol:
        raise NotImplementedError()


def set_symbol_layer_data_defined_property_expressions(
    symbol_layer: QgsSymbolLayer, data_defined_property_expressions: Dict[str, str]
) -> None:
    """
    Sets the symbol layer data defined properties with expressions.

    Will silently ignore if the property name is not found on the symbol layer.
    """
    data_defined_properties = QgsPropertyCollection()

    property_name_to_number_mapping = {
        definition.name(): number
        for number, definition in symbol_layer.propertyDefinitions().items()
    }

    for property_name, property_expression in data_defined_property_expressions.items():
        property = QgsProperty.fromExpression(property_expression)
        if (
            property_number := property_name_to_number_mapping.get(property_name)
        ) is not None:
            data_defined_properties.setProperty(property_number, property)

    symbol_layer.setDataDefinedProperties(data_defined_properties)


def set_symbol_layer_simple_outer_glow_effect(
    symbol_layer: QgsSymbolLayer,
    color_rgba: str,
    spread: Tuple[float, str] = (2.0, "MM"),
    blur: Tuple[float, str] = (2.0, "MM"),
    opacity: float = 1,
) -> None:
    """
    Sets an outer glow effect on a symbol layer.
    """
    spread_amount, spread_unit = spread
    blur_amount, blur_unit = blur

    source_effect_layer = QgsDrawSourceEffect.create({"enabled": "1"})
    glow_effect_layer = QgsOuterGlowEffect.create(
        {
            "enabled": "1",
            "single_color": color_rgba,
            "spread": str(spread_amount),
            "spread_unit": spread_unit,
            "blur_level": str(blur_amount),
            "blur_unit": blur_unit,
            "opacity": str(opacity),
        }
    )

    paint_effect_stack = QgsEffectStack()
    paint_effect_stack.appendEffect(source_effect_layer)
    paint_effect_stack.appendEffect(glow_effect_layer)

    symbol_layer.setPaintEffect(paint_effect_stack)
