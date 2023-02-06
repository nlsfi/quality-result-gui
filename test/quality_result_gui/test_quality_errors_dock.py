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

from copy import copy
from typing import Generator, List, Optional
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsLayerTree,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QAbstractItemModel, QCoreApplication, QModelIndex, Qt
from qgis.PyQt.QtWidgets import QAction, QMenu

from quality_result_gui.api.types.quality_error import (
    ERROR_PRIORITY_LABEL,
    ERROR_TYPE_LABEL,
    QualityError,
    QualityErrorPriority,
    QualityErrorsByFeature,
    QualityErrorsByFeatureType,
    QualityErrorsByPriority,
    QualityErrorType,
)
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_error_visualizer import (
    ErrorFeature,
    QualityErrorVisualizer,
)
from quality_result_gui.quality_errors_tree_model import FilterByExtentProxyModel
from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget
from quality_result_gui.ui.quality_errors_tree_filter_menu import (
    QualityErrorsTreeFilterMenu,
)


# index of fatal errors in quality error tree model
def _count_num_fatal_rows(model: QAbstractItemModel) -> int:
    first_index = model.index(0, 0, QModelIndex())
    if first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]:
        return _count_children_rows(model, model.index(0, 0, QModelIndex()))
    else:
        return 0


# index of warnings in quality error tree model
def _count_num_warning_rows(model: QAbstractItemModel) -> int:
    first_index = model.index(0, 0, QModelIndex())
    if first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]:
        return _count_children_rows(model, model.index(1, 0, QModelIndex()))
    elif first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.WARNING]:
        return _count_children_rows(model, model.index(0, 0, QModelIndex()))
    else:
        return 0


def _count_children_rows(model: QAbstractItemModel, priority_index: QModelIndex) -> int:
    if not priority_index.isValid():
        return 0
    num_rows = 0
    for i in range(model.rowCount(priority_index)):
        feature_type_index = priority_index.child(i, 0)
        for j in range(model.rowCount(feature_type_index)):
            num_rows += model.rowCount(feature_type_index.child(j, 0))
    return num_rows


@pytest.fixture()
def quality_errors_dock(
    qgis_new_project: None,
    bypass_log_if_fails: None,
    qtbot: QtBot,
    quality_errors: List[QualityErrorsByPriority],
) -> Generator[QualityErrorsDockWidget, None, None]:

    m_quality_result_client = MagicMock()
    m_quality_result_client.get_results.return_value = quality_errors
    m_quality_result_client.get_crs.return_value = QgsCoordinateReferenceSystem(
        "EPSG:3903"
    )

    quality_errors_dock = QualityErrorsDockWidget(None)
    qtbot.addWidget(quality_errors_dock)

    quality_errors_dock.show()
    quality_errors_dock._fetcher.set_checks_enabled(False)

    yield quality_errors_dock
    quality_errors_dock.close()


@pytest.fixture()
def quality_errors_manager(
    qgis_new_project: None,
    bypass_log_if_fails: None,
    qtbot: QtBot,
    quality_errors: List[QualityErrorsByPriority],
) -> Generator[QualityResultManager, None, None]:

    m_quality_result_client = MagicMock()
    m_quality_result_client.get_results.return_value = quality_errors
    m_quality_result_client.get_crs.return_value = QgsCoordinateReferenceSystem(
        "EPSG:3903"
    )

    manager = QualityResultManager(m_quality_result_client, None)
    qtbot.addWidget(manager.dock_widget)

    # manager.show_dock_widget()

    manager._fetcher.set_checks_enabled(False)

    yield manager
    manager.unload()


@pytest.fixture()
def quality_errors_dock_with_data(
    quality_errors_dock: QualityErrorsDockWidget,
    quality_errors: List[QualityErrorsByPriority],
) -> QualityErrorsDockWidget:
    quality_errors_dock._fetcher.results_received.emit(quality_errors)
    return quality_errors_dock


def assert_tree_view_is_populated(model: QAbstractItemModel) -> None:
    # Count top level nodes (priority categories)
    assert model.rowCount(QModelIndex()) == 2

    priority_1_index = model.index(0, 0, QModelIndex())
    assert priority_1_index.data() == "Fatal"
    priority_2_index = model.index(1, 0, QModelIndex())
    assert priority_2_index.data() == "Warning"

    # priority: fatal -> feature types
    assert model.rowCount(priority_1_index) == 2
    # priority: fatal -> feature type: building -> features
    assert model.rowCount(priority_1_index.child(0, 0)) == 2
    # priority: fatal -> building feature 1 -> errors
    assert model.rowCount(priority_1_index.child(0, 0).child(0, 0)) == 2
    # priority: fatal -> feature type: chimney -> features
    assert model.rowCount(priority_1_index.child(1, 0)) == 1
    # priority: warning -> feature types
    assert model.rowCount(priority_2_index.child(0, 0)) == 1
    # priority: warning -> feature types: building -> features
    assert model.rowCount(priority_2_index.child(0, 0).child(0, 0)) == 1


def _get_action_from_menu(menu: QMenu, action_title: str) -> Optional[QAction]:
    action_items = [
        item
        for item in menu.children()
        if isinstance(item, QAction) and action_title == item.text()
    ]

    if len(action_items) == 1:
        return action_items[0]
    return None


def test_show_quality_errors_dock_should_have_no_information_if_no_quality_errors_present(
    quality_errors_manager: QualityResultManager,
) -> None:
    model = quality_errors_manager.dock_widget.error_tree_view.model()
    root_index = QModelIndex()
    assert model.rowCount(root_index) == 0


def test_show_quality_errors_dock_should_have_rows_with_quality_errors(
    quality_errors_dock_with_data: QualityErrorsDockWidget,
) -> None:
    model = quality_errors_dock_with_data.error_tree_view.model()
    assert_tree_view_is_populated(model)


@pytest.mark.timeout(15)
def test_show_quality_errors_dock_performance_with_big_dataset(
    quality_errors_dock: QualityErrorsDockWidget,
) -> None:
    quality_errors = []
    # Generate 1000+ errors
    for priority in list(QualityErrorPriority):
        feature_type = "test_feature_type"
        feature_type_errors = []
        for id in range(20):
            feature_id = f"a-{id}"
            feature_errors = []
            for i in range(30):
                feature_errors.append(
                    QualityError(
                        priority,
                        feature_type,
                        feature_id,
                        priority.value * 100 + id * 10 + i,
                        str(priority.value * 100 + id * 10 + i),
                        QualityErrorType.ATTRIBUTE,
                        "test_attribute",
                        "desc1",
                        "desc2",
                        "desc3",
                        QgsGeometry.fromWkt("LINESTRING(0 0, 5 5)"),
                        False,
                    )
                )
            feature_type_errors.append(
                QualityErrorsByFeature(feature_type, feature_id, feature_errors)
            )
        quality_errors.append(
            QualityErrorsByPriority(
                priority,
                [QualityErrorsByFeatureType(feature_type, feature_type_errors)],
            )
        )

    quality_errors_dock._fetcher.results_received.emit(quality_errors)
    # Remove all fatal errors
    quality_errors.pop(0)
    quality_errors_dock._fetcher.results_received.emit(quality_errors)


def test_show_quality_errors_dock_updates_view_partially_when_data_is_refreshed(
    quality_errors_dock_with_data: QualityErrorsDockWidget,
    quality_errors: List[QualityErrorsByPriority],
) -> None:
    model = quality_errors_dock_with_data.error_tree_view.model()

    original_quality_errors = copy(quality_errors)
    quality_errors.remove(quality_errors[0])
    quality_errors_dock_with_data._fetcher.results_received.emit(quality_errors)

    first_priority_index = model.index(0, 0, QModelIndex())
    # Count top level nodes (priority categories)
    assert model.rowCount() == 1
    assert first_priority_index.data() == "Warning"
    # num feature types
    assert model.rowCount(first_priority_index) == 1
    # num features for feature types
    assert model.rowCount(first_priority_index.child(0, 0)) == 1
    # num errors for feature
    assert model.rowCount(first_priority_index.child(0, 0).child(0, 0)) == 1

    quality_errors_dock_with_data._fetcher.results_received.emit(
        original_quality_errors
    )
    assert_tree_view_is_populated(model)


@pytest.mark.parametrize(
    ("mouse_button", "should_preserve_scale"),
    [
        (Qt.LeftButton, False),
        (Qt.RightButton, True),
    ],
    ids=[
        "with-left",
        "with-right",
    ],
)
@pytest.mark.parametrize(
    (
        "row_clicked",
        "expected_value",
        "should_zoom_to_feature",
        "expected_annotation_feature_count",
        "should_trigger_selected_signal",
    ),
    [
        # num all errors: 5
        (0, "Fatal", False, 5, False),
        (1, "building_part_area", False, 5, False),
        (2, "123c1e9b", False, 5, False),
        # single errors of feature 123c1e9b
        (3, "Geometry error", True, 5 + 1, True),
        (4, "Attribute error", True, 5 + 1, True),
    ],
    ids=[
        "priority-selected",
        "feature-type-selected",
        "id-selected",
        "geometry-error-selected",
        "attribute-error-selected",
    ],
)
def test_clicking_tree_view_row_zooms_to_feature_if_feature_or_quality_error_selected(  # noqa: QGS105
    quality_errors_dock_with_data: QualityErrorsDockWidget,
    qtbot: QtBot,
    qgis_iface: QgisInterface,
    mouse_button: Qt.MouseButton,
    should_preserve_scale: bool,
    row_clicked: int,
    expected_value: str,
    should_zoom_to_feature: bool,
    expected_annotation_feature_count: int,
    should_trigger_selected_signal: bool,
) -> None:
    qgis_iface.mapCanvas().setExtent(QgsRectangle(100, 100, 200, 200))
    original_extent = qgis_iface.mapCanvas().extent()
    tree = quality_errors_dock_with_data.error_tree_view

    root_index = tree.model().index(0, 0, QModelIndex())
    index_to_select = root_index

    if row_clicked == 1:
        index_to_select = root_index.child(0, 0)
    elif row_clicked == 2:
        index_to_select = root_index.child(0, 0).child(0, 0)
    elif row_clicked == 3:
        index_to_select = root_index.child(0, 0).child(0, 0).child(0, 0)
    elif row_clicked == 4:
        index_to_select = root_index.child(0, 0).child(0, 0).child(1, 0)

    tree.scrollTo(index_to_select)
    item_location = tree.visualRect(index_to_select).center()

    with qtbot.waitSignal(
        quality_errors_dock_with_data.error_tree_view.quality_error_selected,
        timeout=100,
        raising=False,
    ) as item_selected_signal:
        qtbot.mouseClick(tree.viewport(), mouse_button, pos=item_location, delay=50)

        # Sanity check to test that correct row was selected
        assert index_to_select.data() == expected_value

        # Check that zoom function was triggered
        if should_zoom_to_feature is True:
            assert original_extent != qgis_iface.mapCanvas().extent()

            if should_preserve_scale is True:
                assert round(original_extent.area(), 1) == round(
                    qgis_iface.mapCanvas().extent().area(), 1
                )
        else:
            assert original_extent == qgis_iface.mapCanvas().extent()

        quality_layer = (
            quality_errors_dock_with_data.error_tree_view.visualizer._quality_error_layer.find_layer_from_project()
        )
        assert quality_layer is not None
        assert len(quality_layer.items()) == expected_annotation_feature_count

        assert item_selected_signal.signal_triggered == should_trigger_selected_signal


@pytest.mark.parametrize(
    ("extent", "expected_fatal_count", "expected_warning_count"),
    [
        (QgsRectangle(0, 0, 100, 100), 4, 1),
        (QgsRectangle(10, 10, 100, 100), 2, 1),
        (QgsRectangle(30, 30, 100, 100), 0, 1),
    ],
    ids=[
        "All errors within view extent",
        "Feature 123c1e9b outside view extent",
        "Only feature 2b89a0b0 within view extent",
    ],
)
def test_filter_with_map_extent_check_box(  # noqa: QGS105
    qgis_iface: QgisInterface,
    quality_errors_dock_with_data: QualityErrorsDockWidget,
    mocker: MockerFixture,
    extent: QgsRectangle,
    expected_fatal_count: int,
    expected_warning_count: int,
) -> None:
    qgis_iface.mapCanvas().setExtent(QgsRectangle(-1000, -1000, 1000, 1000))
    filter_with_map_extent_check_box = (
        quality_errors_dock_with_data.filter_with_map_extent_check_box
    )
    # use emit as qtbot.mouseClick does not seem to work with CheckBox
    # emit does not change isChecked() state of checkbox, setChecked(True) manually
    filter_with_map_extent_check_box.setChecked(True)
    filter_with_map_extent_check_box.clicked.emit(True)

    model = quality_errors_dock_with_data.error_tree_view.model()

    assert _count_num_fatal_rows(model) == 4
    assert _count_num_warning_rows(model) == 1

    # Mock canvas extent to return exact extent needed in test (as setExtent depends on window size)

    mocker.patch.object(FilterByExtentProxyModel, "_extent", return_value=extent)

    # Test by changing map extent
    qgis_iface.mapCanvas().setExtent(extent)

    assert _count_num_fatal_rows(model) == expected_fatal_count
    assert _count_num_warning_rows(model) == expected_warning_count


def test_show_errors_on_map_check_box_toggles_quality_error_layer_visibility(
    mocker: MockerFixture,
    quality_errors_dock: QualityErrorsDockWidget,
) -> None:
    show_errors_on_map_check_box = quality_errors_dock.show_errors_on_map_check_box

    m_hide_errors = mocker.patch.object(
        QualityErrorVisualizer, "hide_errors", autospec=True
    )
    m_show_errors = mocker.patch.object(
        QualityErrorVisualizer, "show_errors", autospec=True
    )

    assert show_errors_on_map_check_box.isChecked() is True

    # Test hide errors
    show_errors_on_map_check_box.setChecked(False)

    m_hide_errors.assert_called_once()

    # Test show errors
    show_errors_on_map_check_box.setChecked(True)

    m_show_errors.assert_called_once()


def test_changing_model_data_sends_error_geometries_to_visualizer(
    mocker: MockerFixture,
    quality_errors_dock: QualityErrorsDockWidget,
) -> None:
    feature_type = "building_part_area"
    m_add_new_errors = mocker.patch.object(
        QualityErrorVisualizer, "add_new_errors", autospec=True
    )

    quality_errors_dock._fetcher.results_received.emit(
        [
            QualityErrorsByPriority(
                QualityErrorPriority.WARNING,
                [
                    QualityErrorsByFeatureType(
                        feature_type,
                        [
                            QualityErrorsByFeature(
                                feature_type,
                                "123c1e9b-fade-410d-9b7e-f7ad32317883",
                                [
                                    QualityError(
                                        QualityErrorPriority.WARNING,
                                        feature_type,
                                        "123c1e9b-fade-410d-9b7e-f7ad32317883",
                                        1,
                                        "1",
                                        QualityErrorType.ATTRIBUTE,
                                        "test",
                                        "",
                                        "",
                                        "",
                                        QgsGeometry.fromWkt("Point(0 0)"),
                                        False,
                                    ),
                                    QualityError(
                                        QualityErrorPriority.WARNING,
                                        feature_type,
                                        "123c1e9b-fade-410d-9b7e-f7ad32317883",
                                        2,
                                        "2",
                                        QualityErrorType.GEOMETRY,
                                        None,
                                        "",
                                        "",
                                        "",
                                        QgsGeometry.fromWkt("Point(1 1)"),
                                        True,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ]
    )

    assert m_add_new_errors.call_count == 1
    error_features: List[ErrorFeature] = m_add_new_errors.call_args[0][1]
    assert len(error_features) == 2
    assert error_features[0].priority == QualityErrorPriority.WARNING
    assert error_features[0].geometry.isGeosEqual(QgsGeometry.fromWkt("Point(0 0)"))


def test_updating_filter_refreshes_errors_on_tree_view_and_map(
    quality_manager: QualityResultManager,
    quality_errors_dock: QualityErrorsDockWidget,
    quality_errors: List[QualityErrorsByPriority],
) -> None:
    mock_feature = QgsFeature()
    mock_feature.setGeometry(QgsGeometry.fromWkt("Point(1 3)"))

    # Load all quality rules before test -> quality_rules fixture should contain 4 unique mttj_id
    quality_errors_dock._fetcher.results_received.emit(quality_errors)
    quality_layer = (
        quality_errors_dock.visualizer._quality_error_layer.find_layer_from_project()
    )
    assert quality_layer is not None
    assert len(quality_layer.items()) == 5

    # No filter should be active
    assert quality_errors_dock.filter_button.isDown() is False

    # Get filter menu action
    filter_menu = quality_errors_dock.filter_menu
    error_type_filter_menu = filter_menu.findChild(
        QMenu, QualityErrorsTreeFilterMenu.ERROR_TYPE_MENU_NAME
    )

    action_title = ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]
    filter_action = _get_action_from_menu(
        error_type_filter_menu, ERROR_TYPE_LABEL[QualityErrorType.ATTRIBUTE]
    )
    assert (
        filter_action is not None
    ), f"Could not find action for menu title: {action_title}"

    # Test: unselect all attribute errors from filter menu
    # -> 1 geometry error should remain of quality_rules
    filter_action.trigger()

    model = quality_errors_dock.error_tree_view.model()
    root_index = model.index(0, 0, QModelIndex())
    # Check priority is correct -> should only have 1 feature_type
    assert model.data(root_index) == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]
    assert model.rowCount(root_index) == 1

    # Check feature type is correct -> should have 1 feature id
    assert model.data(root_index.child(0, 0)) == "building_part_area"
    assert model.rowCount(root_index.child(0, 0)) == 1

    # Should have 1 feature with 1 geometry error
    assert model.rowCount(root_index.child(0, 0).child(0, 0)) == 1
    assert (
        model.data(root_index.child(0, 0).child(0, 0).child(0, 0))
        == ERROR_TYPE_LABEL[QualityErrorType.GEOMETRY]
    )

    # Test annotation layer contain only 1 feature
    assert len(quality_layer.items()) == 1

    # Test filter button changed
    assert quality_errors_dock.filter_button.isDown() is True


def test_close_event_hides_errors(
    quality_errors_dock: QualityErrorsDockWidget, mocker: MockerFixture
) -> None:
    m_remove_quality_error_layer = mocker.patch.object(
        QualityErrorVisualizer, "remove_quality_error_layer", autospec=True
    )

    quality_errors_dock.close()

    m_remove_quality_error_layer.assert_called_once()


def test_close_and_reopen_does_not_affect_error_visibility(
    quality_errors_dock_with_data: QualityErrorsDockWidget,
) -> None:
    def _check_quality_layer_visibility(expected_visibility: bool) -> None:
        root: QgsLayerTree = QgsProject.instance().layerTreeRoot()
        quality_layer = (
            quality_errors_dock_with_data.error_tree_view.visualizer._quality_error_layer.find_layer_from_project()
        )
        assert quality_layer is not None
        tree_node = root.findLayer(quality_layer.id())
        assert tree_node is not None
        assert tree_node.itemVisibilityChecked() == expected_visibility

    show_errors_on_map_check_box = (
        quality_errors_dock_with_data.show_errors_on_map_check_box
    )
    assert show_errors_on_map_check_box.isChecked() is True
    _check_quality_layer_visibility(True)

    #  Hide errors
    show_errors_on_map_check_box.setChecked(False)
    _check_quality_layer_visibility(False)

    # Close and reopen dialog
    quality_errors_dock_with_data.close()
    quality_errors_dock_with_data.show()

    assert not show_errors_on_map_check_box.isChecked()

    # Check that quality layer is not visible
    _check_quality_layer_visibility(False)


def test_update_filter_menu_icon_state_disables_button_if_no_quality_errors(
    quality_errors_dock: QualityErrorsDockWidget,
) -> None:

    quality_errors_dock._update_filter_menu_icon_state()

    assert quality_errors_dock.filter_button.isEnabled() is False
    assert quality_errors_dock.filter_button.isDown() is False


@pytest.mark.parametrize(
    (
        "filters_active",
        "button_is_down",
    ),
    [
        (True, True),
        (False, False),
    ],
    ids=[
        "Filters active",
        "Filters not active",
    ],
)
def test_update_filter_menu_icon_state_sets_button_up_or_down(
    quality_errors_dock_with_data: QualityErrorsDockWidget,
    mocker: MockerFixture,
    filters_active: bool,
    button_is_down: bool,
) -> None:

    mocker.patch.object(
        QualityErrorsTreeFilterMenu,
        "is_any_filter_active",
        return_value=filters_active,
        autospec=True,
    )

    quality_errors_dock_with_data._update_filter_menu_icon_state()

    assert quality_errors_dock_with_data.filter_button.isEnabled() is True
    assert quality_errors_dock_with_data.filter_button.isDown() is button_is_down


def test_model_reset_expands_error_rows_recursively(
    quality_errors_dock: QualityErrorsDockWidget,
    quality_errors: List[QualityErrorsByPriority],
) -> None:

    quality_errors_dock._fetcher.results_received.emit(quality_errors)

    errors_index = quality_errors_dock.error_tree_view.model().index(
        0, 0, QModelIndex()
    )
    warnigns_index = quality_errors_dock.error_tree_view.model().index(
        1, 0, QModelIndex()
    )

    # expansion is run as queued connection
    QCoreApplication.processEvents()

    # Error title row -> expanded
    assert quality_errors_dock.error_tree_view.isExpanded(errors_index) is True
    # Feature type rows -> expanded
    assert (
        quality_errors_dock.error_tree_view.isExpanded(errors_index.child(0, 0)) is True
    )
    assert (
        quality_errors_dock.error_tree_view.isExpanded(errors_index.child(1, 0)) is True
    )
    # Feature id rows -> expanded
    assert (
        quality_errors_dock.error_tree_view.isExpanded(
            errors_index.child(0, 0).child(0, 0)
        )
        is True
    )
    assert (
        quality_errors_dock.error_tree_view.isExpanded(
            errors_index.child(0, 0).child(1, 0)
        )
        is True
    )
    assert (
        quality_errors_dock.error_tree_view.isExpanded(
            errors_index.child(1, 0).child(0, 0)
        )
        is True
    )

    # Warnings title row and children -> expanded
    assert quality_errors_dock.error_tree_view.isExpanded(warnigns_index) is True
    assert (
        quality_errors_dock.error_tree_view.isExpanded(warnigns_index.child(0, 0))
        is True
    )
    assert (
        quality_errors_dock.error_tree_view.isExpanded(
            warnigns_index.child(0, 0).child(0, 0)
        )
        is True
    )
