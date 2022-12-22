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

import enum
import logging
from abc import abstractmethod
from typing import Any, Callable, List, NewType, Optional, Set, Tuple, cast

from qgis.core import QgsRectangle
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QIdentityProxyModel,
    QModelIndex,
    QObject,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QVariant,
    pyqtSignal,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.api.types.quality_error import (
    ERROR_PRIORITY_LABEL,
    ERROR_TYPE_LABEL,
    QualityError,
    QualityErrorPriority,
    QualityErrorsByPriority,
)

LOGGER = logging.getLogger(__name__)


class ModelColumn(enum.Enum):
    TYPE_OR_ID = 0
    ERROR_DESCRIPTION = 1


COLUMN_HEADERS = {
    ModelColumn.TYPE_OR_ID: tr("Errors"),
    ModelColumn.ERROR_DESCRIPTION: tr("Error description"),
}


def _count_quality_error_rows(model: QAbstractItemModel, index: QModelIndex) -> int:
    if not index.isValid():
        return 0
    num_rows = 0
    row_count = model.rowCount(index)
    if row_count == 0:
        # Index is for quality error row, which has no children
        return 1
    for i in range(row_count):
        child_index = index.child(i, 0)
        num_rows += _count_quality_error_rows(model, child_index)
    return num_rows


def _count_all_rows(model: QAbstractItemModel) -> int:
    num_rows = 0
    for i in range(model.rowCount(QModelIndex())):
        index = model.index(i, 0, QModelIndex())
        num_rows += _count_quality_error_rows(model, index)
    return num_rows


def get_error_feature_types(
    errors_by_priority: List[QualityErrorsByPriority],
) -> Set[str]:
    feature_types = set()

    for errors_by_feature_type in errors_by_priority:
        for errors in errors_by_feature_type.errors:
            feature_types.add(errors.feature_type)

    return feature_types


def get_error_feature_attributes(
    quality_errors: List[QualityErrorsByPriority],
) -> Set[Optional[str]]:
    feature_attributes = set()

    for errors_by_priority in quality_errors:
        for error in errors_by_priority.get_all_errors():
            feature_attributes.add(error.attribute_name)
    return feature_attributes


class QualityErrorTreeItemType(enum.Enum):
    HEADER = enum.auto()
    PRIORITY = enum.auto()
    FEATURE_TYPE = enum.auto()
    FEATURE = enum.auto()
    ERROR = enum.auto()


ErrorDataType = NewType(
    "ErrorDataType",
    Tuple[QualityErrorTreeItemType, Any],
)


class QualityErrorTreeItem:
    def __init__(
        self,
        data: List[Any],
        item_type: QualityErrorTreeItemType,
        parent: Optional["QualityErrorTreeItem"] = None,
    ) -> None:
        self._item_parent = parent
        self._item_data = data
        self._child_items: List["QualityErrorTreeItem"] = []

        self.item_type = item_type

    def _append_child_item(self, item: "QualityErrorTreeItem") -> None:
        self._child_items.append(item)

    def child(self, row: int) -> Optional["QualityErrorTreeItem"]:
        if row >= 0 and row < self.child_count():
            return self._child_items[row]
        return None

    def child_count(self) -> int:
        return len(self._child_items)

    def row(self) -> int:
        if self._item_parent is not None:
            return self._item_parent._child_items.index(self)
        return 0

    def column_count(self) -> int:
        return len(self._item_data)

    def data(
        self, column_index: int, role: Qt.ItemDataRole = Qt.DisplayRole
    ) -> QVariant:
        if not (column_index >= 0 and column_index < len(self._item_data)):
            return QVariant()

        item_data = self._item_data[column_index]
        column_data = QVariant()

        column = ModelColumn(column_index)

        if self.item_type == QualityErrorTreeItemType.HEADER:
            return QVariant()

        if role == Qt.UserRole and column == ModelColumn.TYPE_OR_ID:
            return (self.item_type, self._item_data[column_index])

        if role == Qt.DisplayRole and column == ModelColumn.TYPE_OR_ID:
            if self.item_type == QualityErrorTreeItemType.PRIORITY:
                column_data = ERROR_PRIORITY_LABEL[QualityErrorPriority(item_data)]

            elif self.item_type == QualityErrorTreeItemType.FEATURE_TYPE:
                column_data = item_data
                # TODO: how to configurate custom data mapping
                # column_data = common.FEATURE_TYPE_NAMES[item_data]

            elif self.item_type == QualityErrorTreeItemType.FEATURE:
                column_data = item_data[1][:8]

            elif self.item_type == QualityErrorTreeItemType.ERROR:
                quality_error = cast(QualityError, item_data)
                column_data = ERROR_TYPE_LABEL[quality_error.error_type]
            return QVariant(column_data)

        if (
            role == Qt.DisplayRole
            and column == ModelColumn.ERROR_DESCRIPTION
            and self.item_type == QualityErrorTreeItemType.ERROR
        ):
            # lang = locale.get_qgis_locale().split("_")[0]
            return item_data["fi"]

        if (
            role == Qt.ToolTipRole
            and column == ModelColumn.ERROR_DESCRIPTION
            and self.item_type == QualityErrorTreeItemType.ERROR
        ):
            # lang = locale.get_qgis_locale().split("_")[0]
            return item_data["fi"]

        if (
            role == Qt.CheckStateRole
            and column == ModelColumn.TYPE_OR_ID
            and self.item_type == QualityErrorTreeItemType.ERROR
        ):
            quality_error = cast(QualityError, item_data)
            if quality_error.is_user_processed is True:
                return QVariant(Qt.Checked)
            else:
                return QVariant(Qt.Unchecked)

        return QVariant()

    def parent(self) -> Optional["QualityErrorTreeItem"]:
        return self._item_parent


class QualityErrorsTreeBaseModel(QAbstractItemModel):
    """
    Simple tree model. Adapted to use conflict process directly as the data source.

    https://doc.qt.io/qt-5/qtwidgets-itemviews-simpletreemodel-example.html
    """

    filterable_data_changed = pyqtSignal(list)
    _quality_error_checked_callback: Callable

    def __init__(
        self,
        parent: Optional[QObject],
        quality_error_checked_callback: Callable,
    ) -> None:
        super().__init__(parent)

        setattr(  # noqa: B010
            self,
            "_quality_error_checked_callback",
            quality_error_checked_callback,
        )

        self._root_item = QualityErrorTreeItem(
            len(COLUMN_HEADERS) * [None],
            QualityErrorTreeItemType.HEADER,
        )

    def _setup_model_data(self, quality_errors: List[QualityErrorsByPriority]) -> None:
        self._root_item = QualityErrorTreeItem(
            len(COLUMN_HEADERS) * [None],
            QualityErrorTreeItemType.HEADER,
        )

        for errors_by_priority in quality_errors:
            priority_row = QualityErrorTreeItem(
                [errors_by_priority.priority, None],
                QualityErrorTreeItemType.PRIORITY,
                self._root_item,
            )

            for errors_by_feature_type in errors_by_priority.errors:
                feature_type_row = QualityErrorTreeItem(
                    [errors_by_feature_type.feature_type, None],
                    QualityErrorTreeItemType.FEATURE_TYPE,
                    priority_row,
                )

                for errors_by_feature_id in errors_by_feature_type.errors:
                    feature_id_row = QualityErrorTreeItem(
                        [
                            (
                                errors_by_feature_type.feature_type,
                                errors_by_feature_id.feature_id,
                            ),
                            None,
                        ],
                        QualityErrorTreeItemType.FEATURE,
                        feature_type_row,
                    )

                    for quality_error in errors_by_feature_id.errors:
                        quality_error_row = QualityErrorTreeItem(
                            [
                                quality_error,
                                {
                                    "fi": quality_error["error_description_fi"],
                                    "en": quality_error["error_description_en"],
                                    "sv": quality_error["error_description_sv"],
                                },
                            ],
                            QualityErrorTreeItemType.ERROR,
                            feature_id_row,
                        )
                        feature_id_row._append_child_item(quality_error_row)

                    feature_type_row._append_child_item(feature_id_row)

                priority_row._append_child_item(feature_type_row)

            self._root_item._append_child_item(priority_row)

    def index(self, row: int, column: int, parent: QModelIndex) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        child = parent_item.child(row)

        if child is not None:
            return self.createIndex(row, column, child)

        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item: QualityErrorTreeItem = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item == self._root_item or parent_item is None:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex) -> int:  # noqa: N802 (qt override)
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex) -> int:  # noqa: N802 (qt override)
        if not parent.isValid():
            parent_item = self._root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.column_count()

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole
    ) -> QVariant:
        if not index.isValid():
            return QVariant()

        item: QualityErrorTreeItem = index.internalPointer()

        return item.data(index.column(), role)

    def headerData(  # noqa: N802 (qt override)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> QVariant:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                model_column = ModelColumn(section)
                if model_column == ModelColumn.TYPE_OR_ID:
                    total_count = _count_all_rows(self)
                    return QVariant(
                        f"{COLUMN_HEADERS.get(model_column, QVariant())}"
                        f" ({total_count}/{total_count})"
                    )
                return COLUMN_HEADERS.get(model_column, QVariant())
            except ValueError:
                return QVariant()
        return QVariant()

    def setData(  # noqa: N802 (qt override)
        self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole
    ) -> bool:
        if not index.isValid() or role == Qt.EditRole:
            return False

        column = ModelColumn(index.column())
        item: QualityErrorTreeItem = index.internalPointer()

        if (
            column == ModelColumn.TYPE_OR_ID
            and item.item_type == QualityErrorTreeItemType.ERROR
        ):
            quality_error = cast(QualityError, item._item_data[0])

            if role == Qt.CheckStateRole:
                checked = value == Qt.Checked
                quality_error.is_user_processed = checked
                self._quality_error_checked_callback(
                    quality_error.unique_identifier, checked
                )
                self.dataChanged.emit(index, index)
                return True

        return False

    def flags(  # (qt override)
        self,
        index: QModelIndex,
    ) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        column = ModelColumn(index.column())
        item: QualityErrorTreeItem = index.internalPointer()

        if (
            column == ModelColumn.TYPE_OR_ID
            and item.item_type == QualityErrorTreeItemType.ERROR
        ):
            return super().flags(index) | Qt.ItemIsUserCheckable

        return super().flags(index)

    def refresh_model(self, quality_errors: List[QualityErrorsByPriority]) -> None:
        self.beginResetModel()
        self._setup_model_data(quality_errors)
        self.endResetModel()
        self.filterable_data_changed.emit(quality_errors)


class QualityErrorIdentityProxyModel(QIdentityProxyModel):
    def __init__(self, parent: Optional[QObject]) -> None:
        super().__init__(parent)
        styles = """
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
        if parent:
            parent.setStyleSheet(styles)

    def headerData(  # noqa: N802 (qt override)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> QVariant:
        return self.sourceModel().headerData(section, orientation, role)

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole
    ) -> QVariant:
        source_index = self.mapToSource(index)
        data = self.sourceModel().data(source_index, Qt.UserRole)

        if not QVariant(data).isValid():
            return self.sourceModel().data(source_index, role)

        (item_type, item_data) = cast(ErrorDataType, data)
        column = ModelColumn(index.column())
        if (
            role == Qt.FontRole
            and column == ModelColumn.TYPE_OR_ID
            and item_type == QualityErrorTreeItemType.PRIORITY
        ):
            font = QFont()
            font.setBold(True)
            font.setPixelSize(15)
            return QVariant(font)

        if (
            role == Qt.FontRole
            and column == ModelColumn.TYPE_OR_ID
            and item_type == QualityErrorTreeItemType.FEATURE_TYPE
        ):
            font = QFont()
            font.setBold(True)
            return QVariant(font)

        if (
            role == Qt.SizeHintRole
            and column == ModelColumn.TYPE_OR_ID
            and item_type == QualityErrorTreeItemType.PRIORITY
        ):
            size = QSize()
            size.setHeight(26)
            return QVariant(size)

        if (
            role == Qt.ForegroundRole
            and column == ModelColumn.TYPE_OR_ID
            and item_type == QualityErrorTreeItemType.ERROR
            and cast(QualityError, item_data).is_user_processed is True
        ):
            return QVariant(QColor(Qt.lightGray))

        if (
            role == Qt.ForegroundRole
            and column == ModelColumn.TYPE_OR_ID
            and item_type == QualityErrorTreeItemType.FEATURE
        ):
            color = QColor()
            color.setRgb(75, 75, 75)
            return QVariant(color)

        return self.sourceModel().data(source_index, role)


class BaseFilterModel(QSortFilterProxyModel):
    def __init__(self, parent: Optional[QObject]) -> None:
        super().__init__(parent)
        self.setFilterRole(Qt.UserRole)

    def filterAcceptsRow(  # noqa: N802 (qt override)
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:

        source_index = self.sourceModel().index(source_row, 0, source_parent)

        if source_index.isValid():
            is_visible = True
            # Check the current index
            data = self.sourceModel().data(source_index, self.filterRole())

            # Always accept anything that did not return valid data
            if not QVariant(data).isValid():
                return True

            (item_type, item_value) = cast(ErrorDataType, data)

            if item_type in (
                QualityErrorTreeItemType.FEATURE_TYPE,
                QualityErrorTreeItemType.FEATURE,
                QualityErrorTreeItemType.ERROR,
            ):
                is_visible = self.accept_row(item_type, item_value)

            # Check child indexes if index is visible:
            #  -> if they match, match current index also
            if is_visible is True:
                children_visible = False
                for i in range(  # noqa: SIM110
                    self.sourceModel().rowCount(source_index)
                ):
                    if self.filterAcceptsRow(i, source_index):
                        return True

                # Hide row if all children rows are hidden
                if (
                    item_type
                    in (
                        QualityErrorTreeItemType.PRIORITY,
                        QualityErrorTreeItemType.FEATURE_TYPE,
                        QualityErrorTreeItemType.FEATURE,
                    )
                    and children_visible is False
                ):
                    return False

            return is_visible
        return True

    @abstractmethod
    def accept_row(
        self, tree_item_type: QualityErrorTreeItemType, tree_item_value: Any
    ) -> bool:
        raise NotImplementedError()

    def headerData(  # noqa: N802 (qt override)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> QVariant:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                model_column = ModelColumn(section)
                if model_column == ModelColumn.TYPE_OR_ID:
                    total_count = str(
                        self.sourceModel()
                        .headerData(section, orientation, role)
                        .value()
                        .split("/")[1]
                    )
                    total_count = "".join([n for n in total_count if n.isdigit()])

                    filtered_count = _count_all_rows(self)
                    return QVariant(
                        f"{COLUMN_HEADERS.get(model_column, QVariant())}"
                        f" ({filtered_count}/{total_count})"
                    )
                return COLUMN_HEADERS.get(model_column, QVariant())
            except ValueError:
                return QVariant()
        return QVariant()

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole
    ) -> QVariant:

        if not index.isValid():
            return QVariant()

        source_index = self.mapToSource(index)
        return self.sourceModel().data(source_index, role)


class FilterByMenuModel(BaseFilterModel):
    _filter_by_error_type: Set[int]
    _filter_by_feature_types: Set[str]
    _filter_by_feature_attributes: Set[str]
    _filter_by_feature_attributes_changed: bool
    _show_user_processed: bool

    def __init__(self, parent: Optional[QObject]) -> None:
        super().__init__(parent)
        self._filter_by_error_type = set()
        self._filter_by_feature_types = set()
        self._filter_by_feature_attributes = set()
        self._show_user_processed = True

    def update_filters(
        self,
        filtered_feature_types: Set[str],
        filtered_error_types: Set[int],
        filtered_feature_attributes: Set[str],
        show_user_processed: bool,
    ) -> None:
        self._filter_by_feature_types = filtered_feature_types
        self._filter_by_error_type = filtered_error_types
        self._filter_by_feature_attributes = filtered_feature_attributes
        self._show_user_processed = show_user_processed
        self.invalidateFilter()

    def accept_row(
        self,
        tree_item_type: QualityErrorTreeItemType,
        tree_item_value: Any,
    ) -> bool:
        if tree_item_type == tree_item_type.FEATURE_TYPE:
            return self._is_feature_type_visible(tree_item_value)

        if tree_item_type == tree_item_type.ERROR:
            return self._is_quality_error_visible(tree_item_value)

        return True

    def _is_quality_error_visible(self, quality_error: QualityError) -> bool:
        return (
            quality_error.error_type.value in self._filter_by_error_type
            and quality_error.feature_type in self._filter_by_feature_types
            and quality_error.attribute_name in self._filter_by_feature_attributes
            and (
                self._show_user_processed is True
                or quality_error.is_user_processed is False
            )
        )

    def _is_feature_type_visible(self, feature_type: str) -> bool:
        return feature_type in self._filter_by_feature_types


class FilterByExtentModel(BaseFilterModel):
    _filter_by_extent: bool
    _extent: QgsRectangle

    def __init__(self, parent: Optional[QObject]) -> None:
        super().__init__(parent)
        self._filter_by_extent = False

    def update_filters(self, filter_by_extent: bool, extent: QgsRectangle) -> None:
        self._filter_by_extent = filter_by_extent
        self._extent = extent
        self.invalidateFilter()

    def accept_row(
        self,
        tree_item_type: QualityErrorTreeItemType,
        tree_item_value: Any,
    ) -> bool:
        if self._filter_by_extent is False:
            return True

        return not (
            tree_item_type == tree_item_type.ERROR
            and self._is_error_visible(tree_item_value) is False
        )

    def _is_error_visible(self, quality_error: QualityError) -> bool:
        return quality_error.geometry.intersects(self._extent)
