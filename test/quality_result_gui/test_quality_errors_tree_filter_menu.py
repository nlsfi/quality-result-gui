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

from typing import List, Optional, Set
from unittest.mock import MagicMock

import pytest
from qgis.PyQt.QtWidgets import QAction, QMenu

from quality_result_gui.api.types.quality_error import (
    ERROR_TYPE_LABEL,
    QualityErrorPriority,
    QualityErrorsByFeatureType,
    QualityErrorsByPriority,
    QualityErrorType,
)
from quality_result_gui.quality_errors_tree_filter_menu import (
    QualityErrorsTreeFilterMenu,
)
from quality_result_gui.quality_errors_tree_model import FilterByExtentModel


def _get_submenu_from_menu(menu: QMenu, submenu_title: str) -> Optional[QMenu]:
    menu_items = [
        item
        for item in menu.children()
        if isinstance(item, QMenu) and submenu_title == item.title()
    ]

    if len(menu_items) == 1:
        return menu_items[0]
    return None


def _get_action_from_menu(menu: QMenu, action_title: str) -> Optional[QAction]:
    # Ensure actions are removed

    action_items = [
        item
        for item in menu.children()
        if isinstance(item, QAction) and action_title == item.text()
    ]

    if len(action_items) == 1:
        return action_items[0]
    return None


def _is_submenu_present(menu: QMenu, submenu_title: str) -> bool:
    return bool(_get_submenu_from_menu(menu, submenu_title))


def _is_action_present(menu: QMenu, action_title: str) -> bool:
    return bool(_get_action_from_menu(menu, action_title))


def _trigger_action(menu: QMenu, action_title: str) -> None:
    action = _get_action_from_menu(menu, action_title)
    assert action is not None, f"Could not find action for menu title: {action_title}"
    action.trigger()


@pytest.fixture()
def quality_errors_with_fence():
    return [
        QualityErrorsByPriority(
            QualityErrorPriority.FATAL,
            [
                QualityErrorsByFeatureType("building_part_area", []),
                QualityErrorsByFeatureType("chimney_point", []),
                QualityErrorsByFeatureType("fence", []),
            ],
        )
    ]


@pytest.fixture()
def quality_errors_without_chimney_point():
    return [
        QualityErrorsByPriority(
            QualityErrorPriority.FATAL,
            [
                QualityErrorsByFeatureType("building_part_area", []),
            ],
        )
    ]


@pytest.fixture()
def quality_errors_without_building_part_area():
    return [
        QualityErrorsByPriority(
            QualityErrorPriority.FATAL,
            [
                QualityErrorsByFeatureType("chimney_point", []),
            ],
        )
    ]


@pytest.mark.parametrize(
    "filter_condition_name",
    ["Error type", "Feature type", "User processed"],
    ids=["Error type menu", "Feature type menu", "User processed menu"],
)
def test_three_different_filter_conditions_are_present(
    quality_errors: List[QualityErrorsByPriority], filter_condition_name: str
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)

    assert _is_submenu_present(filter_menu, filter_condition_name)


def test_reset_filters_action_is_present(quality_errors: List[QualityErrorsByPriority]):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)

    assert _is_action_present(filter_menu, "Reset filters")


def test_select_and_deselect_all_actions_are_present(
    quality_errors: List[QualityErrorsByPriority],
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)
    feature_type_filter_menu = _get_submenu_from_menu(filter_menu, "Feature type")

    assert _is_action_present(feature_type_filter_menu, "Deselect all")
    assert _is_action_present(feature_type_filter_menu, "Select all")


def test_reset_filters_action_restores_check_boxes(
    quality_errors: List[QualityErrorsByPriority],
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)

    error_type_filter_menu = _get_submenu_from_menu(filter_menu, "Error type")
    filter_by_attribute_error_action = _get_action_from_menu(
        error_type_filter_menu, ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]
    )
    assert filter_by_attribute_error_action is not None
    assert filter_by_attribute_error_action.isChecked() is True

    feature_type_filter_menu = _get_submenu_from_menu(filter_menu, "Feature type")
    filter_chimneys_action = _get_action_from_menu(
        feature_type_filter_menu, "chimney_point"
    )
    assert filter_chimneys_action is not None
    assert filter_chimneys_action.isChecked() is True

    user_processed_filter_menu = _get_submenu_from_menu(filter_menu, "User processed")
    show_user_processed_action = _get_action_from_menu(
        user_processed_filter_menu, "Show user processed"
    )
    assert show_user_processed_action is not None
    assert show_user_processed_action.isChecked() is True

    # Do selection in error type filter menu (in this test checkbox is toggled to false):
    _trigger_action(
        error_type_filter_menu,
        ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE],
    )
    _trigger_action(
        feature_type_filter_menu,
        "chimney_point",
    )
    _trigger_action(
        user_processed_filter_menu,
        "Show user processed",
    )

    assert filter_by_attribute_error_action.isChecked() is False
    assert filter_chimneys_action.isChecked() is False
    assert show_user_processed_action.isChecked() is False

    # Test reset filter restores checkbox value
    _trigger_action(filter_menu, "Reset filters")

    assert filter_by_attribute_error_action.isChecked() is True
    assert filter_chimneys_action.isChecked() is True
    assert show_user_processed_action.isChecked() is True


def test_deselect_action_unchecks_all(
    quality_errors: List[QualityErrorsByPriority], error_feature_types: Set[str]
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)

    feature_type_filter_menu = _get_submenu_from_menu(filter_menu, "Feature type")

    # As a default, boolean value for all feature types is True
    for feature_type in error_feature_types:
        filter_action = _get_action_from_menu(feature_type_filter_menu, feature_type)
        assert filter_action is not None
        assert filter_action.isChecked() is True

    # Test that clicking Deselect all button nulls all checkbox values
    _trigger_action(feature_type_filter_menu, "Deselect all")

    for feature_type in error_feature_types:
        filter_action = _get_action_from_menu(feature_type_filter_menu, feature_type)
        assert filter_action is not None
        assert filter_action.isChecked() is False


def test_select_action_checks_all(
    quality_errors: List[QualityErrorsByPriority], error_feature_types: Set[str]
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)
    feature_type_filter_menu = _get_submenu_from_menu(filter_menu, "Feature type")

    # After running this function we know that no feature / error type is selected
    test_deselect_action_unchecks_all(quality_errors, error_feature_types)

    # Test that clicking Select all button checks all checkbox values
    _trigger_action(feature_type_filter_menu, "Select all")

    for feature_type in error_feature_types:
        filter_action = _get_action_from_menu(feature_type_filter_menu, feature_type)
        assert filter_action is not None
        assert filter_action.isChecked() is True


@pytest.mark.parametrize(
    (
        "selected_filter_condition",
        "selected_filter_values",
        "expected_feature_types",
        "expected_error_types",
        "expected_user_processed",
    ),
    [
        (
            "Error type",
            [ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]],
            {"building_part_area", "chimney_point"},
            {2, 3},
            True,
        ),
        (
            "Error type",
            [
                ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE],
                ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY],
            ],
            {"building_part_area", "chimney_point"},
            {3},
            True,
        ),
        (
            "Feature type",
            ["chimney_point"],
            {"building_part_area"},
            {1, 2, 3},
            True,
        ),
        (
            "User processed",
            ["Show user processed"],
            {"building_part_area", "chimney_point"},
            {1, 2, 3},
            False,
        ),
    ],
    ids=[
        "Filter out attribute errors",
        "Filter out attribute and geometry errors",
        "Filter out chimney_point",
        "Filter out user processed",
    ],
)
def test_actions_are_connected_to_correct_implementation_methods_and_filters_are_applied(
    quality_errors: List[QualityErrorsByPriority],
    error_feature_types: List[str],
    selected_filter_condition: str,
    selected_filter_values: List[str],
    expected_feature_types: Set[str],
    expected_error_types: Set[int],
    expected_user_processed: bool,
    qtmodeltester,
):
    # Setup:
    model = FilterByExtentModel(None)
    qtmodeltester.check(model)

    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)
    on_filters_changed = MagicMock()
    filter_menu.filters_changed.connect(on_filters_changed)

    # filters_changed has not been sent
    on_filters_changed.assert_not_called()
    # Baseline filters for menu
    assert filter_menu._available_feature_types == error_feature_types
    assert filter_menu._filtered_feature_types == error_feature_types
    assert filter_menu._filtered_error_types == {1, 2, 3}
    assert filter_menu._show_user_processed is True

    # Do selection in menu (in this test checkbox is toggled to false):
    for selected_filter_value in selected_filter_values:
        _trigger_action(
            _get_submenu_from_menu(filter_menu, selected_filter_condition),
            selected_filter_value,
        )

    # Test filter signal is sent:
    on_filters_changed.assert_called_with(
        expected_feature_types, expected_error_types, expected_user_processed
    )

    # Select "Reset filters" from menu
    _trigger_action(filter_menu, "Reset filters")

    # Filters should be back to baseline
    on_filters_changed.assert_called_with(error_feature_types, {1, 2, 3}, True)


@pytest.mark.parametrize(
    (
        "selected_filter_condition",
        "selected_filter_value",
    ),
    [
        ("Error type", ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]),
        ("Feature type", "chimney_point"),
        ("User processed", "Show user processed"),
    ],
    ids=[
        "Filter out attribute errors",
        "Filter out chimney_point",
        "Filter out user processed",
    ],
)
def test_is_any_filter_active_returns_true_all_false_based_on_filter(
    quality_errors: List[QualityErrorsByPriority],
    selected_filter_condition: str,
    selected_filter_value: str,
):
    filter_menu = QualityErrorsTreeFilterMenu()
    filter_menu.refresh_feature_type_filters(quality_errors)

    assert filter_menu.is_any_filter_active() is False

    menu = _get_submenu_from_menu(filter_menu, selected_filter_condition)

    _trigger_action(
        menu,
        selected_filter_value,
    )

    assert filter_menu.is_any_filter_active() is True


@pytest.mark.parametrize(
    (
        "new_errors",
        "expected_feature_type_filters",
        "expected_filters_after_revert",
    ),
    [
        ("quality_errors", {"building_part_area"}, {"building_part_area"}),
        (
            "quality_errors_with_fence",
            {"building_part_area", "fence"},
            {"building_part_area"},
        ),
        (
            "quality_errors_without_chimney_point",
            {"building_part_area"},
            {"chimney_point", "building_part_area"},
        ),
        ("quality_errors_without_building_part_area", set(), {"building_part_area"}),
    ],
    ids=[
        "Refresh with same errors",
        "Refresh with additional errors",
        "Refresh without deselected feature type",
        "Refresh without selected feature type",
    ],
)
def test_filters_are_retained_when_data_changes(
    quality_errors: List[QualityErrorsByPriority],
    new_errors: str,
    expected_feature_type_filters: Set[str],
    expected_filters_after_revert: Set[str],
    request: pytest.FixtureRequest,
):
    filter_menu = QualityErrorsTreeFilterMenu()
    on_filters_changed = MagicMock()
    filter_menu.filters_changed.connect(on_filters_changed)
    filter_menu.refresh_feature_type_filters(quality_errors)
    menu = _get_submenu_from_menu(filter_menu, "Feature type")

    # deselect / filter out chimney_point
    _trigger_action(
        menu,
        "chimney_point",
    )
    on_filters_changed.assert_called_with({"building_part_area"}, {1, 2, 3}, True)

    # update quality errors
    filter_menu.refresh_feature_type_filters(request.getfixturevalue(new_errors))

    on_filters_changed.assert_called_with(
        expected_feature_type_filters, {1, 2, 3}, True
    )

    # revert quality errors back to original value
    filter_menu.refresh_feature_type_filters(quality_errors)

    on_filters_changed.assert_called_with(
        expected_filters_after_revert, {1, 2, 3}, True
    )
