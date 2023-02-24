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
from importlib.resources import as_file, files
from typing import List, Optional, Union

from qgis.core import (
    QgsCentroidFillSymbolLayer,
    QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
)
from qgis.PyQt.QtGui import QColor

from quality_result_gui import resources
from quality_result_gui.api.types.quality_error import QualityErrorPriority
from quality_result_gui.style.quality_layer_error_symbol import ErrorSymbol
from quality_result_gui.utils import styling_utils
from quality_result_gui.utils.styling_utils import (
    set_symbol_layer_data_defined_property_expressions,
    set_symbol_layer_simple_outer_glow_effect,
)

# Colors for error features
FATAL_PRIMARY_COLOR = "#C31266"
FATAL_SECONDARY_COLOR = "#F24726"
WARNING_PRIMARY_COLOR = "#E65A13"
WARNING_SECONDARY_COLOR = "#FF8303"
INFO_PRIMARY_COLOR = "#EAA613"
INFO_SECONDARY_COLOR = "#FFFF00"

# Colors for selected error features
HIGHLIGHTED_FATAL_PRIMARY_COLOR = "#D90368"
HIGHLIGHTED_FATAL_SECONDARY_COLOR = "#F24726"
HIGHLIGHTED_WARNING_PRIMARY_COLOR = "#FB6107"
HIGHLIGHTED_WARNING_SECONDARY_COLOR = "#FF8303"
HIGHLIGHTED_INFO_PRIMARY_COLOR = "#FBD00E"
HIGHLIGHTED_INFO_SECONDARY_COLOR = "#FFFF00"


@dataclass
class QualityLayerColors:
    stroke_color: Union[QColor, str]
    secondary_color: Union[QColor, str]
    fill_color: Optional[Union[QColor, str]] = None


@dataclass
class QualityLayerStyle:
    colors_by_priority: dict[QualityErrorPriority, QualityLayerColors]
    line_width: float
    polygon_border_width: float
    marker_border_width: float
    marker_size: float


COLORS_FOR_ERRORS = {
    QualityErrorPriority.FATAL: QualityLayerColors(
        stroke_color=FATAL_PRIMARY_COLOR,
        secondary_color=styling_utils.get_color(FATAL_SECONDARY_COLOR, opacity=30),
    ),
    QualityErrorPriority.WARNING: QualityLayerColors(
        stroke_color=WARNING_PRIMARY_COLOR,
        secondary_color=styling_utils.get_color(WARNING_SECONDARY_COLOR, opacity=30),
    ),
    QualityErrorPriority.INFO: QualityLayerColors(
        stroke_color=INFO_PRIMARY_COLOR,
        secondary_color=styling_utils.get_color(INFO_SECONDARY_COLOR, opacity=30),
    ),
}


COLORS_FOR_HIGHLIGHTED_ERRORS = {
    QualityErrorPriority.FATAL: QualityLayerColors(
        stroke_color=HIGHLIGHTED_FATAL_PRIMARY_COLOR,
        fill_color=styling_utils.get_color(HIGHLIGHTED_FATAL_PRIMARY_COLOR, opacity=40),
        secondary_color=styling_utils.get_color(
            HIGHLIGHTED_FATAL_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.WARNING: QualityLayerColors(
        stroke_color=HIGHLIGHTED_WARNING_PRIMARY_COLOR,
        fill_color=styling_utils.get_color(
            HIGHLIGHTED_WARNING_PRIMARY_COLOR, opacity=40
        ),
        secondary_color=styling_utils.get_color(
            HIGHLIGHTED_WARNING_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.INFO: QualityLayerColors(
        stroke_color=HIGHLIGHTED_INFO_PRIMARY_COLOR,
        fill_color=styling_utils.get_color(HIGHLIGHTED_INFO_PRIMARY_COLOR, opacity=40),
        secondary_color=styling_utils.get_color(
            HIGHLIGHTED_INFO_SECONDARY_COLOR, opacity=30
        ),
    ),
}


class DefaultErrorSymbol(ErrorSymbol):
    SYMBOL_MAP_SCALE = 10000

    def __init__(
        self,
        priority: QualityErrorPriority,
    ) -> None:

        self.style: QualityLayerStyle = QualityLayerStyle(
            COLORS_FOR_ERRORS,
            line_width=1.2,
            polygon_border_width=0.4,
            marker_border_width=0.4,
            marker_size=5,
        )
        self.style_for_highlighted_error = QualityLayerStyle(
            COLORS_FOR_HIGHLIGHTED_ERRORS,
            line_width=1.6,
            polygon_border_width=0.8,
            marker_border_width=0.4,
            marker_size=5,
        )

        self.current_style = self.style

        self.priority = priority

        self.icon_symbol_enabled_expression = f"@map_scale > {self.SYMBOL_MAP_SCALE}"
        self.geometry_symbol_enabled_expression = (
            f"@map_scale <= {self.SYMBOL_MAP_SCALE}"
        )

    def _get_polygon_symbol(self, highlighted: bool) -> QgsFillSymbol:
        style = self.style
        if highlighted:
            style = self.style_for_highlighted_error

        colors = style.colors_by_priority[self.priority]

        fill_color = QColor(0, 0, 0, 0)
        if colors.fill_color is not None:
            fill_color = QColor(colors.fill_color)

        symbol = QgsFillSymbol()
        fill_symbol_layer = QgsSimpleFillSymbolLayer.create(
            {
                "color": self.color_to_rgba_string(fill_color),
                "outline_style": "no",
            }
        )
        symbol.changeSymbolLayer(0, fill_symbol_layer)

        primary_border_symbol_layer = QgsSimpleLineSymbolLayer.create(
            {
                "line_color": self.color_to_rgba_string(colors.stroke_color),
                "line_width": str(style.polygon_border_width),
                "line_width_unit": "MM",
            }
        )
        symbol.appendSymbolLayer(primary_border_symbol_layer)

        secondary_border_symbol_layer = QgsSimpleLineSymbolLayer.create(
            {
                "line_color": self.color_to_rgba_string(colors.secondary_color),
                "line_width": "3.4",
                "line_width_unit": "MM",
                "joinstyle": "round",
            }
        )
        symbol.appendSymbolLayer(secondary_border_symbol_layer)

        priority_symbol_layer = self._create_priority_symbol_layer(self.priority)
        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, priority_symbol_layer)

        centroid_layer = QgsCentroidFillSymbolLayer.create({})
        centroid_layer.setSubSymbol(marker_symbol)

        symbol.appendSymbolLayer(centroid_layer)

        self._set_enabled_expression(
            centroid_layer,
            [
                fill_symbol_layer,
                primary_border_symbol_layer,
                secondary_border_symbol_layer,
            ],
        )

        return symbol

    def _get_line_symbol(self, highlighted: bool) -> QgsLineSymbol:
        style = self.style
        if highlighted:
            style = self.style_for_highlighted_error

        colors = style.colors_by_priority[self.priority]
        modified_stroke_color = QColor(colors.stroke_color)
        modified_stroke_color.setAlpha(170)

        line_symbol = QgsLineSymbol()

        primary_border_symbol_layer = QgsSimpleLineSymbolLayer.create(
            {
                "line_color": self.color_to_rgba_string(modified_stroke_color),
                "line_width": str(style.line_width),
                "line_width_unit": "MM",
            }
        )
        line_symbol.changeSymbolLayer(0, primary_border_symbol_layer)

        secondary_border_symbol_layer = QgsSimpleLineSymbolLayer.create(
            {
                "line_color": self.color_to_rgba_string(colors.secondary_color),
                "line_width": "3.4",
                "line_width_unit": "MM",
                "joinstyle": "round",
            }
        )
        line_symbol.appendSymbolLayer(secondary_border_symbol_layer)

        priority_symbol_layer = self._create_priority_symbol_layer(self.priority)
        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, priority_symbol_layer)

        generator_layer = QgsGeometryGeneratorSymbolLayer.create({})
        generator_layer.setGeometryExpression(
            "line_interpolate_point( $geometry, length3D($geometry) / 2)"
        )
        generator_layer.setSubSymbol(marker_symbol)

        if not line_symbol.appendSymbolLayer(generator_layer):
            raise ValueError("invalid line symbol priority_symbol_layer")
        self._set_enabled_expression(
            generator_layer,
            [secondary_border_symbol_layer, primary_border_symbol_layer],
        )

        return line_symbol

    def _get_point_symbol(self, highlighted: bool) -> QgsMarkerSymbol:
        style = self.style
        if highlighted:
            style = self.style_for_highlighted_error

        colors = style.colors_by_priority[self.priority]

        fill_symbol_layer = QgsSimpleMarkerSymbolLayer.create(
            {
                "size": str(style.marker_size),
                "size_unit": "MM",
                "color": self.color_to_rgba_string(QColor(0, 0, 0, 0)),
                "line_color": self.color_to_rgba_string(colors.stroke_color),
                "line_width": str(style.marker_border_width),
                "line_width_unit": "MM",
            }
        )
        modified_color = QColor(colors.secondary_color)
        modified_color.setAlphaF(0.7)
        set_symbol_layer_simple_outer_glow_effect(
            fill_symbol_layer, self.color_to_rgba_string(modified_color)
        )

        symbol = QgsMarkerSymbol()
        symbol.changeSymbolLayer(0, fill_symbol_layer)

        priority_symbol_layer = self._create_priority_symbol_layer(self.priority)
        symbol.appendSymbolLayer(priority_symbol_layer)
        self._set_enabled_expression(priority_symbol_layer, [fill_symbol_layer])

        return symbol

    def _set_enabled_expression(
        self,
        priority_symbol_layer: QgsSymbolLayer,
        geometry_layers: List[QgsSymbolLayer],
    ) -> None:
        if (
            self.icon_symbol_enabled_expression is not None
            and self.geometry_symbol_enabled_expression is not None
        ):
            set_symbol_layer_data_defined_property_expressions(
                priority_symbol_layer,
                {"enabled": self.icon_symbol_enabled_expression},
            )
            for layer in geometry_layers:
                set_symbol_layer_data_defined_property_expressions(
                    layer,
                    {"enabled": self.geometry_symbol_enabled_expression},
                )

    def _create_priority_symbol_layer(
        self, priority: QualityErrorPriority
    ) -> QgsSvgMarkerSymbolLayer:

        file_path = files(resources).joinpath("icons")

        if priority == QualityErrorPriority.FATAL:
            file_path = file_path.joinpath("quality_error_fatal.svg")
        elif priority == QualityErrorPriority.WARNING:
            file_path = file_path.joinpath("quality_error_warning.svg")
        elif priority == QualityErrorPriority.INFO:
            file_path = file_path.joinpath("quality_error_info.svg")
        else:
            raise ValueError(f"Unknown priority {str(priority)}")

        style = dict({})
        with as_file(file_path) as svg_file:
            style["name"] = str(svg_file)

        return QgsSvgMarkerSymbolLayer.create(style)
