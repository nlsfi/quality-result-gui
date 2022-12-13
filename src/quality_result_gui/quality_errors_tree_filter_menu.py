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

import copy
from functools import partial
from typing import List, Optional, Set

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.api.types.quality_error import (
    ERROR_TYPE_LABEL,
    USER_PROCESSED_LABEL,
    QualityErrorsByPriority,
    QualityErrorType,
)
from quality_result_gui.quality_errors_tree_model import get_error_feature_types


class QualityErrorsTreeFilterMenu(QMenu):
    """
    Menu for filtering rows in feature tree view inside quality errors dialog.

    Menu calls methods of QualityErrorsTreeModel class that apply filters
    to feature tree data model.
    """

    ERROR_TYPE_MENU_NAME = "error_type_filter"
    FEATURE_TYPE_MENU_NAME = "feature_type_filter"
    USER_PROCESSED_MENU_NAME = "user_processed_filter"
    filters_changed = pyqtSignal(set, set, bool)
    _available_feature_types: Set[str]
    _filtered_feature_types: Set[str]
    _filtered_error_types: Set[int]
    _show_user_processed: bool

    def __init__(
        self,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.error_type_filter_menu = self.addMenu(tr("Error type"))
        self.error_type_filter_menu.setObjectName(self.ERROR_TYPE_MENU_NAME)

        self.feature_type_filter_menu = self.addMenu(tr("Feature type"))
        self.feature_type_filter_menu.setObjectName(self.FEATURE_TYPE_MENU_NAME)

        self.user_processed_filter_menu = self.addMenu(tr("User processed"))
        self.user_processed_filter_menu.setObjectName(self.USER_PROCESSED_MENU_NAME)

        self.addSeparator()
        self.addAction(tr("Reset filters")).triggered.connect(self.reset_filters)

        self._filtered_feature_types = set()
        self._available_feature_types = set()
        self._filtered_error_types = {item.value for item in QualityErrorType}
        self._show_user_processed = True
        self.populate_feature_type_filter_menu()
        self.populate_quality_error_type_filter_menu()
        self.populate_user_processed_filter_menu()

    def refresh_feature_type_filters(
        self, quality_errors: List[QualityErrorsByPriority]
    ) -> None:
        self._refresh_feature_type_filter_menu(quality_errors)
        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

    def _refresh_feature_type_filter_menu(
        self, quality_errors: List[QualityErrorsByPriority]
    ) -> None:
        filtered_before_refresh = copy.deepcopy(self._filtered_feature_types)
        new_feature_types = get_error_feature_types(quality_errors)
        added_feature_types = new_feature_types.difference(
            self._available_feature_types
        )
        self._available_feature_types = new_feature_types
        self._filtered_feature_types = self._available_feature_types.intersection(
            filtered_before_refresh
        ).union(added_feature_types)
        self.populate_feature_type_filter_menu()

    def populate_quality_error_type_filter_menu(self) -> None:
        for label, error_type in [
            (description, key) for key, description in ERROR_TYPE_LABEL.items()
        ]:
            action = QAction(label, self.error_type_filter_menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(
                partial(
                    self._set_filtered_error_type,
                    error_type.value,
                )
            )

            self.error_type_filter_menu.addAction(action)

    def populate_feature_type_filter_menu(self) -> None:
        for action in self.feature_type_filter_menu.actions():
            action.deleteLater()
            self.feature_type_filter_menu.removeAction(action)

        select_all_action = QAction(tr("Select all"), self.feature_type_filter_menu)
        select_all_action.triggered.connect(partial(self._select_all_feature_types))

        self.feature_type_filter_menu.addAction(select_all_action)

        deselect_all_action = QAction(tr("Deselect all"), self.feature_type_filter_menu)
        deselect_all_action.triggered.connect(partial(self._deselect_all_feature_types))

        self.feature_type_filter_menu.addAction(deselect_all_action)

        self.feature_type_filter_menu.addSeparator()

        for feature_type in self._available_feature_types:
            # TODO: how to configurate custom data mapping
            # label = common.FEATURE_TYPE_NAMES[feature_type]
            label = feature_type

            action = QAction(label, self.feature_type_filter_menu)
            action.setCheckable(True)
            action.setChecked(feature_type in self._filtered_feature_types)
            action.triggered.connect(
                partial(self._set_filtered_feature_type, feature_type)
            )

            self.feature_type_filter_menu.addAction(action)

    def populate_user_processed_filter_menu(self) -> None:
        action = QAction(USER_PROCESSED_LABEL, self.user_processed_filter_menu)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(partial(self._set_user_processed))

        self.user_processed_filter_menu.addAction(action)

    def _set_filtered_feature_type(self, feature_type: str, selected: bool) -> None:
        if selected is True:
            self._filtered_feature_types.add(feature_type)
        else:
            self._filtered_feature_types.remove(feature_type)

        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

    def _select_all_feature_types(self) -> None:
        filtered_feature_types = copy.deepcopy(self._filtered_feature_types)
        self._filtered_error_types = {item.value for item in QualityErrorType}

        for feature_type in self._available_feature_types:
            if feature_type not in filtered_feature_types:
                self._filtered_feature_types.add(feature_type)

        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

        self.set_menu_items_checked(self.feature_type_filter_menu)

    def _deselect_all_feature_types(self) -> None:
        filtered_feature_types = copy.deepcopy(self._filtered_feature_types)
        self._filtered_error_types = {item.value for item in QualityErrorType}

        for feature_type in filtered_feature_types:
            self._filtered_feature_types.remove(feature_type)

        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

        self.set_menu_items_unchecked(self.feature_type_filter_menu)

    def _set_filtered_error_type(self, error_type: int, selected: bool) -> None:
        if selected is True:
            self._filtered_error_types.add(error_type)
        else:
            self._filtered_error_types.remove(error_type)

        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

    def _set_user_processed(self, selected: bool) -> None:
        self._show_user_processed = selected

        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

    def reset_filters(self) -> None:
        self._filtered_feature_types = copy.deepcopy(self._available_feature_types)
        self._filtered_error_types = {item.value for item in QualityErrorType}
        self._show_user_processed = True
        self.set_menu_items_checked(self.error_type_filter_menu)
        self.set_menu_items_checked(self.feature_type_filter_menu)
        self.set_menu_items_checked(self.user_processed_filter_menu)
        self.filters_changed.emit(
            self._filtered_feature_types,
            self._filtered_error_types,
            self._show_user_processed,
        )

    def is_any_filter_active(self) -> bool:
        return not (
            self.all_menu_items_checked(self.error_type_filter_menu)
            and self.all_menu_items_checked(self.feature_type_filter_menu)
            and self.all_menu_items_checked(self.user_processed_filter_menu)
        )

    @staticmethod
    def set_menu_items_checked(menu: QMenu) -> None:
        for menu_item in menu.children():
            if isinstance(menu_item, QAction) and menu_item.isCheckable():
                menu_item.setChecked(True)

    @staticmethod
    def set_menu_items_unchecked(menu: QMenu) -> None:
        for menu_item in menu.children():
            if isinstance(menu_item, QAction) and menu_item.isCheckable():
                menu_item.setChecked(False)

    @staticmethod
    def all_menu_items_checked(menu: QMenu) -> bool:
        return all(
            not (
                isinstance(menu_item, QAction)
                and menu_item.isCheckable()
                and menu_item.isChecked() is False
            )
            for menu_item in menu.children()
        )
