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


import bisect
from abc import abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Hashable, List, Optional, Set, cast

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis_plugin_tools.tools.i18n import tr

from quality_result_gui.api.types.quality_error import ERROR_TYPE_LABEL, QualityError
from quality_result_gui.quality_errors_tree_model import QualityErrorTreeItemType

if TYPE_CHECKING:
    from qgis.PyQt.QtWidgets import QWidget

    from quality_result_gui.api.types.quality_error import QualityErrorsByPriority

FEATURE_TYPE_FILTER_MENU_LABEL = tr("Feature type")
ERROR_TYPE_FILTER_MENU_LABEL = tr("Error type")
ATTRIBUTE_NAME_FILTER_MENU_LABEL = tr("Attribute Filter")
USER_PROCESSED_FILTER_MENU_LABEL = tr("User Processed")


class FilterMenu(QMenu):
    """A QMenu for checkable filter actions with support for select all section and
    sorting"""

    def __init__(self, title: str, parent: Optional["QWidget"] = None) -> None:
        super().__init__(title, parent=parent)

        self._select_all_section_enabled = False
        self._sorted = False

        self._filter_actions: List[QAction] = []

    def set_sorted(self, sorted: bool) -> None:
        """Sets the menu actions in sorted or not sorted order

        Args:
            sorted (bool): If True then menu actions are and will be sorted.
              If False menu actions are not kept sorted anymore.
        """

        if sorted == self._sorted:
            return

        if sorted:
            self._filter_actions.sort(key=lambda action: action.text())
            for action in self._filter_actions:
                self.removeAction(action)
                self.addAction(action)
            self._sorted = True
        else:
            self._sorted = False

    def set_select_all_section_enabled(self, enabled: bool) -> None:
        """Add or removes the (de)select all secion

        Args:
            enabled (bool): If True then the section is added if not present already.
              The section is removed on False.
        """

        if enabled == self._select_all_section_enabled:
            return

        if enabled:
            self._add_select_all_section()
        else:
            self._remove_select_all_section()

    def _add_select_all_section(self) -> None:
        """Add a section to the menu with Select and Deselect all actions

        The section is added always on top of the menu
        """

        if self._select_all_section_enabled:
            return

        select_all_action = QAction(tr("Select all"), self)
        select_all_action.triggered.connect(self._select_all)

        deselect_all_action = QAction(tr("Deselect all"), self)
        deselect_all_action.triggered.connect(self._deselect_all)

        existing_actions = self.actions()
        first_action = existing_actions[0] if existing_actions else None
        separator = self.insertSeparator(first_action)  # type: ignore
        self.insertAction(separator, deselect_all_action)
        self.insertAction(deselect_all_action, select_all_action)

        self._select_all_section_enabled = True

    def _remove_select_all_section(self) -> None:
        """Removes the Select and Deselect all section"""

        if not self._select_all_section_enabled:
            return

        # (de)select all actions are always the first three
        for action in self.actions()[:3]:
            action.deleteLater()
            self.removeAction(action)

        self._select_all_section_enabled = False

    def _select_all(self) -> None:
        """Select all the user added checkable actions"""

        for action in self._filter_actions:
            action.setChecked(True)

    def _deselect_all(self) -> None:
        """Deselects all the user added checkable actions"""

        for action in self._filter_actions:
            action.setChecked(False)

    def remove_user_actions(self) -> None:
        """Removes all the user added actions"""
        for action in self._filter_actions:
            self.remove_filter_action(action)

    def add_checkable_action(self, label: str) -> QAction:
        """Adds a checkable action with a label in to the menu

        Args:
            label (str): Label for the checkbox

        Returns:
            QAction: The generated QAction
        """

        action = QAction(label, parent=self)
        action.setCheckable(True)
        action.setChecked(True)

        if self._sorted:
            insert_index = bisect.bisect_left(
                [action.text() for action in self._filter_actions], label
            )
            try:
                before = self._filter_actions[insert_index]
            except IndexError:
                before = None
        else:
            before = None
            insert_index = len(self._filter_actions)

        self.insertAction(before, action)
        self._filter_actions.insert(insert_index, action)

        return action

    def remove_filter_action(self, action: QAction) -> None:
        """Removes the action from the menu

        Args:
            action (QAction): Action to be removed
        """

        action.deleteLater()
        self.removeAction(action)
        self._filter_actions.remove(action)


class AbstractQualityErrorFilter(QObject):
    """Abstract Base Class for Quality Error Filters

    Attributes:
        menu (QMenu): Bounded QMenu to use as a submenu in QualityErrorsTreeFilterMenu
    """

    filters_changed = pyqtSignal()

    def __init__(self, title: str, parent: Optional[QObject] = None) -> None:
        """Inits a QualityErrorFilter

        Holds a sub menu in the actual QualityErrorsTreeFilterMenu opened by the filter
        button.

        Inherited classes must implement accept_row method that is called by
        filter proxy model.

        self._accepted_values holds current values that are checked by bounded checkable
        actions.

        Args:
            title (str): Label text for the QMenu
            parent (Optional[QObject], optional): QtParent object. Defaults to None.
        """

        super().__init__(parent=parent)
        self._accepted_values: Set[Any] = set()
        self._filter_value_action_map: Dict[Hashable, QAction] = {}

        self.menu = FilterMenu(title)

    @abstractmethod
    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        """The actual filter function that inherited classes should be implemented.

        Args:
            item_type (QualityErrorTreeItemType): Type of the item_value
            item_value (Any): Item to be tested by the filter

        Raises:
            NotImplementedError: Should be implemented by inherited classes

        Returns:
            bool: Is the item accepted by the filter
        """
        raise NotImplementedError()

    def update_filter_from_errors(
        self, quality_errors: List["QualityErrorsByPriority"]
    ) -> None:
        """Updates filters dynamically from a given list of quality errors.

        Should be implemented in inherited classes if feature is wanted.

        Args:
            quality_errors (List[&quot;QualityErrorsByPriority&quot;]): List of errors
              to use to update filters

        Raises:
            NotImplementedError: Should be implemented in inherited classes
        """
        raise NotImplementedError()

    def _sync_filtered(self, value: Any, checked: bool) -> None:
        """Syncs accepted filter values

        Should be connected to checkable action's toggle signal with functool.partial
        where value will be fixed.

        Args:
            value (Any): Value to be added or removed from the accepted value set.
            checked (bool): Is action is checked or not.
        """

        if checked:
            self._accepted_values.add(value)
        else:
            self._accepted_values.remove(value)

        self.filters_changed.emit()

    def _refresh_filters(self, new_filters: Dict[Any, str]) -> None:
        """Adds filters not yet present and removes filters not present anymore.

        Args:
            new_filters (Dict[Any, str]): Filters that should be available after
              the refresh. Dict keys are the filter values and dict values are labels
              for the filters.
        """

        new_values = set(new_filters.keys())
        current_values = set(self._filter_value_action_map.keys())

        values_to_be_added = new_values - current_values
        values_to_be_removed = current_values - new_values

        for filter_value in values_to_be_removed:
            self._remove_filter_item(filter_value)

        for filter_value in values_to_be_added:
            self._add_filter_item(filter_value, new_filters[filter_value])

    def _add_filter_item(self, filter_value: Any, filter_label: str) -> None:
        """Adds a filter item to the filter

        Args:
            filter_value (Any): Value to be used when filtering
            filter_label (str): Label text shown in the menu
        """

        self._accepted_values.add(filter_value)

        action = self.menu.add_checkable_action(filter_label)
        self._filter_value_action_map[filter_value] = action
        action.toggled.connect(partial(self._sync_filtered, filter_value))

        self.filters_changed.emit()

    def _remove_filter_item(self, filter_value: Any) -> None:
        """Removes the filter item

        Args:
            filter_value (Any): The Filter Value that should be removed from the filter
        """

        action = self._filter_value_action_map.pop(filter_value)
        action.deleteLater()
        self.menu.removeAction(action)
        self._accepted_values.remove(filter_value)

        self.filters_changed.emit()


class ErrorTypeFilter(AbstractQualityErrorFilter):
    """Filter for the Error Type of the Quality errors.

    This is a static filter that shows always all the defined error types.
    """

    _accepted_values: Set[QualityErrorTreeItemType]

    def __init__(self) -> None:
        super().__init__(ERROR_TYPE_FILTER_MENU_LABEL)
        self.menu.set_select_all_section_enabled(True)
        self.menu.set_sorted(True)

        self._refresh_filters(ERROR_TYPE_LABEL)

    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        if item_type == QualityErrorTreeItemType.ERROR:
            return cast(QualityError, item_value).error_type in self._accepted_values

        return True


class FeatureTypeFilter(AbstractQualityErrorFilter):
    """Filter for the Feature Type of the Quality errors.

    Adds filterable feature types dynamically based on the current errors received.
    update_filter_from_errors slot should be connected to the signal that transmits
    received errors.
    """

    _accepted_values: Set[str]

    def __init__(self) -> None:
        super().__init__(FEATURE_TYPE_FILTER_MENU_LABEL)
        self.menu.set_select_all_section_enabled(True)
        self.menu.set_sorted(True)

    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        if item_type == QualityErrorTreeItemType.FEATURE_TYPE:
            return cast(str, item_value) in self._accepted_values

        return True

    def update_filter_from_errors(
        self, quality_errors: List["QualityErrorsByPriority"]
    ) -> None:
        """

        Args:
            quality_errors (List[&quot;QualityErrorsByPriority&quot;]): _description_
        """
        feature_types_in_errors = {  # Dict[filter_value, filter_label]
            errors.feature_type: errors.feature_type
            for errors_by_feature_type in quality_errors
            for errors in errors_by_feature_type.errors
        }

        self._refresh_filters(feature_types_in_errors)


class AttributeFilter(AbstractQualityErrorFilter):
    """Filter for the Attribute Errors of the Quality errors.

    Adds filterable Attribute names dynamically based on the current errors received.
    update_filter_from_errors slot should be connected to the signal that transmits
    received errors.
    """

    _accepted_values: Set[str]

    def __init__(self) -> None:
        super().__init__(ATTRIBUTE_NAME_FILTER_MENU_LABEL)
        self.menu.set_select_all_section_enabled(True)
        self.menu.set_sorted(True)

    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        if item_type == QualityErrorTreeItemType.ERROR:
            attribute_name = cast(QualityError, item_value).attribute_name
            if attribute_name:
                return attribute_name in self._accepted_values

        return True

    def update_filter_from_errors(
        self, quality_errors: List["QualityErrorsByPriority"]
    ) -> None:
        attribute_names_in_errors = {  # Dict[filter_value, filter_label]
            error.attribute_name: error.attribute_name
            for errors_by_priority in quality_errors
            for errors_by_feature_type in errors_by_priority.errors
            for errors_by_feature in errors_by_feature_type.errors
            for error in errors_by_feature.errors
            if error.attribute_name
        }

        self._refresh_filters(attribute_names_in_errors)


class UserProcessedFilter(AbstractQualityErrorFilter):
    def __init__(self) -> None:
        super().__init__(USER_PROCESSED_FILTER_MENU_LABEL)

        self._add_filter_item(True, tr("Show user prosessed"))

    def accept_row(self, item_type: QualityErrorTreeItemType, item_value: Any) -> bool:
        if (
            item_type == QualityErrorTreeItemType.ERROR
            and cast(QualityError, item_value).is_user_processed
        ):
            return True in self._accepted_values

        return True
