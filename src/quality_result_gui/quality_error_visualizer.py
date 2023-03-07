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
from typing import Iterable, List, Optional

from qgis.core import QgsAnnotationLayer, QgsCoordinateReferenceSystem, QgsProject

from quality_result_gui.api.types.quality_error import QualityError
from quality_result_gui.configuration import QualityLayerStyleConfig
from quality_result_gui.quality_layer import QualityErrorLayer
from quality_result_gui.ui.quality_error_tree_view import SelectionType
from quality_result_gui.utils import layer_utils

LOGGER = logging.getLogger(__name__)


class QualityErrorVisualizer:
    """
    Class for visualizing quality errors on map canvas.
    """

    ID_PREFIX_FOR_SELECTED = "selected-"
    style_config: Optional["QualityLayerStyleConfig"] = None

    def __init__(
        self,
        crs: QgsCoordinateReferenceSystem,
        style_config: Optional["QualityLayerStyleConfig"] = None,
    ) -> None:
        self._crs = crs
        self._selected_quality_error: Optional[QualityError] = None
        self.style_config = style_config

        self._quality_error_layer = QualityErrorLayer()

    def toggle_visibility(self, show_errors: bool) -> None:
        if show_errors is True:
            self.show_errors()
        else:
            self.hide_errors()

    def add_new_errors(self, quality_errors: Iterable[QualityError]) -> None:
        for quality_error in quality_errors:
            self._quality_error_layer.add_or_replace_annotation(
                quality_error, use_highlighted_style=False
            )

    def remove_errors(self, quality_errors: Iterable[QualityError]) -> None:
        errors = list(quality_errors)
        self._quality_error_layer.remove_annotations(errors)

        if (
            self._selected_quality_error
            and self._selected_quality_error.unique_identifier
            in [error.unique_identifier for error in errors]
        ):
            self._remove_selected_error()
            self._selected_quality_error = None

    def on_error_selected(
        self, quality_error: QualityError, selection_type: SelectionType
    ) -> None:
        preserve_scale = selection_type == SelectionType.RightClick

        self.zoom_to_geometries_and_flash(
            [quality_error], preserve_scale=preserve_scale
        )

        self.refresh_selected_error(quality_error)

    def refresh_selected_error(
        self,
        selected_quality_error: QualityError,
    ) -> None:
        self._remove_selected_error()
        self._selected_quality_error = selected_quality_error

        self._quality_error_layer.add_or_replace_annotation(
            selected_quality_error,
            use_highlighted_style=True,
            id_prefix=self.ID_PREFIX_FOR_SELECTED,
        )

    def show_errors(self) -> None:
        layer = self._get_or_create_layer()
        self.override_quality_layer_style()
        layer_utils.set_visibility_checked(layer, True)

    def hide_errors(self) -> None:
        layer = self._get_or_create_layer()
        layer_utils.set_visibility_checked(layer, False)

    def initialize_quality_error_layer(self, visible: bool = True) -> None:
        self.remove_quality_error_layer()
        layer = self._get_or_create_layer()
        layer_utils.set_visibility_checked(layer, visible)

    def remove_quality_error_layer(self) -> None:
        layer = self._quality_error_layer.find_layer_from_project()

        if layer is not None:
            QgsProject.instance().removeMapLayer(layer.id())

    def zoom_to_geometries_and_flash(
        self, quality_errors: List[QualityError], preserve_scale: bool = False
    ) -> None:
        if len(quality_errors) > 0:
            layer_utils.zoom_to_geometries_and_flash(
                [error.geometry for error in quality_errors],
                self._crs,
                preserve_scale,
                min_extent_height=20,
            )

    def override_quality_layer_style(self) -> None:
        if self.style_config:
            self._quality_error_layer.override_style(self.style_config)

    def _get_or_create_layer(self) -> QgsAnnotationLayer:
        layer = self._quality_error_layer.find_layer_from_project()

        if layer is None:
            layer = self._quality_error_layer.get_annotation_layer()
            QgsProject.instance().addMapLayer(layer, False)
            QgsProject.instance().layerTreeRoot().insertLayer(0, layer)

        return layer

    def _remove_selected_error(self) -> None:
        if self._selected_quality_error is not None:
            self._quality_error_layer.remove_annotations(
                [self._selected_quality_error], id_prefix=self.ID_PREFIX_FOR_SELECTED
            )
            self._selected_quality_error = None
