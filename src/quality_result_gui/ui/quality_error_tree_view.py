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

from types import GeneratorType
from typing import TYPE_CHECKING, Generator, Optional, cast

from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant, pyqtSignal
from qgis.PyQt.QtWidgets import QTreeView, QWidget
from qgis_plugin_tools.tools.decorations import log_if_fails

from quality_result_gui import SelectionType
from quality_result_gui.api.types.quality_error import QualityError
from quality_result_gui.quality_errors_tree_model import (
    ErrorDataType,
    ModelColumn,
    QualityErrorTreeItemType,
)

if TYPE_CHECKING:
    from qgis.PyQt.QtGui import QMouseEvent

TREE_VIEW_STYLE = """
        QTreeView::item:hover, QTreeView::item:selected:active,
        QTreeView::item:selected, QTreeView::branch:selected:active,
        QTreeView::branch:hover {
            background: #f5f5f5;
            border-bottom: 1px solid #f5f5f5;
            color: black;
        }
        QTreeView::item {
            border-bottom: 1px solid #f5f5f5;
            background: white;
        }
        """


class QualityErrorTreeView(QTreeView):
    quality_error_selected = pyqtSignal(QualityError, SelectionType)

    errors_inserted = pyqtSignal(GeneratorType)
    errors_removed = pyqtSignal(GeneratorType)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.source_button_event: Optional["QMouseEvent"] = None

        self.setColumnWidth(ModelColumn.TYPE_OR_ID.value, 150)
        self.setIndentation(10)
        self.setUniformRowHeights(True)

        self.setStyleSheet(TREE_VIEW_STYLE)

    def setModel(  # noqa: N802 (override qt method)
        self, model: Optional[QAbstractItemModel]
    ) -> None:
        super().setModel(model)
        if not model:
            return

        self.selectionModel().currentChanged.connect(self._on_current_item_changed)

        model.rowsInserted.connect(self._on_model_rows_inserted)
        model.rowsAboutToBeRemoved.connect(self._on_rows_about_to_be_removed)

    def mousePressEvent(  # noqa: N802 (override qt method)
        self, event: "QMouseEvent"
    ) -> None:
        self.source_button_event = event
        # Calling super will trigger currentChanged if row clicked
        super().mousePressEvent(event)

        self.source_button_event = None

    def _on_model_rows_inserted(
        self, parent: QModelIndex, first: int, last: int
    ) -> None:
        self.expandRecursively(parent)

        for i in range(first, last + 1):
            index = self.model().index(i, 0, parent)

            # Update visualized errors
            new_errors_to_visualize = self._get_quality_errors_from_index(index)
            self.errors_inserted.emit(new_errors_to_visualize)

    def _on_rows_about_to_be_removed(
        self, parent: QModelIndex, first: int, last: int
    ) -> None:
        for i in range(first, last + 1):
            index = self.model().index(i, 0, parent)

            # Update visualized errors
            errors_to_remove = self._get_quality_errors_from_index(index)
            self.errors_removed.emit(errors_to_remove)

    @log_if_fails
    def _on_current_item_changed(
        self, current_index: QModelIndex, previous_index: QModelIndex
    ) -> None:
        quality_error = self._get_quality_error_from_row(current_index)

        if quality_error is None:
            return

        selection_mode = (
            SelectionType.RightClick
            if (
                self.source_button_event is not None
                and self.source_button_event.button() == Qt.MouseButton.RightButton
            )
            else SelectionType.Other
        )

        self.quality_error_selected.emit(quality_error, selection_mode)

    def _get_quality_errors_from_index(
        self, index: QModelIndex
    ) -> Generator[QualityError, None, None]:
        """Get quality errors recursively from index."""

        if not index.isValid():
            return

        row_count = self.model().rowCount(index)
        if row_count == 0:
            # Index may now be at quality error row, which has never any children
            error = self._get_quality_error_from_row(index)
            if error is not None:
                yield error
            return
        else:
            for i in range(row_count):
                yield from self._get_quality_errors_from_index(index.child(i, 0))

    def _get_quality_error_from_row(
        self,
        row_index: QModelIndex,
    ) -> Optional[QualityError]:
        data = row_index.data(Qt.UserRole)

        if not QVariant(data).isValid():
            return None

        item_type, item_data = cast(ErrorDataType, data)
        # Single quality error
        if item_type == QualityErrorTreeItemType.ERROR:
            return cast(QualityError, item_data)
        return None
