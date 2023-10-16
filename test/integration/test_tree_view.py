#  Copyright (C) 2022-2023 National Land Survey of Finland
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

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot
from qgis.core import QgsGeometry, QgsRectangle
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QAbstractItemModel, QCoreApplication, QModelIndex, Qt
from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorPriority,
    QualityErrorType,
)
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_layer import QualityErrorLayer


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


def test_quality_error_tree_view_should_have_no_information_if_no_quality_errors_present(
    quality_result_manager: QualityResultManager,
) -> None:
    model = quality_result_manager.dock_widget.error_tree_view.model()
    root_index = QModelIndex()
    assert model.rowCount(root_index) == 0


def test_quality_error_tree_view_should_have_rows_with_quality_errors(
    quality_result_manager_with_data: QualityResultManager,
) -> None:
    model = quality_result_manager_with_data.dock_widget.error_tree_view.model()
    assert_tree_view_is_populated(model)


@pytest.mark.timeout(15)
def test_quality_error_tree_view_performance_with_big_dataset(
    quality_result_manager_with_data: QualityResultManager,
) -> None:
    quality_errors = []
    # Generate 1000+ errors
    for priority in [1, 2, 3]:
        feature_type = "test_feature_type"
        for id in range(20):
            feature_id = f"a-{id}"
            for i in range(30):
                quality_errors.append(
                    QualityError(
                        QualityErrorPriority(priority),
                        feature_type,
                        feature_id,
                        priority * 100 + id * 10 + i,
                        str(priority * 100 + id * 10 + i),
                        QualityErrorType.ATTRIBUTE,
                        "test_attribute",
                        "desc1",
                        "Extra info",
                        QgsGeometry.fromWkt("LINESTRING(0 0, 5 5)"),
                        False,
                    )
                )

    quality_result_manager_with_data._fetcher.results_received.emit(quality_errors)
    # Remove all fatal errors
    quality_errors.pop(0)
    quality_result_manager_with_data._fetcher.results_received.emit(quality_errors)


def test_quality_error_tree_view_updates_view_partially_when_data_is_refreshed(
    quality_result_manager_with_data: QualityResultManager,
    quality_errors: list[QualityError],
) -> None:
    model = quality_result_manager_with_data.dock_widget.error_tree_view.model()
    original_quality_errors = copy(quality_errors)
    quality_errors = list(
        filter(lambda a: a.priority != QualityErrorPriority.FATAL, quality_errors)
    )
    quality_result_manager_with_data._fetcher.results_received.emit(quality_errors)

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

    quality_result_manager_with_data._fetcher.results_received.emit(
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
def test_clicking_tree_view_row_zooms_to_feature_if_feature_or_quality_error_selected(
    quality_result_manager_with_data: QualityResultManager,
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
    tree = quality_result_manager_with_data.dock_widget.error_tree_view

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
        quality_result_manager_with_data.dock_widget.error_tree_view.quality_error_selected,
        timeout=200,
        # Does not raise if signal is not received -> needed for tests clicking
        # rows that should not do any zooming
        raising=False,
    ) as item_selected_signal:
        qtbot.mouseClick(tree.viewport(), mouse_button, pos=item_location, delay=100)

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
        quality_result_manager_with_data.visualizer._quality_error_layer.find_layer_from_project()
    )
    assert quality_layer is not None
    assert len(quality_layer.items()) == expected_annotation_feature_count

    assert item_selected_signal.signal_triggered == should_trigger_selected_signal


def test_changing_model_data_sends_error_geometries_to_visualizer(
    mocker: MockerFixture,
    quality_result_manager: QualityResultManager,
) -> None:
    feature_type = "building_part_area"
    m_add_or_replace_annotation = mocker.patch.object(
        QualityErrorLayer, "add_or_replace_annotation", autospec=True
    )

    quality_result_manager._fetcher.results_received.emit(
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
                QgsGeometry.fromWkt("Point(1 1)"),
                True,
            ),
        ]
    )

    assert m_add_or_replace_annotation.call_count == 2
    quality_errors: list[QualityError] = [
        call_args[0][1] for call_args in m_add_or_replace_annotation.call_args_list
    ]
    assert len(quality_errors) == 2
    assert quality_errors[0].priority.value == 2
    assert quality_errors[0].geometry.isGeosEqual(QgsGeometry.fromWkt("Point(1 1)"))
    assert quality_errors[1].geometry.isGeosEqual(QgsGeometry.fromWkt("Point(0 0)"))


def test_model_reset_expands_error_rows_recursively_on_tree_view(
    quality_result_manager_with_data: QualityResultManager,
    quality_errors: list[QualityError],
) -> None:
    quality_result_manager_with_data._fetcher.results_received.emit(quality_errors)

    errors_index = (
        quality_result_manager_with_data.dock_widget.error_tree_view.model().index(
            0, 0, QModelIndex()
        )
    )
    warnigns_index = (
        quality_result_manager_with_data.dock_widget.error_tree_view.model().index(
            1, 0, QModelIndex()
        )
    )

    # expansion is run as queued connection
    QCoreApplication.processEvents()

    # Error title row -> expanded
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index
        )
        is True
    )
    # Feature type rows -> expanded
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index.child(0, 0)
        )
        is True
    )
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index.child(1, 0)
        )
        is True
    )
    # Feature id rows -> expanded
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index.child(0, 0).child(0, 0)
        )
        is True
    )
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index.child(0, 0).child(1, 0)
        )
        is True
    )
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            errors_index.child(1, 0).child(0, 0)
        )
        is True
    )

    # Warnings title row and children -> expanded
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            warnigns_index
        )
        is True
    )
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            warnigns_index.child(0, 0)
        )
        is True
    )
    assert (
        quality_result_manager_with_data.dock_widget.error_tree_view.isExpanded(
            warnigns_index.child(0, 0).child(0, 0)
        )
        is True
    )


def test_quality_error_tree_view_with_layer_aliases(
    quality_result_manager_with_data_and_layer_mapping: QualityResultManager,
) -> None:
    model = (
        quality_result_manager_with_data_and_layer_mapping.dock_widget.error_tree_view.model()
    )
    first_priority_index = model.index(0, 0, QModelIndex())
    feature_type = first_priority_index.child(1, 0).data()
    assert feature_type == "chimney point alias"
