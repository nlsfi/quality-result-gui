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


from typing import TYPE_CHECKING, Generator, List, Optional, cast

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui import SelectionType
from quality_result_gui.api.types.quality_error import QualityError
from quality_result_gui.quality_data_fetcher import (
    CHECK_STATUS_LABELS,
    BackgroundQualityResultsFetcher,
    CheckStatus,
)
from quality_result_gui.quality_error_visualizer import (
    ErrorFeature,
    QualityErrorVisualizer,
)
from quality_result_gui.quality_errors_filters import (
    AbstractQualityErrorFilter,
    AttributeFilter,
    ErrorTypeFilter,
    FeatureTypeFilter,
    UserProcessedFilter,
)
from quality_result_gui.quality_errors_tree_model import (
    FilterByExtentProxyModel,
    FilterProxyModel,
    QualityErrorsTreeBaseModel,
    StyleProxyModel,
)
from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget

if TYPE_CHECKING:
    from quality_result_gui.api.quality_api_client import QualityResultClient

iface = cast(QgisInterface, utils_iface)


class QualityResultManager(QObject):
    closed = pyqtSignal()
    error_checked = pyqtSignal(str, bool)
    quality_error_selected = pyqtSignal(QualityError, SelectionType)

    def __init__(
        self, api_client: "QualityResultClient", parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent=parent)

        self._api_client = api_client

        self.visualizer = QualityErrorVisualizer(self._api_client.get_crs())
        # This also creates the layer
        # TODO: Move to show_widget method to be cleaner.
        # Layer creation should probably be done separately.
        self.visualizer.show_errors()

        self.dock_widget = QualityErrorsDockWidget(iface.mainWindow())
        self.dock_widget.closed.connect(self.closed)

        self.dock_widget.error_tree_view.errors_inserted.connect(
            lambda errors: self.visualizer.add_new_errors(
                self._quality_errors_to_features(errors)
            )
        )
        self.dock_widget.error_tree_view.errors_removed.connect(
            lambda errors: self.visualizer.remove_errors(
                self._quality_errors_to_features(errors)
            )
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

        self._filter_map_extent_model = FilterByExtentProxyModel()
        self._filter_map_extent_model.setSourceModel(self._filter_model)

        self._styled_model = StyleProxyModel()
        self._styled_model.setSourceModel(self._filter_map_extent_model)

        self.dock_widget.error_tree_view.setModel(self._styled_model)

        self.dock_widget.filter_with_map_extent_check_box.toggled.connect(
            self._filter_map_extent_model.set_enabled
        )
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

    def _quality_errors_to_features(
        self, quality_errors: List[QualityError]
    ) -> Generator[ErrorFeature, None, None]:
        return (
            ErrorFeature.from_quality_error(quality_error, self._api_client.get_crs())
            for quality_error in quality_errors
        )

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

        self._user_processed_filter = UserProcessedFilter()
        self.add_filter(self._user_processed_filter)

    def unload(self) -> None:
        self._fetcher.stop()
        self._filter_map_extent_model.set_enabled(False)
        self.dock_widget.deleteLater()
        self.visualizer.remove_quality_error_layer()

    def _update_info_label(self, status: CheckStatus) -> None:
        status_text = CHECK_STATUS_LABELS.get(
            status, tr("Status of fetching quality result unknown")
        )
        self.dock_widget.info_label.setText(status_text)

    def show_dock_widget(self) -> None:
        self._fetcher.start()
        self.dock_widget.show()

    def add_filter(self, filter: AbstractQualityErrorFilter) -> None:
        filter.filters_changed.connect(self.dock_widget._update_filter_menu_icon_state)
        self.dock_widget.filter_menu.add_filter_menu(filter.menu)
        self._filter_model.add_filter(filter)
