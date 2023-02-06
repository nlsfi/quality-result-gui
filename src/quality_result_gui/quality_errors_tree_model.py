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

import contextlib
import enum
import logging
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    NewType,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
    overload,
)

from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QIdentityProxyModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    QVariant,
    pyqtSignal,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.utils import iface as utils_iface
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.api.types.quality_error import (
    ERROR_PRIORITY_LABEL,
    ERROR_TYPE_LABEL,
    QualityError,
    QualityErrorPriority,
    QualityErrorsByPriority,
)

if TYPE_CHECKING:
    from qgis.core import QgsRectangle

    from quality_result_gui.quality_errors_filters import AbstractQualityErrorFilter

LOGGER = logging.getLogger(__name__)

iface = cast(QgisInterface, utils_iface)


class ModelColumn(enum.Enum):
    TYPE_OR_ID = 0
    ERROR_DESCRIPTION = 1


COLUMN_HEADERS = {
    ModelColumn.TYPE_OR_ID: tr("Errors"),
    ModelColumn.ERROR_DESCRIPTION: tr("Error description"),
}


def get_error_feature_types(
    errors_by_priority: List[QualityErrorsByPriority],
) -> Set[str]:
    return {
        errors.feature_type
        for errors_by_feature_type in errors_by_priority
        for errors in errors_by_feature_type.errors
    }


def get_error_feature_attributes(
    quality_errors: List[QualityErrorsByPriority],
) -> Set[str]:
    return {
        error.attribute_name
        for errors_by_priority in quality_errors
        for error in errors_by_priority.get_all_errors()
        if error.attribute_name
    }


def _get_quality_errors_indexes(
    model: QAbstractItemModel, index: QModelIndex
) -> Iterator[QModelIndex]:
    """Get quality all error indexes from index."""
    if not index.isValid():
        return

    row_count = model.rowCount(index)
    if row_count == 0:
        data = index.data(Qt.UserRole)
        (item_type, _) = cast(ErrorDataType, data)
        if item_type == QualityErrorTreeItemType.ERROR:
            # Index is for quality error row, which has no children
            yield index
    else:
        for i in range(row_count):
            yield from _get_quality_errors_indexes(model, index.child(i, 0))


def _count_quality_error_rows(model: QAbstractItemModel, index: QModelIndex) -> int:
    if not index.isValid():
        return 0
    num_rows = 0
    row_count = model.rowCount(index)
    if row_count == 0:
        data = index.data(Qt.UserRole)
        (item_type, _) = cast(ErrorDataType, data)
        if item_type == QualityErrorTreeItemType.ERROR:
            # Index is for quality error row
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
        key: str,
        item_type: QualityErrorTreeItemType,
        parent: Optional["QualityErrorTreeItem"] = None,
    ) -> None:
        self.key = key
        self._item_parent = parent
        self._item_data = data
        self._child_items: List["QualityErrorTreeItem"] = []
        self._child_item_map: Dict[str, int] = {}

        self.item_type = item_type

    def append_child_item(self, item: "QualityErrorTreeItem") -> None:
        self._child_item_map[item.key] = len(self._child_items)
        self._child_items.append(item)

    def remove_child_item(self, item: "QualityErrorTreeItem") -> None:
        self._child_items.remove(item)
        self._child_item_map.pop(item.key)

    def get_child_by_key(self, key: str) -> "QualityErrorTreeItem":
        return self._child_items[self._child_item_map[key]]

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

        if role == Qt.UserRole and column in [
            ModelColumn.TYPE_OR_ID,
            ModelColumn.ERROR_DESCRIPTION,
        ]:
            index = (
                column_index - 1
                if column == ModelColumn.ERROR_DESCRIPTION
                else column_index
            )
            return (self.item_type, self._item_data[index])

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
            role in [Qt.DisplayRole, Qt.ToolTipRole]
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

    filterable_data_changed = pyqtSignal()
    error_checked = pyqtSignal(str, bool)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._root_item = QualityErrorTreeItem(
            len(COLUMN_HEADERS) * [None],
            "header",
            QualityErrorTreeItemType.HEADER,
        )
        # Show error priority rows always
        for priority in list(QualityErrorPriority):
            priority_item = QualityErrorTreeItem(
                [priority, None],
                str(priority.value),
                QualityErrorTreeItemType.PRIORITY,
                self._root_item,
            )
            self._add_item_to_model(priority_item, self._root_item)

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

    @overload
    def parent(self, child: QModelIndex) -> QModelIndex:
        ...

    @overload
    def parent(self) -> QObject:
        ...

    def parent(
        self, child: Optional[QModelIndex] = None
    ) -> Union[QModelIndex, QObject]:
        if child is None:
            return super().parent()

        if not child.isValid():
            return QModelIndex()

        child_item: QualityErrorTreeItem = child.internalPointer()
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

                self.error_checked.emit(quality_error.unique_identifier, checked)
                self.dataChanged.emit(index, index)

                parent_index = index
                while parent_index.isValid():
                    parent_index = parent_index.parent()
                    self.dataChanged.emit(parent_index, parent_index)
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

        updated_quality_error_ids = {
            error.unique_identifier
            for errors_by_priority in quality_errors
            for error in errors_by_priority.get_all_errors()
        }

        current_quality_error_ids = set()
        for i in range(self.rowCount(QModelIndex())):
            for index in _get_quality_errors_indexes(
                self, self.index(i, 0, QModelIndex())
            ):
                _, item_data = index.data(Qt.UserRole)
                current_quality_error_ids.add(
                    cast(QualityError, item_data).unique_identifier
                )

        deleted_error_ids = current_quality_error_ids - updated_quality_error_ids
        new_error_ids = updated_quality_error_ids - current_quality_error_ids

        # Nothing changed
        if not deleted_error_ids and not new_error_ids:
            return

        errors_to_be_added = (
            error
            for errors_by_priority in quality_errors
            for error in errors_by_priority.get_all_errors()
            if error.unique_identifier in new_error_ids
        )

        errors_to_be_deleted: List[Tuple[QualityErrorTreeItem, QModelIndex]] = []

        for i in range(self.rowCount(QModelIndex())):
            for index in _get_quality_errors_indexes(
                self, self.index(i, 0, QModelIndex())
            ):
                item: QualityErrorTreeItem = index.internalPointer()
                if item.key in deleted_error_ids:
                    errors_to_be_deleted.append((item, index))

        self._update_model_data(errors_to_be_added, errors_to_be_deleted)

        self.filterable_data_changed.emit()

    def _update_model_data(
        self,
        errors_to_be_added: Iterable[QualityError],
        errors_to_be_deleted: List[Tuple[QualityErrorTreeItem, QModelIndex]],
    ) -> None:
        """
        Updates model data based on new and deleted quality errors.

        Deletion of quality errors must be done in reversed order for model
        indices to stay valid during the update process. New items are added
        after deletion. Empty parents are left to the model as filter model
        will leave them out eventually.
        """
        # Remove quality error items that are no longer found from errors
        for item, item_index in reversed(errors_to_be_deleted):
            self._remove_item_from_model(item, item_index)

        # Add new quality error items and parent items for them if needed
        for quality_error in errors_to_be_added:
            priority_item = self._root_item.get_child_by_key(
                str(quality_error.priority.value)
            )

            try:
                feature_type_item = priority_item.get_child_by_key(
                    quality_error.feature_type
                )
            except KeyError:
                feature_type_item = QualityErrorTreeItem(
                    [quality_error.feature_type, None],
                    quality_error.feature_type,
                    QualityErrorTreeItemType.FEATURE_TYPE,
                    priority_item,
                )
                self._add_item_to_model(
                    feature_type_item,
                    priority_item,
                )

            try:
                feature_item = feature_type_item.get_child_by_key(
                    quality_error.feature_id
                )
            except KeyError:
                feature_item = QualityErrorTreeItem(
                    [
                        (
                            quality_error.feature_type,
                            quality_error.feature_id,
                        ),
                        None,
                    ],
                    quality_error.feature_id,
                    QualityErrorTreeItemType.FEATURE,
                    feature_type_item,
                )
                self._add_item_to_model(
                    feature_item,
                    feature_type_item,
                )

            quality_error_item = QualityErrorTreeItem(
                [
                    quality_error,
                    {
                        "fi": quality_error["error_description_fi"],
                        "en": quality_error["error_description_en"],
                        "sv": quality_error["error_description_sv"],
                    },
                ],
                quality_error.unique_identifier,
                QualityErrorTreeItemType.ERROR,
                feature_item,
            )

            self._add_item_to_model(
                quality_error_item,
                feature_item,
            )

    def _get_index_for_item(self, item: QualityErrorTreeItem) -> QModelIndex:

        if item.item_type == QualityErrorTreeItemType.HEADER:
            return QModelIndex()
        else:
            item_parent = item.parent()
            if item_parent is None:
                raise ValueError
            return self.index(item.row(), 0, self._get_index_for_item(item_parent))

    def _remove_item_from_model(
        self,
        item: QualityErrorTreeItem,
        item_index: QModelIndex,
    ) -> None:
        item_parent = item.parent()
        if item_parent is None:
            return

        self.beginRemoveRows(item_index.parent(), item.row(), item.row())
        item_parent.remove_child_item(item)
        self.endRemoveRows()

    def _add_item_to_model(
        self, item: QualityErrorTreeItem, item_parent: QualityErrorTreeItem
    ) -> None:
        parent_index = self._get_index_for_item(item_parent)
        self.beginInsertRows(
            parent_index,
            item_parent.child_count(),
            item_parent.child_count(),
        )
        item_parent.append_child_item(item)
        self.endInsertRows()


class StyleProxyModel(QIdentityProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

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
            font.setPointSize(10)
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


class AbstractFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setFilterRole(Qt.UserRole)

    def filterAcceptsRow(  # noqa: N802 (qt override)
        self, source_row: int, source_parent: QModelIndex
    ) -> bool:
        source_index = self.sourceModel().index(source_row, 0, source_parent)

        if not source_index.isValid():
            return True

        data = self.sourceModel().data(source_index, self.filterRole())
        if not QVariant(data).isValid():
            # Always accept anything that did not return valid data
            return True

        (item_type, item_value) = cast(ErrorDataType, data)

        row_accepted = self.accept_row(item_type, item_value)
        if not row_accepted:
            return False

        if item_type == QualityErrorTreeItemType.ERROR:
            return True
        else:
            return self._is_any_children_visible(source_index)

    @abstractmethod
    def accept_row(
        self, tree_item_type: QualityErrorTreeItemType, tree_item_value: Any
    ) -> bool:
        raise NotImplementedError()

    def _is_any_children_visible(self, source_index: QModelIndex) -> bool:
        child_count = self.sourceModel().rowCount(source_index)
        return any(
            self.filterAcceptsRow(child_row_num, source_index)
            for child_row_num in range(child_count)
        )


class FilterProxyModel(AbstractFilterProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._filters: List["AbstractQualityErrorFilter"] = []

    def add_filter(self, filter: "AbstractQualityErrorFilter") -> None:
        filter.filters_changed.connect(self.invalidateFilter)
        self._filters.append(filter)

        self.invalidateFilter()

    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        # TODO: Check only the changed filters.
        # Now this checks all the filters when one changes
        return all(
            quality_filter.accept_row(item_type, item_value)
            for quality_filter in self._filters
        )

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


class FilterByExtentProxyModel(AbstractFilterProxyModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._extent: Union["QgsRectangle", None] = None

    def set_extent(self, extent: Union["QgsRectangle", None]) -> None:
        self._extent = extent
        self.invalidateFilter()

    def _on_map_extent_changed(self) -> None:
        self.set_extent(iface.mapCanvas().extent())

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            iface.mapCanvas().extentsChanged.connect(self._on_map_extent_changed)
            self.set_extent(iface.mapCanvas().extent())
        else:
            with contextlib.suppress(TypeError):  # Ignore case when not connected
                iface.mapCanvas().extentsChanged.disconnect(self._on_map_extent_changed)

            self.set_extent(None)

    def accept_row(
        self, tree_item_type: QualityErrorTreeItemType, tree_item_value: Any
    ) -> bool:
        if not self._extent:
            return True
        if tree_item_type != tree_item_type.ERROR:
            return True

        quality_error = cast(QualityError, tree_item_value)

        return quality_error.geometry.intersects(self._extent)
