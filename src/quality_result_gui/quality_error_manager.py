#  Copyright (C) 2023-2024 National Land Survey of Finland
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


from typing import TYPE_CHECKING, Optional, cast

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui import SelectionType
from quality_result_gui.api.types.quality_error import QualityError
from quality_result_gui.layer_mapping import LayerMapping
from quality_result_gui.quality_data_fetcher import (
    CHECK_STATUS_LABELS,
    BackgroundQualityResultsFetcher,
    CheckStatus,
)
from quality_result_gui.quality_error_manager_settings import (
    QualityResultManagerSettings,
)
from quality_result_gui.quality_error_visualizer import QualityErrorVisualizer
from quality_result_gui.quality_errors_filters import (
    AbstractQualityErrorFilter,
    AttributeFilter,
    ErrorTypeFilter,
    FeatureTypeFilter,
)
from quality_result_gui.quality_errors_tree_model import (
    FilterByExtentProxyModel,
    FilterByShowUserProcessedProxyModel,
    FilterProxyModel,
    QualityErrorsTreeBaseModel,
    StyleProxyModel,
)
from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget

if TYPE_CHECKING:
    from quality_result_gui.api.quality_api_client import QualityResultClient
    from quality_result_gui.configuration import QualityLayerStyleConfig

iface = cast(QgisInterface, utils_iface)


class QualityResultManager(QObject):
    closed = pyqtSignal()
    error_checked = pyqtSignal(str, bool)
    quality_error_selected = pyqtSignal(QualityError, SelectionType)

    def __init__(
        self,
        api_client: "QualityResultClient",
        parent: Optional[QObject] = None,
        style_config: Optional["QualityLayerStyleConfig"] = None,
    ) -> None:
        super().__init__(parent=parent)

        self._api_client = api_client

        self.visualizer = QualityErrorVisualizer(
            self._api_client.get_crs(), style_config
        )
        self.visualizer.show_errors()

        self.dock_widget = QualityErrorsDockWidget(iface.mainWindow())
        self.dock_widget.closed.connect(self.closed)

        self.dock_widget.error_tree_view.errors_inserted.connect(
            lambda errors: self.visualizer.add_new_errors(errors)
        )
        self.dock_widget.error_tree_view.errors_removed.connect(
            lambda errors: self.visualizer.remove_errors(errors)
        )

        self._fetcher = BackgroundQualityResultsFetcher(self._api_client, self)
        self._fetcher.status_changed.connect(self._update_info_label)

        self._base_model = QualityErrorsTreeBaseModel()
        self._base_model.error_checked.connect(self.error_checked)

        self._fetcher.results_received.connect(self._base_model.refresh_model)

        self._filter_model = FilterProxyModel()
        self._filter_model.setSourceModel(self._base_model)

        self._base_model.filterable_data_changed.connect(
            self._filter_model.invalidateFilter
        )

        # Checkbox for filtering out user processed rows
        self._filter_user_processed_model = FilterByShowUserProcessedProxyModel()
        self._filter_user_processed_model.setSourceModel(self._filter_model)
        self._filter_model.filter_invalidated.connect(
            self._filter_user_processed_model.invalidateFilter
        )
        self.dock_widget.show_user_processed_errors_check_box.toggled.connect(
            self._filter_user_processed_model.set_show_processed_errors
        )

        # Checkbox for filtering out rows outside map extent
        self._filter_map_extent_model = FilterByExtentProxyModel()
        self._filter_map_extent_model.setSourceModel(self._filter_user_processed_model)
        self._filter_user_processed_model.filter_invalidated.connect(
            self._filter_map_extent_model.invalidateFilter
        )
        self.dock_widget.filter_with_map_extent_check_box.toggled.connect(
            self._filter_map_extent_model.set_enabled
        )

        # Invalidate map extent filter also when user processed checkbox is toggled
        self.dock_widget.show_user_processed_errors_check_box.toggled.connect(
            self._filter_map_extent_model.invalidateFilter
        )

        self._styled_model = StyleProxyModel()
        self._styled_model.setSourceModel(self._filter_map_extent_model)

        self.dock_widget.error_tree_view.setModel(self._styled_model)

        # Checkbox for showing errors on map
        self.dock_widget.show_errors_on_map_check_box.toggled.connect(
            self.visualizer.toggle_visibility
        )

        self.dock_widget.error_tree_view.quality_error_selected.connect(
            self.quality_error_selected
        )
        self.dock_widget.error_tree_view.quality_error_selected.connect(
            self.visualizer.on_error_selected
        )

        self._add_predefined_filters()

    def _add_predefined_filters(self) -> None:
        self._error_type_filter = ErrorTypeFilter()
        self.add_filter(self._error_type_filter)

        self._feature_type_filter = FeatureTypeFilter()
        self.add_filter(self._feature_type_filter)
        self._fetcher.results_received.connect(
            self._feature_type_filter.update_filter_from_errors
        )

        self._attribute_filter = AttributeFilter()
        self.add_filter(self._attribute_filter)
        self._fetcher.results_received.connect(
            self._attribute_filter.update_filter_from_errors
        )

    def unload(self) -> None:
        self._fetcher.stop()
        self._filter_map_extent_model.set_enabled(False)
        self.dock_widget.close()
        self.dock_widget.deleteLater()
        self.visualizer.remove_quality_error_layer()

    def _update_info_label(self, status: CheckStatus) -> None:
        try:
            status_text = CHECK_STATUS_LABELS[status]()
        except ValueError:
            status_text = tr("Status of fetching quality result unknown")
        self.dock_widget.info_label.setText(status_text)

    def show_dock_widget(self) -> None:
        self._fetcher.start()
        self.dock_widget.show()
        self.visualizer.initialize_quality_error_layer(
            self.dock_widget.show_errors_on_map_check_box.isChecked()
        )
        self.visualizer.add_new_errors(
            self.dock_widget.error_tree_view.get_all_quality_errors()
        )

    def hide_dock_widget(self) -> None:
        self._fetcher.stop()
        self.dock_widget.hide()
        self.visualizer.remove_quality_error_layer()

    def add_filter(self, filter: AbstractQualityErrorFilter) -> None:
        filter.filters_changed.connect(self.dock_widget._update_filter_menu_icon_state)
        self.dock_widget.filter_menu.add_filter_menu(filter.menu)
        self._filter_model.add_filter(filter)

    def set_layer_mapping(self, layer_mapping: dict[str, str]) -> None:
        QualityResultManagerSettings.get().set_layer_mapping(
            LayerMapping(layer_map=layer_mapping)
        )
