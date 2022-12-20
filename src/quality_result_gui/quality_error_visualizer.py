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
from typing import List, Optional

from qgis.core import (
    QgsAnnotationLayer,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsProject,
)

from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorPriority,
)
from quality_result_gui.quality_layer import QualityErrorLayer
from quality_result_gui.utils import layer_utils

LOGGER = logging.getLogger(__name__)


@dataclass
class ErrorFeature:
    id: str
    priority: QualityErrorPriority
    geometry: QgsGeometry
    crs: QgsCoordinateReferenceSystem

    @staticmethod
    def from_quality_error(
        quality_error: QualityError, crs: QgsCoordinateReferenceSystem
    ) -> "ErrorFeature":
        return ErrorFeature(
            quality_error.unique_identifier,
            quality_error.priority,
            quality_error.geometry,
            crs,
        )


class QualityErrorVisualizer:
    """
    Class for visualizing quality errors on map canvas.
    """

    ID_PREFIX_FOR_SELECTED = "selected-"

    def __init__(self) -> None:
        self.errors_visible = True

        self._all_error_features: List[ErrorFeature] = []
        self._selected_error_feature: Optional[ErrorFeature] = None

        self._quality_error_layer = QualityErrorLayer()

    def toggle_visibility(self, show_errors: bool) -> None:
        if show_errors is True:
            self.show_errors()
        else:
            self.hide_errors()

    def add_new_errors(self, error_features: List[ErrorFeature]) -> None:
        for error_feature in error_features:
            self._quality_error_layer.add_or_replace_annotation(
                error_feature, use_highlighted_style=False
            )

    def remove_errors(self, error_features: List[ErrorFeature]) -> None:
        self._quality_error_layer.remove_annotations(error_features)

    def refresh_selected_error(
        self,
        selected_error_feature: ErrorFeature,
    ) -> None:
        self._remove_selected_error()
        self._selected_error_feature = selected_error_feature

        self._quality_error_layer.add_or_replace_annotation(
            selected_error_feature,
            use_highlighted_style=True,
            id_prefix=self.ID_PREFIX_FOR_SELECTED,
        )

    def show_errors(self) -> None:
        layer = self._get_or_create_layer()
        layer_utils.set_visibility_checked(layer, True)
        self.errors_visible = True

    def hide_errors(self) -> None:
        layer = self._get_or_create_layer()
        layer_utils.set_visibility_checked(layer, False)
        self.errors_visible = False

    def remove_quality_error_layer(self) -> None:
        layer = self._quality_error_layer.find_layer_from_project()

        if layer is not None:
            QgsProject.instance().removeMapLayer(layer.id())

    def zoom_to_geometries_and_flash(
        self, error_features: List[ErrorFeature], preserve_scale: bool = False
    ) -> None:
        if len(error_features) > 0:
            layer_utils.zoom_to_geometries_and_flash(
                [feature.geometry for feature in error_features],
                error_features[0].crs,  # Use crs from first feature
                preserve_scale,
                min_extent_height=20,
            )

    def _get_or_create_layer(self) -> QgsAnnotationLayer:
        layer = self._quality_error_layer.find_layer_from_project()

        if layer is None:
            layer = self._quality_error_layer.get_annotation_layer()
            QgsProject.instance().addMapLayer(layer, False)
            QgsProject.instance().layerTreeRoot().insertLayer(0, layer)

        return layer

    def _remove_selected_error(self) -> None:
        if self._selected_error_feature is not None:
            self._quality_error_layer.remove_annotations(
                [self._selected_error_feature], id_prefix=self.ID_PREFIX_FOR_SELECTED
            )
            self._selected_error_feature = None
