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

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional, Union

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
from qgis_plugin_tools.tools.exceptions import QgsPluginException
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.configuration import QualityLayerStyleConfig
from quality_result_gui.style.default_style import DefaultErrorSymbol

if TYPE_CHECKING:
    from quality_result_gui.api.types.quality_error import QualityError
    from quality_result_gui.style.quality_layer_error_symbol import ErrorSymbol

LOGGER = logging.getLogger(__name__)


class LayerException(QgsPluginException):
    pass


class DefaultStyleConfig(QualityLayerStyleConfig):
    def create_error_symbol(self, quality_error: "QualityError") -> "ErrorSymbol":
        return DefaultErrorSymbol(quality_error)


class QualityErrorLayer:
    LAYER_ID = "quality-errors"
    LAYER_ID_PROPERTY = "quality-result-gui-layer"

    def __init__(self) -> None:
        self._annotation_ids: dict[str, list[str]] = {}
        self.style: "QualityLayerStyleConfig" = DefaultStyleConfig()

    @property
    def annotation_layer(self) -> QgsAnnotationLayer:
        return self.get_annotation_layer()

    def override_style(
        self,
        style: "QualityLayerStyleConfig",
    ) -> None:
        self.style = style

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
        quality_error: "QualityError",
        use_highlighted_style: bool,
        id_prefix: str = "",
    ) -> None:
        annotation_layer = self.annotation_layer
        if quality_error.geometry.isNull():
            return

        annotations = self._create_annotations(
            quality_error,
            use_highlighted_style,
        )

        internal_id = f"{id_prefix}{quality_error.unique_identifier}"

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
        self, quality_errors: Iterable["QualityError"], id_prefix: str = ""
    ) -> None:
        annotation_layer = self.annotation_layer

        for quality_error in quality_errors:
            internal_id = f"{id_prefix}{quality_error.unique_identifier}"
            try:
                annotation_ids = self._annotation_ids.pop(internal_id)
                for annotation_id in annotation_ids:
                    annotation_layer.removeItem(annotation_id)
            except KeyError:
                # Consume exception, feature is not found
                pass

    def _create_annotations(  # noqa: C901, PLR0912
        self,
        quality_error: "QualityError",
        use_highlighted_style: bool,
    ) -> list[
        Union[QgsAnnotationMarkerItem, QgsAnnotationPolygonItem, QgsAnnotationLineItem]
    ]:
        annotations: list[
            Union[
                QgsAnnotationMarkerItem, QgsAnnotationPolygonItem, QgsAnnotationLineItem
            ]
        ] = []
        geometry = quality_error.geometry
        geom_type = geometry.type()

        original_abstract_geometry = geometry.get()
        cloned_original_abstract_geometry = original_abstract_geometry.clone()
        cloned_geom = QgsGeometry(cloned_original_abstract_geometry)

        annotation = None

        symbol = self.style.create_error_symbol(quality_error)

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
                annotation.setSymbol(
                    symbol.to_qgs_symbol(geom_type, use_highlighted_style)
                )
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
                annotation.setSymbol(
                    symbol.to_qgs_symbol(geom_type, use_highlighted_style)
                )
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
                annotation.setSymbol(
                    symbol.to_qgs_symbol(geom_type, use_highlighted_style)
                )
                annotations.append(annotation)

        else:
            raise ValueError(f"Unsupported geom type: {geom_type}")

        for annotation in annotations:
            # Set z-index based on the priority
            annotation.setZIndex(-quality_error.priority.value)

        return annotations
