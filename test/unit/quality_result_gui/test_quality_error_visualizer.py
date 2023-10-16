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

from collections.abc import Generator
from unittest.mock import ANY

import pytest
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsLayerTree,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgisInterface
from quality_result_gui import SelectionType
from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorPriority,
)
from quality_result_gui.quality_error_visualizer import QualityErrorVisualizer

CRS = QgsCoordinateReferenceSystem("EPSG:3067")


def _create_test_quality_error(
    priority: QualityErrorPriority, unique_id: str, geom: QgsGeometry
) -> QualityError:
    return QualityError(
        priority, ANY, ANY, ANY, unique_id, ANY, ANY, ANY, ANY, geom, ANY
    )


@pytest.fixture()
def visualizer() -> Generator[QualityErrorVisualizer, None, None]:
    visualizer = QualityErrorVisualizer(CRS)
    visualizer.toggle_visibility(True)
    yield visualizer
    visualizer.remove_quality_error_layer()
    assert visualizer._quality_error_layer.find_layer_from_project() is None


@pytest.fixture()
def visualized_errors() -> list[QualityError]:
    return [
        _create_test_quality_error(
            QualityErrorPriority.FATAL, "1", QgsGeometry.fromWkt("Point(1 1)")
        ),
        _create_test_quality_error(
            QualityErrorPriority.WARNING,
            "2",
            QgsGeometry.fromWkt("LinestringZ(1 1 0, 2 2 0)"),
        ),
        _create_test_quality_error(
            QualityErrorPriority.INFO,
            "3",
            QgsGeometry.fromWkt("Polygon((0 0, 0 1, 1 1, 1 0, 0 0))"),
        ),
    ]


def get_num_visualized_features(visualizer: QualityErrorVisualizer) -> int:
    layer = visualizer._quality_error_layer.find_layer_from_project()
    if layer is not None:
        return len(layer.items())
    return 0


def test_add_new_errors_adds_geometries_to_annotation_layer(
    visualizer: QualityErrorVisualizer,
):
    geometry = QgsGeometry.fromWkt("Polygon((0 0, 0 1, 1 1, 1 0, 0 0))")
    assert not geometry.isNull(), "Input WKT was not valid"

    # Test
    visualizer.add_new_errors(
        [
            _create_test_quality_error(QualityErrorPriority.FATAL, "1", geometry),
            _create_test_quality_error(QualityErrorPriority.WARNING, "2", geometry),
        ]
    )

    layer = visualizer._quality_error_layer.find_layer_from_project()

    assert layer is not None

    for key in visualizer._quality_error_layer._annotation_ids:
        assert key in [
            "1",
            "2",
        ]

    assert len(layer.items()) == 2

    for key in layer.items():
        assert key in sum(visualizer._quality_error_layer._annotation_ids.values(), [])
        assert layer.item(key).geometry().isEmpty() is False


def test_add_new_errors_does_nothing_with_empty_input(
    visualizer: QualityErrorVisualizer,
):
    # Test
    visualizer.add_new_errors([])

    assert get_num_visualized_features(visualizer) == 0


def test_add_new_errors_does_nothing_with_empty_input_geometry(
    visualizer: QualityErrorVisualizer,
):
    # Test
    visualizer.add_new_errors(
        [_create_test_quality_error(QualityErrorPriority.FATAL, "1", QgsGeometry())]
    )

    assert get_num_visualized_features(visualizer) == 0


def test_add_new_errors_works_with_multiple_geoms_with_same_geometry_type(
    visualizer: QualityErrorVisualizer,
):
    priority = QualityErrorPriority.FATAL
    errors = [
        _create_test_quality_error(priority, "1", QgsGeometry.fromWkt("Point(2 3)")),
        _create_test_quality_error(priority, "2", QgsGeometry.fromWkt("Point(1 1)")),
        _create_test_quality_error(priority, "3", QgsGeometry.fromWkt("Point(0 0)")),
    ]

    # Test
    visualizer.add_new_errors(errors)

    assert get_num_visualized_features(visualizer) == len(errors)


@pytest.mark.parametrize(
    ("remove_selected_error"),
    [
        (True),
        (False),
    ],
    ids=[
        "selected error in removed list",
        "selected error not in removed list",
    ],
)
def test_remove_errors_removes_features_from_annotation_layer(
    visualizer: QualityErrorVisualizer,
    visualized_errors: list[QualityError],
    remove_selected_error: bool,
):
    visualizer.add_new_errors(visualized_errors)
    # Select first error
    visualizer.refresh_selected_error(visualized_errors[0])

    num_errors_before_removal = len(visualized_errors) + 1
    assert get_num_visualized_features(visualizer) == num_errors_before_removal

    # Test
    if remove_selected_error:
        visualizer.remove_errors(visualized_errors[:2])
    else:
        visualizer.remove_errors(visualized_errors[1:3])

    if remove_selected_error:
        assert get_num_visualized_features(visualizer) == num_errors_before_removal - 3
        for key in visualizer._quality_error_layer._annotation_ids:
            assert key == visualized_errors[2].unique_identifier
    else:
        assert get_num_visualized_features(visualizer) == num_errors_before_removal - 2
        assert set(visualizer._quality_error_layer._annotation_ids.keys()) == {
            visualized_errors[0].unique_identifier,
            f"selected-{visualized_errors[0].unique_identifier}",
        }


def test_remove_errors_does_nothing_with_empty_input(
    visualizer: QualityErrorVisualizer, visualized_errors: list[QualityError]
):
    visualizer.add_new_errors(visualized_errors)
    visualizer.refresh_selected_error(visualized_errors[0])

    assert get_num_visualized_features(visualizer) == len(visualized_errors) + 1

    # Test
    visualizer.remove_errors([])

    assert get_num_visualized_features(visualizer) == len(visualized_errors) + 1
    assert (
        f"selected-{visualized_errors[0].unique_identifier}"
        in visualizer._quality_error_layer._annotation_ids
    )


def test_hide_errors_changes_quality_layer_visibility(
    visualizer: QualityErrorVisualizer, visualized_errors: list[QualityError]
):
    root: QgsLayerTree = QgsProject.instance().layerTreeRoot()

    visualizer.add_new_errors(visualized_errors)

    layer = visualizer._quality_error_layer.find_layer_from_project()
    assert layer is not None

    tree_node = root.findLayer(layer.id())
    assert tree_node is not None
    assert tree_node.itemVisibilityChecked() is True

    # Test
    visualizer.hide_errors()

    assert get_num_visualized_features(visualizer) == len(visualized_errors)
    assert tree_node.itemVisibilityChecked() is False


def test_add_new_errors_replaces_annotation_features_if_same_id(
    visualizer: QualityErrorVisualizer,
    visualized_errors: list[QualityError],
):
    visualizer.add_new_errors(visualized_errors)
    assert get_num_visualized_features(visualizer) == len(visualized_errors)

    new_errors = [
        _create_test_quality_error(
            QualityErrorPriority.FATAL, "1", QgsGeometry.fromWkt("Point(2 3)")
        )
    ]

    # Test
    visualizer.add_new_errors(new_errors)

    assert get_num_visualized_features(visualizer) == len(visualized_errors)


def test_refresh_selected_errors_replaces_selected_features_only(
    visualizer: QualityErrorVisualizer, visualized_errors: list[QualityError]
):
    visualizer.add_new_errors(visualized_errors)
    visualizer.refresh_selected_error(visualized_errors[0])

    assert (
        f"selected-{visualized_errors[0].unique_identifier}"
        in visualizer._quality_error_layer._annotation_ids
    )

    # Test
    visualizer.refresh_selected_error(visualized_errors[1])

    assert get_num_visualized_features(visualizer) == len(visualized_errors) + 1

    assert sorted(visualizer._quality_error_layer._annotation_ids.keys()) == sorted(
        [
            str(visualized_errors[0].unique_identifier),
            str(visualized_errors[1].unique_identifier),
            str(visualized_errors[2].unique_identifier),
            f"selected-{visualized_errors[1].unique_identifier}",
        ]
    )


@pytest.mark.parametrize(
    ("input_geom", "should_zoom_to_feature"),
    [
        (QgsGeometry.fromWkt("Point(2 3)"), True),
        (QgsGeometry(), False),
    ],
    ids=[
        "one geom",
        "null geometry",
    ],
)
def test_on_error_selected(
    visualizer: QualityErrorVisualizer,
    qgis_iface: QgisInterface,
    input_geom: QgsGeometry,
    should_zoom_to_feature: bool,
):
    qgis_iface.mapCanvas().setExtent(QgsRectangle(100, 100, 200, 200))
    original_extent = qgis_iface.mapCanvas().extent()
    visualized_error = _create_test_quality_error(
        QualityErrorPriority.FATAL, "1", input_geom
    )

    # Test
    visualizer.on_error_selected(visualized_error, SelectionType.RightClick)

    if should_zoom_to_feature is True:
        assert original_extent != qgis_iface.mapCanvas().extent()
        assert round(original_extent.area(), 1) == round(
            qgis_iface.mapCanvas().extent().area(), 1
        )
    else:
        assert original_extent == qgis_iface.mapCanvas().extent()


@pytest.mark.parametrize(
    ("preserve_scale"),
    [
        (True),
        (False),
    ],
    ids=[
        "scale preserved",
        "scale not preserved",
    ],
)
@pytest.mark.parametrize(
    ("input_geoms", "should_zoom_to_feature"),
    [
        ([QgsGeometry.fromWkt("Point(2 3)")], True),
        ([QgsGeometry.fromWkt("Point(2 3)"), QgsGeometry.fromWkt("Point(1 1)")], True),
        ([], False),
    ],
    ids=[
        "one geom",
        "multiple geoms",
        "empty list",
    ],
)
def test_zoom_to_geometries_and_flash(
    visualizer: QualityErrorVisualizer,
    qgis_iface: QgisInterface,
    preserve_scale: bool,
    input_geoms: list[QgsGeometry],
    should_zoom_to_feature: bool,
):
    qgis_iface.mapCanvas().setExtent(QgsRectangle(100, 100, 200, 200))
    original_extent = qgis_iface.mapCanvas().extent()
    visualized_errors = []

    for geom in input_geoms:
        visualized_errors.append(
            _create_test_quality_error(QualityErrorPriority.FATAL, "1", geom)
        )
    # Test
    visualizer.zoom_to_geometries_and_flash(visualized_errors, preserve_scale)

    if should_zoom_to_feature is True:
        assert original_extent != qgis_iface.mapCanvas().extent()
        if preserve_scale is True:
            assert round(original_extent.area(), 1) == round(
                qgis_iface.mapCanvas().extent().area(), 1
            )
        else:
            for geom in input_geoms:
                assert QgsGeometry.fromRect(qgis_iface.mapCanvas().extent()).contains(
                    geom
                )
    else:
        assert original_extent == qgis_iface.mapCanvas().extent()
