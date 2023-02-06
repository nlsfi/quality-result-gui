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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Union

from qgis.core import (
    QgsAnnotationLayer,
    QgsAnnotationLineItem,
    QgsAnnotationMarkerItem,
    QgsAnnotationPolygonItem,
    QgsGeometry,
    QgsLineString,
    QgsPoint,
    QgsPolygon,
    QgsProject,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor
from qgis_plugin_tools.tools.exceptions import QgsPluginException
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui import quality_layer_styles
from quality_result_gui.api.types.quality_error import QualityErrorPriority
from quality_result_gui.quality_layer_styles import ErrorSymbol

if TYPE_CHECKING:
    from quality_result_gui.quality_error_visualizer import ErrorFeature

LOGGER = logging.getLogger(__name__)


@dataclass
class QualityLayerColors:
    stroke_color: Union[QColor, str]
    secondary_color: Union[QColor, str]
    fill_color: Optional[Union[QColor, str]] = None


@dataclass
class QualityLayerStyle:
    colors_by_priority: Dict[QualityErrorPriority, QualityLayerColors]
    line_width: float
    polygon_border_width: float
    marker_border_width: float
    marker_size: float


COLORS_FOR_ERRORS = {
    QualityErrorPriority.FATAL: QualityLayerColors(
        stroke_color=quality_layer_styles.FATAL_PRIMARY_COLOR,
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.FATAL_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.WARNING: QualityLayerColors(
        stroke_color=quality_layer_styles.WARNING_PRIMARY_COLOR,
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.WARNING_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.INFO: QualityLayerColors(
        stroke_color=quality_layer_styles.INFO_PRIMARY_COLOR,
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.INFO_SECONDARY_COLOR, opacity=30
        ),
    ),
}


COLORS_FOR_HIGHLIGHTED_ERRORS = {
    QualityErrorPriority.FATAL: QualityLayerColors(
        stroke_color=quality_layer_styles.HIGHLIGHTED_FATAL_PRIMARY_COLOR,
        fill_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_FATAL_PRIMARY_COLOR, opacity=40
        ),
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_FATAL_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.WARNING: QualityLayerColors(
        stroke_color=quality_layer_styles.HIGHLIGHTED_WARNING_PRIMARY_COLOR,
        fill_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_WARNING_PRIMARY_COLOR, opacity=40
        ),
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_WARNING_SECONDARY_COLOR, opacity=30
        ),
    ),
    QualityErrorPriority.INFO: QualityLayerColors(
        stroke_color=quality_layer_styles.HIGHLIGHTED_INFO_PRIMARY_COLOR,
        fill_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_INFO_PRIMARY_COLOR, opacity=40
        ),
        secondary_color=quality_layer_styles.get_color(
            quality_layer_styles.HIGHLIGHTED_INFO_SECONDARY_COLOR, opacity=30
        ),
    ),
}


STYLE_FOR_ERRORS = QualityLayerStyle(
    COLORS_FOR_ERRORS,
    line_width=1.2,
    polygon_border_width=0.4,
    marker_border_width=0.4,
    marker_size=5,
)

STYLE_FOR_HIGHLIGHTED_ERRORS = QualityLayerStyle(
    COLORS_FOR_HIGHLIGHTED_ERRORS,
    line_width=1.6,
    polygon_border_width=0.8,
    marker_border_width=0.4,
    marker_size=5,
)


class LayerException(QgsPluginException):
    pass


class QualityErrorLayer:
    LAYER_ID = "quality-errors"
    LAYER_ID_PROPERTY = "quality-result-gui-layer"
    SYMBOL_MAP_SCALE = 10000

    def __init__(self) -> None:
        self._annotation_ids: Dict[str, List[str]] = {}

    @property
    def annotation_layer(self) -> QgsAnnotationLayer:
        return self.get_annotation_layer()

    def find_layer_from_project(self) -> Optional[QgsAnnotationLayer]:
        """
        Find QGIS layer using custom layer id which is automatically
        generated for the layer.
        """
        layers = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsAnnotationLayer)
            and layer.customProperty(self.LAYER_ID_PROPERTY) == self.LAYER_ID
        ]
        if len(layers) > 1:
            LOGGER.warning(
                f"Found multiple ({len(layers)}) layers with the same identifying "
                f"internal id {self.LAYER_ID}, should have found only one for the "
                "find logic to work on unique instances."
            )
        return layers[0] if len(layers) > 0 else None

    def _create_annotation_layer(self) -> QgsAnnotationLayer:
        layer = QgsAnnotationLayer(
            tr("Quality errors"),
            QgsAnnotationLayer.LayerOptions(QgsProject.instance().transformContext()),
        )

        layer.setCustomProperty(self.LAYER_ID_PROPERTY, self.LAYER_ID)

        LOGGER.debug(f"Created a layer: {layer.name()}")

        return layer

    def get_annotation_layer(self) -> QgsAnnotationLayer:
        """Creates an annotation layer from the layer configuration."""
        layer = self.find_layer_from_project()
        if layer is None:
            layer = self._create_annotation_layer()

        return layer

    def add_or_replace_annotation(
        self,
        error_feature: "ErrorFeature",
        use_highlighted_style: bool,
        id_prefix: str = "",
    ) -> None:
        annotation_layer = self.annotation_layer
        if error_feature.geometry.isNull():
            return

        annotations = self._create_annotations(
            error_feature.geometry,
            error_feature.priority,
            use_highlighted_style,
        )

        internal_id = f"{id_prefix}{error_feature.id}"

        # Update
        if internal_id in self._annotation_ids:
            # Singlepart geometries
            if len(annotations) == 1 and len(self._annotation_ids[internal_id]) == 1:
                annotation_layer.replaceItem(
                    self._annotation_ids[internal_id][0], annotations[0]
                )
            # Multipart geometries
            else:
                for annotation_id in self._annotation_ids[internal_id]:
                    annotation_layer.removeItem(annotation_id)
                new_ids = []
                for annotation in annotations:
                    new_ids.append(annotation_layer.addItem(annotation))
                self._annotation_ids[internal_id] = new_ids
        # New
        else:
            new_ids = []
            for annotation in annotations:
                new_ids.append(annotation_layer.addItem(annotation))
            self._annotation_ids[internal_id] = new_ids

    def remove_annotations(
        self, error_features: Iterable["ErrorFeature"], id_prefix: str = ""
    ) -> None:
        annotation_layer = self.annotation_layer

        for error_feature in error_features:
            internal_id = f"{id_prefix}{error_feature.id}"
            try:
                annotation_ids = self._annotation_ids.pop(internal_id)
                for annotation_id in annotation_ids:
                    annotation_layer.removeItem(annotation_id)
            except KeyError:
                # Consume exception, feature is not found
                pass

    def _create_annotations(
        self,
        geometry: QgsGeometry,
        priority: QualityErrorPriority,
        use_highlighted_style: bool,
    ) -> List[
        Union[QgsAnnotationMarkerItem, QgsAnnotationPolygonItem, QgsAnnotationLineItem]
    ]:
        annotations: List[
            Union[
                QgsAnnotationMarkerItem, QgsAnnotationPolygonItem, QgsAnnotationLineItem
            ]
        ] = []
        geom_type = geometry.type()

        original_abstract_geometry = geometry.get()
        cloned_original_abstract_geometry = original_abstract_geometry.clone()
        cloned_geom = QgsGeometry(cloned_original_abstract_geometry)

        style = STYLE_FOR_ERRORS
        if use_highlighted_style is True:
            style = STYLE_FOR_HIGHLIGHTED_ERRORS

        colors = style.colors_by_priority[priority]

        annotation = None
        symbol = ErrorSymbol(
            colors.stroke_color,
            colors.secondary_color,
            priority,
            symbol_map_scale=QualityErrorLayer.SYMBOL_MAP_SCALE,
        )

        if geom_type == QgsWkbTypes.PointGeometry:
            points = []
            if geometry.isMultipart() is False:
                point = QgsPoint()
                point.fromWkt(cloned_geom.asWkt())
                points.append(point)
            else:
                for part in cloned_geom.constParts():
                    point = QgsPoint()
                    point.fromWkt(part.asWkt())
                    points.append(point)

            for point in points:
                annotation = QgsAnnotationMarkerItem(point)
                symbol.line_or_border_width = style.marker_border_width
                symbol.marker_size = style.marker_size
                annotation.setSymbol(symbol._to_qgs_symbol(geom_type))
                annotations.append(annotation)

        elif geom_type == QgsWkbTypes.PolygonGeometry:
            polygons = []

            if geometry.isMultipart() is False:
                polygon = QgsPolygon()
                polygon.fromWkt(geometry.asWkt())
                polygons.append(polygon)
            else:
                for part in geometry.constParts():
                    polygon = QgsPolygon()
                    polygon.fromWkt(part.asWkt())
                    polygons.append(polygon)

            for polygon in polygons:
                annotation = QgsAnnotationPolygonItem(polygon)
                symbol.line_or_border_width = style.polygon_border_width
                symbol.fill_color = colors.fill_color
                annotation.setSymbol(symbol._to_qgs_symbol(geom_type))
                annotations.append(annotation)

        elif geom_type == QgsWkbTypes.LineGeometry:
            lines = []
            if geometry.isMultipart() is False:
                line = QgsLineString()
                line.fromWkt(cloned_geom.asWkt())
                lines.append(line)
            else:
                for part in cloned_geom.constParts():
                    line = QgsLineString()
                    line.fromWkt(part.asWkt())
                    lines.append(line)

            for line in lines:
                annotation = QgsAnnotationLineItem(line)

                modified_stroke_color = QColor(colors.stroke_color)
                modified_stroke_color.setAlpha(170)
                symbol.primary_color = modified_stroke_color
                symbol.line_or_border_width = style.line_width
                annotation.setSymbol(symbol._to_qgs_symbol(geom_type))
                annotations.append(annotation)

        else:
            raise ValueError(f"Unsupported geom type: {geom_type}")

        return annotations
