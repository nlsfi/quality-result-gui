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

from typing import Dict, Tuple, Union

from qgis.core import (
    QgsDrawSourceEffect,
    QgsEffectStack,
    QgsOuterGlowEffect,
    QgsProperty,
    QgsPropertyCollection,
    QgsSymbolLayer,
)
from qgis.PyQt.QtGui import QColor


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


def get_color(
    hex_or_rgb: Union[str, Tuple[int, int, int]], opacity: int = 100
) -> QColor:
    color = QColor(hex_or_rgb)
    color.setAlpha(int(opacity / 100 * 255))
    return color
