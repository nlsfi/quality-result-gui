#  Copyright (C) 2023 National Land Survey of Finland
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

from typing import Callable, Optional

import pytest
from pytestqt.qtbot import QtBot
from qgis.core import QgsFeature, QgsGeometry
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtWidgets import QAction, QMenu
from quality_result_gui.api.types.quality_error import (
    ERROR_PRIORITY_LABEL,
    ERROR_TYPE_LABEL,
    QualityError,
    QualityErrorPriority,
    QualityErrorType,
)
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_errors_filters import (
    AttributeFilter,
    ErrorTypeFilter,
    FeatureTypeFilter,
)
from quality_result_gui.ui.quality_errors_tree_filter_menu import (
    QualityErrorsTreeFilterMenu,
)


@pytest.fixture()
def filter_menu(
    quality_result_manager_with_data: QualityResultManager,
) -> QualityErrorsTreeFilterMenu:
    return quality_result_manager_with_data.dock_widget.filter_menu


@pytest.fixture()
def error_type_menu(
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    filter_menu: QualityErrorsTreeFilterMenu,
) -> QMenu:
    menu = get_submenu_from_menu(
        filter_menu, ErrorTypeFilter.get_error_type_filter_menu_label()
    )
    assert menu is not None
    return menu


@pytest.fixture()
def feature_type_menu(
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    filter_menu: QualityErrorsTreeFilterMenu,
) -> QMenu:
    menu = get_submenu_from_menu(
        filter_menu,
        FeatureTypeFilter.get_feature_type_filter_menu_label(),
    )
    assert menu is not None
    return menu


@pytest.fixture()
def attribute_menu(
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    filter_menu: QualityErrorsTreeFilterMenu,
) -> QMenu:
    menu = get_submenu_from_menu(
        filter_menu,
        AttributeFilter.get_attribute_name_filter_menu_label(),
    )
    assert menu is not None
    return menu


@pytest.fixture()
def quality_errors_with_fence() -> list[QualityError]:
    return [
        QualityError(
            QualityErrorPriority.FATAL,
            "building_part_area",
            "aa-bbb-cc-1",
            5,
            "5",
            QualityErrorType.GEOMETRY,
            None,
            "Invalid geometry",
            "Extra info",
            QgsGeometry.fromWkt("POINT ((5 5))"),
            False,
        ),
        QualityError(
            QualityErrorPriority.FATAL,
            "chimney_point",
            "aa-bbb-cc-2",
            6,
            "6",
            QualityErrorType.GEOMETRY,
            None,
            "Invalid geometry",
            "Extra info",
            QgsGeometry.fromWkt("POLYGON((20 20, 20 25, 25 25, 25 20, 20 20))"),
            False,
        ),
        QualityError(
            QualityErrorPriority.FATAL,
            "fence",
            "aa-bbb-cc-3",
            7,
            "7",
            QualityErrorType.GEOMETRY,
            None,
            "Invalid geometry",
            "Extra info",
            QgsGeometry.fromWkt("POINT ((5 5))"),
            False,
        ),
    ]


@pytest.fixture()
def quality_errors_without_chimney_point() -> list[QualityError]:
    return [
        QualityError(
            QualityErrorPriority.FATAL,
            "building_part_area",
            "123c1e9b-fade-410d-9b7e-f7ad32317883",
            1,
            "1",
            QualityErrorType.GEOMETRY,
            None,
            "Invalid geometry",
            "Extra info",
            QgsGeometry.fromWkt("POINT ((5 5))"),
            False,
        ),
        QualityError(
            QualityErrorPriority.FATAL,
            "building_part_area",
            "123c1e9b-fade-410d-9b7e-f7ad32317883",
            2,
            "2",
            QualityErrorType.ATTRIBUTE,
            "vtj_prt",
            "Invalid value",
            "Extra info",
            QgsGeometry.fromWkt("POLYGON((0 0, 0 5, 5 5, 5 0, 0 0))"),
            True,
        ),
    ]


@pytest.fixture()
def quality_errors_without_building_part_area() -> list[QualityError]:
    return [
        QualityError(
            QualityErrorPriority.FATAL,
            "chimney_point",
            "7067408f-e7ff-4be4-9def-fe17e9b6bdb2",
            4,
            "4",
            QualityErrorType.ATTRIBUTE,
            "height_relative",
            "Invalid value",
            "Extra info",
            QgsGeometry.fromWkt("POLYGON((20 20, 20 25, 25 25, 25 20, 20 20))"),
            False,
        )
    ]


def test_select_and_deselect_all_actions_are_present(
    filter_menu: QualityErrorsTreeFilterMenu,
    is_action_present: Callable[[QMenu, str], bool],
):
    for action in filter_menu.actions():
        if action.menu() is not None:
            assert is_action_present(
                action.menu(), "Deselect all"
            ), f"Did not find option from menu {action.menu().title()}"
            assert is_action_present(
                action.menu(), "Select all"
            ), f"Did not find option from menu {action.menu().title()}"


def test_reset_filters_action_restores_check_boxes(
    error_type_menu: QMenu,
    feature_type_menu: QMenu,
    attribute_menu: QMenu,
    get_action_from_menu: Callable[[QMenu, str], Optional[QAction]],
    trigger_action: Callable[[QMenu, str], None],
    filter_menu: QualityErrorsTreeFilterMenu,
):
    filter_by_attribute_error_action = get_action_from_menu(
        error_type_menu, ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]()
    )
    assert filter_by_attribute_error_action is not None
    assert filter_by_attribute_error_action.isChecked() is True

    filter_chimneys_action = get_action_from_menu(feature_type_menu, "chimney_point")
    assert filter_chimneys_action is not None
    assert filter_chimneys_action.isChecked() is True

    filter_height_absolute_action = get_action_from_menu(
        attribute_menu, "height_absolute"
    )
    assert filter_height_absolute_action is not None
    assert filter_height_absolute_action.isChecked() is True

    # Do selection in error type filter menu (in this test checkbox is toggled to false):
    trigger_action(
        error_type_menu,
        ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
    )
    trigger_action(
        feature_type_menu,
        "chimney_point",
    )
    trigger_action(
        attribute_menu,
        "height_absolute",
    )

    assert filter_by_attribute_error_action.isChecked() is False
    assert filter_chimneys_action.isChecked() is False
    assert filter_height_absolute_action.isChecked() is False

    # Test reset filter restores checkbox value
    trigger_action(filter_menu, "Reset filters")

    assert filter_by_attribute_error_action.isChecked() is True
    assert filter_chimneys_action.isChecked() is True
    assert filter_height_absolute_action.isChecked() is True


@pytest.mark.parametrize(
    (
        "selected_filter_condition",
        "selected_filter_values",
        "expected_feature_types",
        "expected_error_types",
        "expected_feature_attributes",
    ),
    [
        (
            ErrorTypeFilter.get_error_type_filter_menu_label(),
            [ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]()],
            ["building_part_area", "chimney_point"],
            [
                ERROR_TYPE_LABEL[QualityErrorType.CONTINUITY](),
                ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY](),
                ERROR_TYPE_LABEL[QualityErrorType.TOPOLOGY](),
            ],
            [
                "floors_above_ground",
                "height_absolute",
                "height_relative",
                "vtj_prt",
            ],
        ),
        (
            ErrorTypeFilter.get_error_type_filter_menu_label(),
            [
                ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
                ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY](),
            ],
            ["building_part_area", "chimney_point"],
            [
                ERROR_TYPE_LABEL[QualityErrorType.CONTINUITY](),
                ERROR_TYPE_LABEL[QualityErrorType.TOPOLOGY](),
            ],
            [
                "floors_above_ground",
                "height_absolute",
                "height_relative",
                "vtj_prt",
            ],
        ),
        (
            FeatureTypeFilter.get_feature_type_filter_menu_label(),
            ["chimney_point"],
            ["building_part_area"],
            [
                ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
                ERROR_TYPE_LABEL[QualityErrorType.CONTINUITY](),
                ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY](),
                ERROR_TYPE_LABEL[QualityErrorType.TOPOLOGY](),
            ],
            [
                "floors_above_ground",
                "height_absolute",
                "height_relative",
                "vtj_prt",
            ],
        ),
        (
            AttributeFilter.get_attribute_name_filter_menu_label(),
            ["height_relative"],
            ["building_part_area", "chimney_point"],
            [
                ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
                ERROR_TYPE_LABEL[QualityErrorType.CONTINUITY](),
                ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY](),
                ERROR_TYPE_LABEL[QualityErrorType.TOPOLOGY](),
            ],
            ["floors_above_ground", "height_absolute", "vtj_prt"],
        ),
    ],
    ids=[
        "Filter out attribute errors",
        "Filter out attribute and geometry errors",
        "Filter out chimney_point",
        "Filter out height_relative",
    ],
)
def test_actions_are_connected_to_correct_implementation_methods_and_filters_are_applied(
    get_checked_menu_items: Callable[[QMenu], list[str]],
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    trigger_action: Callable[[QMenu, str], None],
    error_type_menu: QMenu,
    feature_type_menu: QMenu,
    attribute_menu: QMenu,
    filter_menu: QualityErrorsTreeFilterMenu,
    error_feature_types: list[str],
    error_feature_attributes: list[str],
    selected_filter_condition: str,
    selected_filter_values: list[str],
    expected_feature_types: list[str],
    expected_feature_attributes: list[str],
    expected_error_types: list[int],
):
    # Baseline filters for menu
    labels = []
    for error_type_label in ERROR_TYPE_LABEL.values():
        labels.append(error_type_label())
    assert get_checked_menu_items(error_type_menu) == sorted(labels)
    assert get_checked_menu_items(feature_type_menu) == error_feature_types
    assert get_checked_menu_items(attribute_menu) == error_feature_attributes

    # Do selection in menu (in this test checkbox is toggled to false):
    for selected_filter_value in selected_filter_values:
        trigger_action(
            get_submenu_from_menu(filter_menu, selected_filter_condition),
            selected_filter_value,
        )

    # Test filters are updated
    assert get_checked_menu_items(error_type_menu) == expected_error_types
    assert get_checked_menu_items(feature_type_menu) == expected_feature_types
    assert get_checked_menu_items(attribute_menu) == expected_feature_attributes

    # Select "Reset filters" from menu
    trigger_action(filter_menu, "Reset filters")

    # Filters should be back to baseline
    labels = []
    for error_type_label in ERROR_TYPE_LABEL.values():
        labels.append(error_type_label())
    assert get_checked_menu_items(error_type_menu) == sorted(labels)
    assert get_checked_menu_items(feature_type_menu) == error_feature_types
    assert get_checked_menu_items(attribute_menu) == error_feature_attributes


@pytest.mark.parametrize(
    (
        "selected_filter_condition",
        "selected_filter_value",
    ),
    [
        (
            ErrorTypeFilter.get_error_type_filter_menu_label(),
            ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
        ),
        (
            FeatureTypeFilter.get_feature_type_filter_menu_label(),
            "chimney_point",
        ),
        (
            AttributeFilter.get_attribute_name_filter_menu_label(),
            "height_relative",
        ),
    ],
    ids=[
        "Filter out attribute errors",
        "Filter out chimney_point",
        "Filter out height_relative",
    ],
)
def test_is_any_filter_active_returns_true_all_false_based_on_filter(
    filter_menu: QualityErrorsTreeFilterMenu,
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    trigger_action: Callable[[QMenu, str], None],
    selected_filter_condition: str,
    selected_filter_value: str,
):
    assert filter_menu.is_any_filter_active() is False

    menu = get_submenu_from_menu(filter_menu, selected_filter_condition)

    trigger_action(
        menu,
        selected_filter_value,
    )

    assert filter_menu.is_any_filter_active() is True


@pytest.mark.parametrize(
    (
        "new_errors",
        "should_send_data_changed_signal",
        "expected_feature_type_filter_options",
        "expected_attribute_filter_options",
        "expected_feature_type_filter_options_after_revert",
        "expected_attribute_filter_options_after_revert",
    ),
    [
        (
            "quality_errors",
            False,
            ["building_part_area"],
            ["floors_above_ground", "height_absolute", "vtj_prt"],
            ["building_part_area"],
            ["floors_above_ground", "height_absolute", "vtj_prt"],
        ),
        (
            "quality_errors_with_fence",
            True,
            ["building_part_area", "fence"],
            [],
            ["building_part_area"],
            [
                "floors_above_ground",
                "height_absolute",
                "height_relative",
                "vtj_prt",
            ],
        ),
        (
            "quality_errors_without_chimney_point",
            True,
            ["building_part_area"],
            ["vtj_prt"],
            ["building_part_area", "chimney_point"],
            [
                "floors_above_ground",
                "height_absolute",
                "height_relative",
                "vtj_prt",
            ],
        ),
        (
            "quality_errors_without_building_part_area",
            True,
            [],
            [],
            ["building_part_area"],
            ["floors_above_ground", "height_absolute", "vtj_prt"],
        ),
    ],
    ids=[
        "Refresh with same errors",
        "Refresh with additional errors",
        "Refresh without deselected feature type",
        "Refresh without selected feature type",
    ],
)
def test_filters_are_retained_when_data_changes(
    qtbot: QtBot,
    quality_errors: list[QualityError],
    error_feature_types: list[str],
    error_feature_attributes: list[str],
    quality_result_manager_with_data: QualityResultManager,
    get_checked_menu_items: Callable[[QMenu], list[str]],
    trigger_action: Callable[[QMenu, str], None],
    feature_type_menu: QMenu,
    attribute_menu: QMenu,
    new_errors: str,
    should_send_data_changed_signal: bool,
    expected_feature_type_filter_options: list[str],
    expected_feature_type_filter_options_after_revert: list[str],
    expected_attribute_filter_options: list[str],
    expected_attribute_filter_options_after_revert: list[str],
    request: pytest.FixtureRequest,
):
    assert get_checked_menu_items(feature_type_menu) == error_feature_types
    assert get_checked_menu_items(attribute_menu) == error_feature_attributes

    # deselect / filter out chimney_point & height_relative
    trigger_action(
        feature_type_menu,
        "chimney_point",
    )
    trigger_action(
        attribute_menu,
        "height_relative",
    )

    # update quality errors
    with qtbot.waitSignal(
        quality_result_manager_with_data._base_model.filterable_data_changed,
        timeout=200,
        raising=should_send_data_changed_signal,
    ) as _:
        quality_result_manager_with_data._fetcher.results_received.emit(
            request.getfixturevalue(new_errors)
        )

    assert (
        get_checked_menu_items(feature_type_menu)
        == expected_feature_type_filter_options
    )
    assert get_checked_menu_items(attribute_menu) == expected_attribute_filter_options

    # revert quality errors back to original value
    with qtbot.waitSignal(
        quality_result_manager_with_data._base_model.filterable_data_changed,
        timeout=200,
        raising=should_send_data_changed_signal,
    ) as _:
        quality_result_manager_with_data._fetcher.results_received.emit(quality_errors)

    assert (
        get_checked_menu_items(feature_type_menu)
        == expected_feature_type_filter_options_after_revert
    )
    assert (
        get_checked_menu_items(attribute_menu)
        == expected_attribute_filter_options_after_revert
    )


def test_updating_filter_refreshes_errors_on_tree_view_and_map(
    quality_result_manager_with_data: QualityResultManager,
    filter_menu: QualityErrorsTreeFilterMenu,
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
    trigger_action: Callable[[QMenu, str], None],
) -> None:
    mock_feature = QgsFeature()
    mock_feature.setGeometry(QgsGeometry.fromWkt("Point(1 3)"))

    quality_layer = (
        quality_result_manager_with_data.visualizer._quality_error_layer.get_annotation_layer()
    )
    assert quality_layer is not None
    assert len(quality_layer.items()) == 5

    # No filter should be active
    assert quality_result_manager_with_data.dock_widget.filter_button.isDown() is False

    # Test: unselect all attribute errors from filter menu
    # -> 1 geometry error should remain of quality_rules
    error_type_menu = get_submenu_from_menu(
        filter_menu, ErrorTypeFilter.get_error_type_filter_menu_label()
    )
    trigger_action(
        error_type_menu,
        ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE](),
    )

    model = quality_result_manager_with_data.dock_widget.error_tree_view.model()
    root_index = model.index(0, 0, QModelIndex())
    # Check priority is correct -> should only have 1 feature_type
    assert model.data(root_index) == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]()
    assert model.rowCount(root_index) == 1

    # Check feature type is correct -> should have 1 feature id
    assert model.data(root_index.child(0, 0)) == "building_part_area"
    assert model.rowCount(root_index.child(0, 0)) == 1

    # Should have 1 feature with 1 geometry error
    assert model.rowCount(root_index.child(0, 0).child(0, 0)) == 1
    assert (
        model.data(root_index.child(0, 0).child(0, 0).child(0, 0))
        == ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY]()
    )

    # Test annotation layer contain only 1 feature
    assert len(quality_layer.items()) == 1

    # Test filter button changed
    assert quality_result_manager_with_data.dock_widget.filter_button.isDown() is True


def test_filter_menu_label_aliases(
    filter_menu_with_chimney_point_alias: QualityErrorsTreeFilterMenu,
    get_submenu_from_menu: Callable[[QMenu, str], Optional[QMenu]],
):
    feature_type_menu = get_submenu_from_menu(
        filter_menu_with_chimney_point_alias,
        FeatureTypeFilter.get_feature_type_filter_menu_label(),
    )
    attribute_type_menu = get_submenu_from_menu(
        filter_menu_with_chimney_point_alias,
        AttributeFilter.get_attribute_name_filter_menu_label(),
    )
    feature_type_menu = get_submenu_from_menu(
        filter_menu_with_chimney_point_alias,
        FeatureTypeFilter.get_feature_type_filter_menu_label(),
    )

    assert feature_type_menu is not None
    assert attribute_type_menu is not None
    assert "chimney point alias" in [
        action.text() for action in feature_type_menu.actions()
    ]
    assert "height relative alias" in [
        action.text() for action in attribute_type_menu.actions()
    ]
