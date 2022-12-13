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
from pathlib import Path
from typing import Iterator, List, Optional, cast

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsRectangle
from qgis.gui import QgisInterface
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex, Qt, QVariant, pyqtSignal
from qgis.PyQt.QtGui import QMouseEvent
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QLabel,
    QPushButton,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.decorations import log_if_fails
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorsByPriority,
)
from quality_result_gui.quality_data_fetcher import (
    BackgroundQualityResultsFetcher,
    CheckStatus,
)
from quality_result_gui.quality_error_visualizer import (
    ErrorFeature,
    QualityErrorVisualizer,
)
from quality_result_gui.quality_errors_tree_filter_menu import (
    QualityErrorsTreeFilterMenu,
)
from quality_result_gui.quality_errors_tree_model import (
    ErrorDataType,
    FilterByExtentModel,
    FilterByMenuModel,
    ModelColumn,
    QualityErrorIdentityProxyModel,
    QualityErrorsTreeBaseModel,
    QualityErrorTreeItemType,
)

iface: QgisInterface = utils_iface

LOGGER = logging.getLogger(__name__)


DOCK_UI: QWidget
DOCK_UI, _ = uic.loadUiType(
    str(Path(__file__).parent.joinpath("quality_errors_dock.ui"))
)


class QualityErrorsDockWidget(QDockWidget, DOCK_UI):
    """
    Graphical user interface for quality errors dock widget.
    """

    # type necessary widgets that are provided from the .ui
    error_tree_layout: QVBoxLayout
    filter_button: QToolButton
    info_label: QLabel
    close_button: QPushButton
    map_actions_layout: QVBoxLayout
    filter_with_map_extent_check_box: QCheckBox
    show_errors_on_map_check_box: QCheckBox

    quality_errors: List[QualityErrorsByPriority]

    def __init__(
        self, api_client: QualityResultClient, parent: Optional[QWidget]
    ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.quality_errors = []
        self._api_client = api_client

        # Create filter menu before tree view
        self.filter_button.setIcon(QgsApplication.getThemeIcon("/mActionFilter2.svg"))
        self.quality_errors_tree_filter_menu = QualityErrorsTreeFilterMenu(self)
        self.filter_button.setMenu(self.quality_errors_tree_filter_menu)
        self.quality_errors_tree_filter_menu.filters_changed.connect(
            lambda *args: self._update_filter_menu_icon_state()
        )

        # Remove placeholder map extent check box, replace with custom check box
        map_extent_check_box_placeholder = self.map_actions_layout.takeAt(0)
        map_extent_check_box_placeholder.widget().deleteLater()
        self.filter_with_map_extent_check_box = MapExtentCheckBox()
        self.map_actions_layout.insertWidget(0, self.filter_with_map_extent_check_box)

        # Remove placeholder show errors on map check box, replace with custom check box
        show_errors_check_box_placeholder = self.map_actions_layout.takeAt(1)
        show_errors_check_box_placeholder.widget().deleteLater()
        self.show_errors_on_map_check_box = ShowErrorsOnMapCheckBox()
        self.show_errors_on_map_check_box.setChecked(True)
        self.map_actions_layout.insertWidget(1, self.show_errors_on_map_check_box)

        self._fetcher = BackgroundQualityResultsFetcher(api_client, self)
        self._fetcher.status_changed.connect(self._update_label_for_status)

        # Remove placeholder tree view
        tree_view_placeholder = self.error_tree_layout.takeAt(0)
        tree_view_placeholder.widget().deleteLater()

        # Create custom tree view and insert to layout
        self.error_tree_view = QualityErrorTreeView(
            self.quality_errors_tree_filter_menu,
            self.filter_with_map_extent_check_box,
            self.show_errors_on_map_check_box,
            self._fetcher,
            api_client.get_crs(),
        )
        self.visibilityChanged.connect(self._on_visibility_changed)

        self.error_tree_layout.insertWidget(0, self.error_tree_view)

        self._update_filter_menu_icon_state()

        self.close_button.clicked.connect(self.close)

    @log_if_fails
    def _update_label_for_status(self, status: CheckStatus) -> None:
        self.info_label.setText(
            {
                CheckStatus.CHECKING: tr("Checking for quality result updates"),
                CheckStatus.RESULT_ONGOING: tr("Quality check is in progress"),
                CheckStatus.RESULT_FAILED: tr("Quality result update failed"),
                CheckStatus.RESULT_UPDATED: tr("Quality results are up to date"),
            }.get(status)
        )

    def _on_visibility_changed(self, visible: bool) -> None:
        if visible:
            self.error_tree_view.on_visualized_data_changed()
            self._fetcher.set_checks_enabled(True)
        else:
            self._fetcher.set_checks_enabled(False)

            # Disable filtering by map extent always when dock is closed
            if self.filter_with_map_extent_check_box.isChecked() is True:
                self.filter_with_map_extent_check_box.setChecked(False)

            self.error_tree_view.visualizer.remove_quality_error_layer()

    def _update_filter_menu_icon_state(self) -> None:
        if self.error_tree_view.base_model.rowCount(QModelIndex()) == 0:
            self.filter_button.setDisabled(True)
        else:
            self.filter_button.setEnabled(True)
            if self.quality_errors_tree_filter_menu.is_any_filter_active():
                self.filter_button.setDown(True)
            else:
                self.filter_button.setDown(False)

    def _on_tree_view_data_changed(self) -> None:
        self._update_filter_menu_icon_state()


class MapExtentCheckBox(QCheckBox):

    extents_changed = pyqtSignal(bool, QgsRectangle)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(tr("Show only errors within map extent"), parent)

        self.toggled.connect(self.on_toggled)

    def on_toggled(self, checked: bool) -> None:
        if checked is True:
            iface.mapCanvas().extentsChanged.connect(self._on_map_extent_changed)
        else:
            iface.mapCanvas().extentsChanged.disconnect(self._on_map_extent_changed)

        self.extents_changed.emit(checked, self._canvas_extent())

    def _canvas_extent(self) -> QgsRectangle:
        return iface.mapCanvas().extent()

    def _on_map_extent_changed(self) -> None:
        self.extents_changed.emit(self.isChecked(), self._canvas_extent())


class ShowErrorsOnMapCheckBox(QCheckBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(tr("Visualize errors on map"), parent)


class QualityErrorTreeView(QTreeView):
    quality_error_checked = pyqtSignal(str, bool)

    def __init__(
        self,
        filter_menu: QualityErrorsTreeFilterMenu,
        map_extent_check_box: MapExtentCheckBox,
        show_errors_on_map_check_box: ShowErrorsOnMapCheckBox,
        fetcher: BackgroundQualityResultsFetcher,
        crs: QgsCoordinateReferenceSystem,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._crs = crs
        self.visualizer = QualityErrorVisualizer()
        show_errors_on_map_check_box.toggled.connect(self.visualizer.change_visibility)

        self.source_button_event = None

        self.setColumnWidth(ModelColumn.TYPE_OR_ID.value, 250)
        self.setIndentation(10)
        self.setUniformRowHeights(True)

        self.base_model = QualityErrorsTreeBaseModel(
            self, self._quality_error_checked_callback
        )
        fetcher.results_received.connect(self.base_model.refresh_model)
        self.base_model.filterable_data_changed.connect(
            filter_menu.refresh_feature_type_filters
        )
        self.base_model.filterable_data_changed.connect(self.on_visualized_data_changed)

        self.filter_by_menu_model = FilterByMenuModel(self)
        self.filter_by_menu_model.setSourceModel(self.base_model)
        self.filter_by_menu_model.rowsInserted.connect(self.on_visualized_data_changed)
        self.filter_by_menu_model.rowsRemoved.connect(self.on_visualized_data_changed)

        filter_menu.filters_changed.connect(self.filter_by_menu_model.update_filters)

        filter_by_extent_model = FilterByExtentModel(self)
        filter_by_extent_model.setSourceModel(self.filter_by_menu_model)

        map_extent_check_box.extents_changed.connect(
            filter_by_extent_model.update_filters
        )

        styled_model = QualityErrorIdentityProxyModel(self)
        styled_model.setSourceModel(filter_by_extent_model)
        self.setModel(styled_model)
        self.selectionModel().currentChanged.connect(self._on_current_item_changed)
        self.model().rowsInserted.connect(self._on_rows_inserted)

        # connect reset after setting model to fire expansion after view is reset
        # https://www.qtcentre.org/threads/61009-QTreeView-expansion-after-model-reset?p=269908#post269908
        # for some reason initial model open wont expand if directconnection is used,
        # queue instead to wait for synchronous code to run the model reset first
        filter_by_extent_model.modelReset.connect(
            self._expand_all_error_rows, Qt.ConnectionType.QueuedConnection
        )

    def mousePressEvent(  # noqa: N802 (override qt method)
        self, event: QMouseEvent
    ) -> None:
        self.source_button_event = event
        # Calling super will trigger currentChanged if row clicked
        super().mousePressEvent(event)

        self.source_button_event = None

    def on_visualized_data_changed(self) -> None:
        self.visualizer.refresh_all_errors(
            self._get_error_features_to_visualize(),
            self._get_error_feature_from_row(self.selectionModel().currentIndex()),
        )

    def _on_rows_inserted(self, parent: QModelIndex, first: int, last: int) -> None:
        self.expandRecursively(parent)

    def _expand_all_error_rows(self) -> None:
        self.expandRecursively(QModelIndex())

    @log_if_fails
    def _on_current_item_changed(
        self, current_index: QModelIndex, previous_index: QModelIndex
    ) -> None:
        error_feature = self._get_error_feature_from_row(current_index)

        if error_feature is None:
            return

        # Right button behaviour
        if (
            self.source_button_event is not None
            and self.source_button_event.button() == Qt.RightButton
        ):
            self.visualizer.zoom_to_geometries_and_flash(
                [error_feature], preserve_scale=True
            )
        # Left button or keyboard behaviour
        else:
            self.visualizer.zoom_to_geometries_and_flash(
                [error_feature], preserve_scale=False
            )

        self.visualizer.refresh_selected_error(error_feature)

    def _get_error_features_to_visualize(self) -> List[ErrorFeature]:
        error_features: List[ErrorFeature] = []

        def _get_quality_errors_from_rows(index: QModelIndex) -> Iterator[ErrorFeature]:
            """Get quality error rows from index."""
            if not index.isValid():
                return

            row_count = self.filter_by_menu_model.rowCount(index)
            if row_count == 0:
                # Index is for quality error row, which has no children
                error = self._get_error_feature_from_row(index)
                if error is not None:
                    yield error
            else:
                for i in range(row_count):
                    yield from _get_quality_errors_from_rows(index.child(i, 0))

        for i in range(self.filter_by_menu_model.rowCount(QModelIndex())):
            index = self.filter_by_menu_model.index(i, 0, QModelIndex())
            error_features += list(_get_quality_errors_from_rows(index))

        return error_features

    def _quality_error_checked_callback(
        self, error_hash: str, is_checked: bool
    ) -> None:
        self.quality_error_checked.emit(error_hash, is_checked)

    def _get_error_feature_from_row(
        self,
        row_index: QModelIndex,
    ) -> Optional[ErrorFeature]:
        data = row_index.data(Qt.UserRole)

        if not QVariant(data).isValid():
            return None

        item_type, item_data = cast(ErrorDataType, data)

        # Single quality error
        if item_type == QualityErrorTreeItemType.ERROR:
            quality_error = cast(QualityError, item_data)
            return ErrorFeature(
                quality_error.unique_identifier,
                quality_error.priority,
                quality_error.geometry,
                self._crs,
            )
        return None
