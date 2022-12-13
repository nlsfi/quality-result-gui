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

from typing import Dict, List, Set
from unittest.mock import MagicMock

import pytest
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant

from quality_result_gui.api.types.quality_error import (
    QualityErrorsByPriority,
    QualityErrorType,
)
from quality_result_gui.quality_errors_tree_model import (
    FilterByExtentModel,
    FilterByMenuModel,
    QualityErrorIdentityProxyModel,
    QualityErrorsTreeBaseModel,
    get_error_feature_types,
)


def _feature_type_filters(quality_errors: List[QualityErrorsByPriority]) -> Set[str]:
    return get_error_feature_types(quality_errors)


def _error_type_filters() -> Set[int]:
    return {item.value for item in QualityErrorType}


def _reset_filters(
    model: FilterByExtentModel, quality_errors: List[QualityErrorsByPriority]
) -> None:
    model.sourceModel().update_filters(
        _feature_type_filters(quality_errors), _error_type_filters(), True
    )


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


def _priority_1_index(model) -> QModelIndex:
    return model.index(0, 0, QModelIndex())


def _priority_2_index(model) -> QModelIndex:
    return model.index(1, 0, QModelIndex())


def _priority_1_feature_type_1_index(model) -> QModelIndex:
    return model.index(0, 0, _priority_1_index(model))


def _priority_1_feature_type_2_index(model) -> QModelIndex:
    return model.index(1, 0, _priority_1_index(model))


def _priority_1_feature_type_1_feature_1_index(model) -> QModelIndex:
    return model.index(0, 0, _priority_1_feature_type_1_index(model))


def _priority_1_feature_type_1_feature_2_index(model) -> QModelIndex:
    return model.index(1, 0, _priority_1_feature_type_1_index(model))


def _priority_1_feature_type_1_feature_1_error_1_index(model) -> QModelIndex:
    return model.index(0, 0, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_2_index(model) -> QModelIndex:
    return model.index(1, 0, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_1_description_index(
    model,
) -> QModelIndex:
    return model.index(0, 1, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_2_description_index(
    model,
) -> QModelIndex:
    return model.index(1, 1, _priority_1_feature_type_1_feature_1_index(model))


@pytest.fixture()
def m_user_processed_callback():
    return MagicMock()


@pytest.fixture()
def model(quality_errors, qtmodeltester, m_user_processed_callback):
    base_model = QualityErrorsTreeBaseModel(None, m_user_processed_callback)
    styled_model = QualityErrorIdentityProxyModel(None)
    styled_model.setSourceModel(base_model)
    menu_model = FilterByMenuModel(None)
    menu_model.setSourceModel(styled_model)
    menu_model.update_filters({"building_part_area", "chimney_point"}, {1, 2, 3}, True)
    extent_model = FilterByExtentModel(None)
    extent_model.setSourceModel(menu_model)
    base_model.refresh_model(quality_errors)
    return extent_model
    # TODO: skip for now, fix errors in MATI-1722 or split new issue
    # if actual crashes on reload are not related to errors revealed by checker
    # qtmodeltester.check(filter_model)
    # model = filter_model.sourceModel()
    # qtmodeltester.check(model)
    # return model


def test_model_index(model: FilterByExtentModel):
    priority_1_index = _priority_1_index(model)
    assert priority_1_index.isValid()

    priority_1_feature_type_1_index = _priority_1_feature_type_1_index(model)
    assert priority_1_feature_type_1_index.isValid()

    priority_1_feature_type_1_feature_1_index = (
        _priority_1_feature_type_1_feature_1_index(model)
    )
    assert priority_1_feature_type_1_feature_1_index.isValid()

    priority_1_feature_type_1_feature_1_error_1_index = (
        _priority_1_feature_type_1_feature_1_error_1_index(model)
    )
    assert priority_1_feature_type_1_feature_1_error_1_index.isValid()

    priority_1_feature_type_1_feature_1_error_1_description_index = (
        _priority_1_feature_type_1_feature_1_error_1_description_index(model)
    )
    assert priority_1_feature_type_1_feature_1_error_1_description_index.isValid()

    nonexistent_priority_index = model.index(99, 0, QModelIndex())
    assert not nonexistent_priority_index.isValid()

    nonexistent_feature_type_index = model.index(99, 0, _priority_1_index(model))
    assert not nonexistent_feature_type_index.isValid()

    nonexistent_feature_index = model.index(
        99, 0, _priority_1_feature_type_1_index(model)
    )
    assert not nonexistent_feature_index.isValid()

    nonexistent_error_index = model.index(
        99, 0, _priority_1_feature_type_1_feature_1_index(model)
    )
    assert not nonexistent_error_index.isValid()


def test_model_parent(model: FilterByExtentModel):
    assert not model.parent(QModelIndex()).isValid()

    priority_1_index = _priority_1_index(model)
    assert not model.parent(priority_1_index).isValid()

    priority_1_feature_type_1_index = _priority_1_feature_type_1_index(model)
    assert model.parent(priority_1_feature_type_1_index) == priority_1_index

    priority_1_feature_type_1_feature_1_index = (
        _priority_1_feature_type_1_feature_1_index(model)
    )
    assert (
        model.parent(priority_1_feature_type_1_feature_1_index)
        == priority_1_feature_type_1_index
    )

    assert (
        model.parent(_priority_1_feature_type_1_feature_1_error_1_index(model))
        == priority_1_feature_type_1_feature_1_index
    )
    assert (
        model.parent(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == priority_1_feature_type_1_feature_1_index
    )


def test_model_row_count(model: FilterByExtentModel):
    assert model.rowCount(QModelIndex()) == 2
    assert model.rowCount(_priority_1_index(model)) == 2
    assert model.rowCount(_priority_1_feature_type_1_index(model)) == 2
    assert model.rowCount(_priority_1_feature_type_1_feature_1_index(model)) == 2
    assert (
        model.rowCount(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == 0
    )


def test_model_column_count(model: FilterByExtentModel):
    assert model.columnCount(QModelIndex()) == 2
    assert (
        model.columnCount(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == 2
    )


def test_model_header_data(model: FilterByExtentModel):
    assert not QVariant(model.headerData(0, Qt.Vertical)).isValid()
    assert QVariant(model.headerData(0, Qt.Horizontal)).isValid()

    for valid_col_index in [0, 1]:
        assert QVariant(model.headerData(valid_col_index, Qt.Horizontal)).isValid()

    for invalid_col_index in [-1, 2, 3, 4, 5, 10, 99]:
        assert not QVariant(
            model.headerData(invalid_col_index, Qt.Horizontal)
        ).isValid()


def test_total_number_of_errors_is_shown_in_header(
    model: FilterByExtentModel, quality_errors: List[QualityErrorsByPriority]
):
    assert "5/5" in model.headerData(0, Qt.Horizontal).value()

    error_type_filters = _error_type_filters()
    error_type_filters.remove(2)
    model.sourceModel().update_filters(
        _feature_type_filters(quality_errors), error_type_filters, True
    )
    assert "4/5" in model.headerData(0, Qt.Horizontal).value()

    _reset_filters(model, quality_errors)
    feature_type_filters = _feature_type_filters(quality_errors)
    feature_type_filters.remove("building_part_area")
    model.sourceModel().update_filters(
        feature_type_filters, _error_type_filters(), True
    )
    assert "1/5" in model.headerData(0, Qt.Horizontal).value()


def test_model_data_invalid_index(model: FilterByExtentModel):
    assert not QVariant(model.data(QModelIndex())).isValid()


def test_model_data_priority(model: FilterByExtentModel):
    assert model.data(_priority_1_index(model)) == "Fatal"
    assert _count_quality_error_rows(model, _priority_1_index(model)) == 4
    assert not QVariant(model.data(model.index(0, 2, QModelIndex()))).isValid()

    assert model.data(_priority_2_index(model)) == "Warning"
    assert _count_quality_error_rows(model, _priority_2_index(model)) == 1


def test_model_data_feature_type(model: FilterByExtentModel):
    assert model.data(_priority_1_feature_type_1_index(model)) == "building_part_area"
    assert (
        _count_quality_error_rows(model, _priority_1_feature_type_1_index(model)) == 3
    )
    assert not QVariant(model.data(model.index(0, 2, QModelIndex()))).isValid()

    assert model.data(_priority_1_feature_type_2_index(model)) == "chimney_point"
    assert (
        _count_quality_error_rows(model, _priority_1_feature_type_2_index(model)) == 1
    )


def test_model_data_feature(model: FilterByExtentModel):
    assert model.data(_priority_1_feature_type_1_feature_1_index(model)) == "123c1e9b"
    assert (
        _count_quality_error_rows(
            model, _priority_1_feature_type_1_feature_1_index(model)
        )
        == 2
    )
    assert not QVariant(model.data(model.index(0, 2, QModelIndex()))).isValid()

    assert model.data(_priority_1_feature_type_1_feature_2_index(model)) == "604eb499"
    assert (
        _count_quality_error_rows(
            model, _priority_1_feature_type_1_feature_2_index(model)
        )
        == 1
    )


def test_model_data_error(
    model: FilterByExtentModel,
):
    assert (
        model.data(_priority_1_feature_type_1_feature_1_error_1_index(model))
        == "Geometry error"
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == "Virheellinen geometria"
    )

    assert (
        model.data(_priority_1_feature_type_1_feature_1_error_2_index(model))
        == "Attribute error"
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_description_index(model)
        )
        == "Virheellinen arvo"
    )


def test_model_data_user_processed(model: FilterByExtentModel):
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.CheckStateRole
        ).value()
        == Qt.Unchecked
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_index(model), Qt.CheckStateRole
        ).value()
        == Qt.Checked
    )


def test_model_data_error_text_color(model: FilterByExtentModel):
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.ForegroundRole
        ).value()
        is None
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_index(model), Qt.ForegroundRole
        ).value()
        == Qt.lightGray
    )


def test_model_checkable_flags(model: FilterByExtentModel):
    invalid_index_flags = model.flags(QModelIndex())
    assert int(invalid_index_flags) == Qt.NoItemFlags

    error_flags = model.flags(_priority_1_feature_type_1_feature_1_error_1_index(model))
    assert int(error_flags & Qt.ItemIsUserCheckable) == Qt.ItemIsUserCheckable

    priority_flags = model.flags(_priority_1_index(model))
    assert int(priority_flags & Qt.ItemIsUserCheckable) == Qt.NoItemFlags


@pytest.mark.parametrize(
    (
        "value",
        "role",
        "expected_check_state",
        "expected_callback_value",
        "callback_called",
    ),
    [
        (-1, Qt.EditRole, Qt.Unchecked, None, False),
        (Qt.Checked, Qt.CheckStateRole, Qt.Checked, True, True),
        (Qt.Unchecked, Qt.CheckStateRole, Qt.Unchecked, False, True),
    ],
)
def test_model_set_data_user_processed(
    model: FilterByExtentModel,
    m_user_processed_callback: MagicMock,
    value: int,
    role: Qt.ItemDataRole,
    expected_check_state: int,
    expected_callback_value: bool,
    callback_called: bool,
):
    model.setData(
        _priority_1_feature_type_1_feature_1_error_1_index(model), value, role
    )

    check_state = model.data(
        _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.CheckStateRole
    )
    assert check_state.value() == expected_check_state
    if callback_called:
        m_user_processed_callback.assert_called_with("1", expected_callback_value)
    else:
        m_user_processed_callback.assert_not_called()


@pytest.mark.parametrize(
    (
        "error_type_filter",
        "feature_type_filter",
        "user_processed_filter",
        "expected_counts",
    ),
    [
        (
            {1},
            None,
            True,
            {
                "priority_count": 3,
                "feature_type_count": 2,
                "feature_1_count": 1,
                "feature_2_count": 1,
            },
        ),
        (
            {2},
            None,
            True,
            {
                "priority_count": 1,
                "feature_type_count": 1,
                "feature_1_count": 1,
                "feature_2_count": 0,
            },
        ),
        (
            {1, 2},
            None,
            True,
            {
                "priority_count": 4,
                "feature_type_count": 3,
                "feature_1_count": 2,
                "feature_2_count": 1,
            },
        ),
        (
            None,
            {"building_part_area"},
            True,
            {
                "priority_count": 3,
                "feature_type_count": 3,
                "feature_1_count": 2,
                "feature_2_count": 1,
            },
        ),
        (
            None,
            {"chimney_point"},
            True,
            {
                "priority_count": 1,
                "feature_type_count": 1,
                "feature_1_count": 1,
                "feature_2_count": 0,
            },
        ),
        (
            None,
            None,
            False,
            {
                "priority_count": 3,
                "feature_type_count": 2,
                "feature_1_count": 1,
                "feature_2_count": 1,
            },
        ),
        (
            {1},
            {"building_part_area"},
            True,
            {
                "priority_count": 2,
                "feature_type_count": 2,
                "feature_1_count": 1,
                "feature_2_count": 1,
            },
        ),
        (
            {},
            {},
            True,
            {
                "priority_count": 0,
                "feature_type_count": 0,
                "feature_1_count": 0,
                "feature_2_count": 0,
            },
        ),
    ],
    ids=[
        "Attribute filter",
        "Geometry filter",
        "Attribute and geometry filter",
        "Building part filter",
        "Chimney point filter",
        "User processed filter",
        "Combined filters",
        "Empty filters",
    ],
)
def test_model_data_count_changes_when_filter_is_applied(
    model: FilterByExtentModel,
    quality_errors: List[QualityErrorsByPriority],
    error_type_filter: Set[int],
    feature_type_filter: Set[str],
    user_processed_filter: bool,
    expected_counts: Dict[str, int],
):
    error_type_filters = _error_type_filters()
    feature_type_filters = _feature_type_filters(quality_errors)

    if feature_type_filter is not None:
        feature_type_filters = feature_type_filter

    if error_type_filter is not None:
        error_type_filters = error_type_filter

    model.sourceModel().update_filters(
        feature_type_filters, error_type_filters, user_processed_filter
    )

    assert (
        _count_quality_error_rows(model, _priority_1_index(model))
        == expected_counts["priority_count"]
    )
    assert (
        _count_quality_error_rows(model, _priority_1_feature_type_1_index(model))
        == expected_counts["feature_type_count"]
    )
    assert (
        _count_quality_error_rows(
            model, _priority_1_feature_type_1_feature_1_index(model)
        )
        == expected_counts["feature_1_count"]
    )
    assert (
        _count_quality_error_rows(
            model, _priority_1_feature_type_1_feature_2_index(model)
        )
        == expected_counts["feature_2_count"]
    )
