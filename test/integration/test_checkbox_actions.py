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

import pytest
from pytest_mock import MockerFixture
from qgis.core import QgsRectangle
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex
from quality_result_gui.api.types.quality_error import (
    ERROR_PRIORITY_LABEL,
    QualityErrorPriority,
)
from quality_result_gui.quality_error_manager import QualityResultManager
from quality_result_gui.quality_error_visualizer import QualityErrorVisualizer


# index of fatal errors in quality error tree model
def _count_num_fatal_rows(model: QAbstractItemModel) -> int:
    first_index = model.index(0, 0, QModelIndex())
    if first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]():
        return _count_children_rows(model, model.index(0, 0, QModelIndex()))
    else:
        return 0


# index of warnings in quality error tree model
def _count_num_warning_rows(model: QAbstractItemModel) -> int:
    first_index = model.index(0, 0, QModelIndex())
    if first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.FATAL]():
        return _count_children_rows(model, model.index(1, 0, QModelIndex()))
    elif first_index.data() == ERROR_PRIORITY_LABEL[QualityErrorPriority.WARNING]():
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
def test_filter_with_map_extent_check_box(
    qgis_iface: QgisInterface,
    quality_result_manager_with_data: QualityResultManager,
    mocker: MockerFixture,
    extent: QgsRectangle,
    expected_fatal_count: int,
    expected_warning_count: int,
) -> None:
    qgis_iface.mapCanvas().setExtent(QgsRectangle(-1000, -1000, 1000, 1000))
    quality_result_manager_with_data.dock_widget.filter_with_map_extent_check_box.setChecked(
        True
    )

    model = quality_result_manager_with_data.dock_widget.error_tree_view.model()

    assert _count_num_fatal_rows(model) == 4
    assert _count_num_warning_rows(model) == 1

    # Mock canvas extent to return exact extent needed in test (as setExtent depends on window size)
    mocker.patch.object(
        quality_result_manager_with_data._filter_map_extent_model,
        "_extent",
        return_value=extent,
    )
    # Test by changing map extent
    qgis_iface.mapCanvas().setExtent(extent)

    assert _count_num_fatal_rows(model) == expected_fatal_count
    assert _count_num_warning_rows(model) == expected_warning_count


def test_filter_with_user_processed_check_box(
    quality_result_manager_with_data: QualityResultManager,
) -> None:
    quality_result_manager_with_data.dock_widget.show_user_processed_errors_check_box.setChecked(
        True
    )

    model = quality_result_manager_with_data.dock_widget.error_tree_view.model()

    assert _count_num_fatal_rows(model) == 4
    assert _count_num_warning_rows(model) == 1

    quality_result_manager_with_data.dock_widget.show_user_processed_errors_check_box.setChecked(
        False
    )

    assert _count_num_fatal_rows(model) == 3
    assert _count_num_warning_rows(model) == 1


def test_show_errors_on_map_check_box_toggles_quality_error_layer_visibility(
    mocker: MockerFixture,
    quality_result_manager_with_data: QualityResultManager,
) -> None:
    show_errors_on_map_check_box = (
        quality_result_manager_with_data.dock_widget.show_errors_on_map_check_box
    )

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
