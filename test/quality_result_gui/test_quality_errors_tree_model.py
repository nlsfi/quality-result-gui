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

from typing import Dict, List, NamedTuple, Optional, Set
from unittest.mock import MagicMock

import pytest
from pytestqt.modeltest import ModelTester
from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt, QVariant

from quality_result_gui.api.types.quality_error import (
    QualityErrorsByPriority,
    QualityErrorType,
)
from quality_result_gui.quality_errors_filters import (
    AttributeFilter,
    ErrorTypeFilter,
    FeatureTypeFilter,
)
from quality_result_gui.quality_errors_tree_model import (
    FilterByExtentProxyModel,
    FilterByShowUserProcessedProxyModel,
    FilterProxyModel,
    QualityErrorsTreeBaseModel,
    StyleProxyModel,
    get_error_feature_attributes,
    get_error_feature_types,
)


def _feature_type_filters(quality_errors: List[QualityErrorsByPriority]) -> Set[str]:
    return get_error_feature_types(quality_errors)


def _feature_attribute_filters(
    quality_errors: List[QualityErrorsByPriority],
) -> Set[str]:
    return get_error_feature_attributes(quality_errors)


def _error_type_filters() -> Set[QualityErrorType]:
    return set(QualityErrorType)


def _reset_filters(
    model: FilterByExtentProxyModel, quality_errors: List[QualityErrorsByPriority]
) -> None:
    model.sourceModel().update_filters(
        _feature_type_filters(quality_errors),
        _error_type_filters(),
        _feature_attribute_filters(quality_errors),
        True,
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


def _priority_1_index(model: QAbstractItemModel) -> QModelIndex:
    return model.index(0, 0, QModelIndex())


def _priority_2_index(model: QAbstractItemModel) -> QModelIndex:
    return model.index(1, 0, QModelIndex())


def _priority_1_feature_type_1_index(model: QAbstractItemModel) -> QModelIndex:
    return model.index(0, 0, _priority_1_index(model))


def _priority_1_feature_type_2_index(model: QAbstractItemModel) -> QModelIndex:
    return model.index(1, 0, _priority_1_index(model))


def _priority_1_feature_type_1_feature_1_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(0, 0, _priority_1_feature_type_1_index(model))


def _priority_1_feature_type_1_feature_2_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(1, 0, _priority_1_feature_type_1_index(model))


def _priority_1_feature_type_1_feature_1_error_1_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(0, 0, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_2_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(1, 0, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_1_description_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(0, 1, _priority_1_feature_type_1_feature_1_index(model))


def _priority_1_feature_type_1_feature_1_error_2_description_index(
    model: QAbstractItemModel,
) -> QModelIndex:
    return model.index(1, 1, _priority_1_feature_type_1_feature_1_index(model))


@pytest.fixture()
def feature_type_filter(
    quality_errors: List[QualityErrorsByPriority],
) -> FeatureTypeFilter:
    feature_type_filter = FeatureTypeFilter()
    for feature_type in get_error_feature_types(quality_errors):
        feature_type_filter._add_filter_item(feature_type, feature_type)
    return feature_type_filter


@pytest.fixture()
def m_user_processed_callback() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def base_model() -> QualityErrorsTreeBaseModel:
    return QualityErrorsTreeBaseModel()


@pytest.fixture()
def model(
    quality_errors: List[QualityErrorsByPriority],
    base_model: QualityErrorsTreeBaseModel,
) -> FilterByExtentProxyModel:
    styled_model = StyleProxyModel(None)
    styled_model.setSourceModel(base_model)

    filter_model = FilterProxyModel(None)
    filter_model.setSourceModel(styled_model)

    user_processed_model = FilterByShowUserProcessedProxyModel(None)
    user_processed_model.setSourceModel(filter_model)

    extent_model = FilterByExtentProxyModel(None)
    extent_model.setSourceModel(user_processed_model)

    base_model.refresh_model(quality_errors)
    filter_model.invalidateFilter()

    return extent_model


class ModelAndFilters(NamedTuple):
    base_model: QualityErrorsTreeBaseModel
    filter_proxy_model: FilterProxyModel
    feature_type_filter: FeatureTypeFilter
    error_type_filter: ErrorTypeFilter
    attribute_name_filter: AttributeFilter


@pytest.fixture()
def filter_proxy_model_and_filters(
    base_model: QualityErrorsTreeBaseModel,
    quality_errors: List[QualityErrorsByPriority],
) -> ModelAndFilters:

    filter_model = FilterProxyModel()
    filter_model.setSourceModel(base_model)

    feature_type_filter = FeatureTypeFilter()
    feature_type_filter.update_filter_from_errors(quality_errors)
    filter_model.add_filter(feature_type_filter)

    error_type_filter = ErrorTypeFilter()
    filter_model.add_filter(error_type_filter)

    attribute_name_filter = AttributeFilter()
    attribute_name_filter.update_filter_from_errors(quality_errors)
    filter_model.add_filter(attribute_name_filter)

    base_model.refresh_model(quality_errors)
    filter_model.invalidateFilter()

    return ModelAndFilters(
        base_model,
        filter_model,
        feature_type_filter,
        error_type_filter,
        attribute_name_filter,
    )


def test_base_model(
    base_model: QualityErrorsTreeBaseModel,
    qtmodeltester: ModelTester,
    quality_errors: List[QualityErrorsByPriority],
) -> None:
    base_model.refresh_model(quality_errors)

    qtmodeltester.check(base_model)


def test_model_index(model: FilterByExtentProxyModel):
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


def test_model_parent(model: FilterByExtentProxyModel):
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


def test_model_row_count(model: FilterByExtentProxyModel):
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


def test_model_column_count(model: FilterByExtentProxyModel):
    assert model.columnCount(QModelIndex()) == 2
    assert (
        model.columnCount(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == 2
    )


@pytest.mark.xfail(reason="Not yet revised.")
def test_model_header_data(model: FilterByExtentProxyModel):
    assert not QVariant(model.headerData(0, Qt.Vertical)).isValid()
    assert QVariant(model.headerData(0, Qt.Horizontal)).isValid()

    for valid_col_index in [0, 1]:
        assert QVariant(model.headerData(valid_col_index, Qt.Horizontal)).isValid()

    for invalid_col_index in [-1, 2, 3, 4, 5, 10, 99]:
        assert not QVariant(
            model.headerData(invalid_col_index, Qt.Horizontal)
        ).isValid()


@pytest.mark.xfail(reason="Not yet revised.")
def test_total_number_of_errors_is_shown_in_header(
    model: FilterByExtentProxyModel, quality_errors: List[QualityErrorsByPriority]
):
    assert "5/5" in model.headerData(0, Qt.Horizontal).value()

    error_type_filters = _error_type_filters()

    error_type_filters.remove(QualityErrorType.GEOMETRY)
    model.sourceModel().update_filters(
        _feature_type_filters(quality_errors),
        error_type_filters,
        _feature_attribute_filters(quality_errors),
        True,
    )
    assert "4/5" in model.headerData(0, Qt.Horizontal).value()

    _reset_filters(model, quality_errors)
    feature_type_filters = _feature_type_filters(quality_errors)
    feature_type_filters.remove("building_part_area")
    model.sourceModel().update_filters(
        feature_type_filters,
        _error_type_filters(),
        _feature_attribute_filters(quality_errors),
        True,
    )
    assert "1/5" in model.headerData(0, Qt.Horizontal).value()


def test_model_data_invalid_index(model: FilterByExtentProxyModel):
    assert not QVariant(model.data(QModelIndex())).isValid()


def test_model_data_priority(model: FilterByExtentProxyModel):
    assert model.data(_priority_1_index(model)) == "Fatal"
    assert _count_quality_error_rows(model, _priority_1_index(model)) == 4
    assert not QVariant(model.data(model.index(0, 2, QModelIndex()))).isValid()

    assert model.data(_priority_2_index(model)) == "Warning"
    assert _count_quality_error_rows(model, _priority_2_index(model)) == 1


def test_model_data_feature_type(model: FilterByExtentProxyModel):
    assert model.data(_priority_1_feature_type_1_index(model)) == "building_part_area"
    assert (
        _count_quality_error_rows(model, _priority_1_feature_type_1_index(model)) == 3
    )
    assert not QVariant(model.data(model.index(0, 2, QModelIndex()))).isValid()

    assert model.data(_priority_1_feature_type_2_index(model)) == "chimney_point"
    assert (
        _count_quality_error_rows(model, _priority_1_feature_type_2_index(model)) == 1
    )


def test_model_data_feature(model: FilterByExtentProxyModel):
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
    model: FilterByExtentProxyModel,
):
    assert (
        model.data(_priority_1_feature_type_1_feature_1_error_1_index(model))
        == "Geometry error"
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_description_index(model)
        )
        == "Invalid geometry"
    )
    extra_info = model.data(
        _priority_1_feature_type_1_feature_1_error_1_description_index(model),
        Qt.ToolTipRole,
    )
    assert "Invalid geometry" in extra_info
    assert "Extra info" in extra_info

    assert (
        model.data(_priority_1_feature_type_1_feature_1_error_2_index(model))
        == "Attribute error"
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_description_index(model)
        )
        == "Invalid value"
    )


def test_model_data_user_processed(model: FilterByExtentProxyModel):
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.CheckStateRole
        )
        == Qt.Unchecked
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_index(model), Qt.CheckStateRole
        )
        == Qt.Checked
    )


def test_model_data_error_text_color(model: FilterByExtentProxyModel):
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.ForegroundRole
        )
        is None
    )
    assert (
        model.data(
            _priority_1_feature_type_1_feature_1_error_2_index(model), Qt.ForegroundRole
        )
        == Qt.lightGray
    )


def test_model_checkable_flags(model: FilterByExtentProxyModel):
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
@pytest.mark.xfail(reason="Not yet revised.")
def test_model_set_data_user_processed(
    model: FilterByExtentProxyModel,
    m_user_processed_callback: MagicMock,
    value: int,
    role: Qt.ItemDataRole,
    expected_check_state: int,
    expected_callback_value: bool,
    callback_called: bool,
) -> None:
    model.setData(
        _priority_1_feature_type_1_feature_1_error_1_index(model), value, role
    )
    check_state = model.data(
        _priority_1_feature_type_1_feature_1_error_1_index(model), Qt.CheckStateRole
    )
    assert check_state == expected_check_state

    if callback_called:
        m_user_processed_callback.assert_called_with("1", expected_callback_value)
    else:
        m_user_processed_callback.assert_not_called()


@pytest.mark.parametrize(
    (
        "accepted_error_types",
        "accepted_feature_types",
        "accetepted_attribute_names",
        "expected_counts",
    ),
    [
        (
            {QualityErrorType.ATTRIBUTE},
            None,
            None,
            {
                "priority_count": 3,
                "feature_type_count": 2,
                "feature_1_count": 1,
                "feature_2_count": 1,
            },
        ),
        (
            {QualityErrorType.GEOMETRY},
            None,
            None,
            {
                "priority_count": 1,
                "feature_type_count": 1,
                "feature_1_count": 1,
                "feature_2_count": 0,
            },
        ),
        (
            {QualityErrorType.ATTRIBUTE, QualityErrorType.GEOMETRY},
            None,
            None,
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
            None,
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
            None,
            {
                "priority_count": 1,
                "feature_type_count": 1,
                "feature_1_count": 1,
                "feature_2_count": 0,
            },
        ),
        (
            {QualityErrorType.ATTRIBUTE},
            {"building_part_area"},
            None,
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
            {},
            {
                "priority_count": 0,
                "feature_type_count": 0,
                "feature_1_count": 0,
                "feature_2_count": 0,
            },
        ),
        pytest.param(
            None,
            None,
            {"height_relative"},
            {
                "priority_count": 1,
                "feature_type_count": 1,
                "feature_1_count": 1,
                "feature_2_count": 0,
            },
            marks=pytest.mark.xfail(reason="Not yet revised fully"),
        ),
    ],
    ids=[
        "Attribute filter",
        "Geometry filter",
        "Attribute and geometry filter",
        "Building part filter",
        "Chimney point filter",
        "Combined filters",
        "Empty filters",
        "Relative height filters",
    ],
)
def test_model_data_count_changes_when_filter_is_applied(
    filter_proxy_model_and_filters: ModelAndFilters,
    quality_errors: List[QualityErrorsByPriority],
    accepted_error_types: Optional[Set[QualityErrorType]],
    accepted_feature_types: Optional[Set[str]],
    accetepted_attribute_names: Optional[Set[str]],
    expected_counts: Dict[str, int],
):
    accepted_feature_types = (
        accepted_feature_types
        if accepted_feature_types is not None
        else _feature_type_filters(quality_errors)
    )
    for (
        filter_value
    ) in (
        filter_proxy_model_and_filters.feature_type_filter._filter_value_action_map.keys()
    ):
        filter_proxy_model_and_filters.feature_type_filter._sync_filtered(
            filter_value, filter_value in accepted_feature_types
        )

    accetepted_attribute_names = (
        accetepted_attribute_names
        if accetepted_attribute_names is not None
        else _feature_attribute_filters(quality_errors)
    )
    for (
        filter_value
    ) in (
        filter_proxy_model_and_filters.attribute_name_filter._filter_value_action_map.keys()
    ):
        filter_proxy_model_and_filters.attribute_name_filter._sync_filtered(
            filter_value, filter_value in accetepted_attribute_names
        )

    accepted_error_types = (
        accepted_error_types
        if accepted_error_types is not None
        else _error_type_filters()
    )
    for (
        filter_value
    ) in (
        filter_proxy_model_and_filters.error_type_filter._filter_value_action_map.keys()
    ):
        filter_proxy_model_and_filters.error_type_filter._sync_filtered(
            filter_value, filter_value in accepted_error_types
        )

    model = filter_proxy_model_and_filters.filter_proxy_model
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


def test_refresh_model_updates_data_partially_when_data_is_refreshed(
    base_model: QualityErrorsTreeBaseModel,
    quality_errors: List[QualityErrorsByPriority],
):
    base_model.refresh_model(quality_errors)

    assert base_model.index(0, 0, QModelIndex()).data() == "Fatal"
    assert (
        _count_quality_error_rows(base_model, base_model.index(0, 0, QModelIndex()))
        == 4
    )

    # Remove fatal errors
    quality_errors.remove(quality_errors[0])
    base_model.refresh_model(quality_errors)

    assert base_model.index(0, 0, QModelIndex()).data() == "Fatal"
    assert base_model.index(1, 0, QModelIndex()).data() == "Warning"
    assert (
        _count_quality_error_rows(base_model, base_model.index(1, 0, QModelIndex()))
        == 1
    )


def test_refresh_model_does_nothing_if_data_does_not_change(
    base_model: QualityErrorsTreeBaseModel,
    quality_errors: List[QualityErrorsByPriority],
):
    base_model.refresh_model(quality_errors)

    assert base_model.index(0, 0, QModelIndex()).data() == "Fatal"
    assert (
        _count_quality_error_rows(base_model, base_model.index(0, 0, QModelIndex()))
        == 4
    )

    base_model.refresh_model(quality_errors)

    assert base_model.index(0, 0, QModelIndex()).data() == "Fatal"
    assert (
        _count_quality_error_rows(base_model, base_model.index(0, 0, QModelIndex()))
        == 4
    )


@pytest.mark.xfail(reason="Not yet revised.")
def test_no_rows_visible_when_all_user_processed(
    model: FilterByExtentProxyModel,
):
    model.sourceModel().update_filters(
        {"chimney_point"},
        {1},
        {"height_relative"},
        False,
    )

    assert _count_quality_error_rows(model, _priority_1_index(model)) == 1
    assert _count_quality_error_rows(model, _priority_2_index(model)) == 0

    model.setData(
        _priority_1_feature_type_1_feature_1_error_1_index(model),
        Qt.Checked,
        Qt.CheckStateRole,
    )

    assert _count_quality_error_rows(model, _priority_1_index(model)) == 0
    assert _count_quality_error_rows(model, _priority_2_index(model)) == 0
