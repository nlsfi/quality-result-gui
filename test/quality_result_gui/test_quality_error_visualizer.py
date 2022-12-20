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

from typing import Generator, List

import pytest
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsLayerTree,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgisInterface

from quality_result_gui.api.types.quality_error import QualityErrorPriority
from quality_result_gui.quality_error_visualizer import (
    ErrorFeature,
    QualityErrorVisualizer,
)

CRS = QgsCoordinateReferenceSystem("EPSG:3067")


@pytest.fixture()
def visualizer() -> Generator[QualityErrorVisualizer, None, None]:
    visualizer = QualityErrorVisualizer()
    visualizer.toggle_visibility(True)
    yield visualizer
    visualizer.remove_quality_error_layer()
    assert visualizer._quality_error_layer.find_layer_from_project() is None


@pytest.fixture()
def error_features() -> List[ErrorFeature]:
    return [
        ErrorFeature(
            "1", QualityErrorPriority.FATAL, QgsGeometry.fromWkt("POINT(1 1)"), CRS
        ),
        ErrorFeature(
            "2",
            QualityErrorPriority.WARNING,
            QgsGeometry.fromWkt("LinestringZ(1 1 0, 2 2 0)"),
            CRS,
        ),
        ErrorFeature(
            "3",
            QualityErrorPriority.INFO,
            QgsGeometry.fromWkt("Polygon((0 0, 0 1, 1 1, 1 0, 0 0))"),
            CRS,
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
            ErrorFeature("1", QualityErrorPriority.FATAL, geometry, CRS),
            ErrorFeature("2", QualityErrorPriority.WARNING, geometry, CRS),
        ]
    )

    layer = visualizer._quality_error_layer.find_layer_from_project()

    assert layer is not None

    for key in visualizer._quality_error_layer._annotation_ids.keys():
        assert key in [
            "1",
            "2",
        ]

    assert len(layer.items()) == 2

    for key in layer.items().keys():
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
        [ErrorFeature("1", QualityErrorPriority.FATAL, QgsGeometry(), CRS)]
    )

    assert get_num_visualized_features(visualizer) == 0


def test_add_new_errors_works_with_multiple_geoms_with_same_geometry_type(
    visualizer: QualityErrorVisualizer,
):

    priority = QualityErrorPriority.FATAL
    errors = [
        ErrorFeature("1", priority, QgsGeometry.fromWkt("Point(2 3)"), CRS),
        ErrorFeature("2", priority, QgsGeometry.fromWkt("Point(1 1)"), CRS),
        ErrorFeature("3", priority, QgsGeometry.fromWkt("Point(0 0)"), CRS),
    ]

    # Test
    visualizer.add_new_errors(errors)

    assert get_num_visualized_features(visualizer) == len(errors)


def test_remove_errors_removes_features_from_annotation_layer(
    visualizer: QualityErrorVisualizer, error_features: List[ErrorFeature]
):
    visualizer.add_new_errors(error_features)
    assert get_num_visualized_features(visualizer) == len(error_features)

    # Test
    visualizer.remove_errors(error_features[:2])

    assert get_num_visualized_features(visualizer) == len(error_features) - 2
    for key in visualizer._quality_error_layer._annotation_ids.keys():
        assert key == error_features[2].id


def test_remove_errors_does_nothing_with_empty_input(
    visualizer: QualityErrorVisualizer, error_features: List[ErrorFeature]
):
    visualizer.add_new_errors(error_features)
    assert get_num_visualized_features(visualizer) == len(error_features)

    # Test
    visualizer.remove_errors([])

    assert get_num_visualized_features(visualizer) == len(error_features)


def test_hide_errors_changes_quality_layer_visibility(
    visualizer: QualityErrorVisualizer, error_features: List[ErrorFeature]
):
    root: QgsLayerTree = QgsProject.instance().layerTreeRoot()

    visualizer.add_new_errors(error_features)

    layer = visualizer._quality_error_layer.find_layer_from_project()
    assert layer is not None

    tree_node = root.findLayer(layer.id())
    assert tree_node is not None
    assert tree_node.itemVisibilityChecked() is True

    # Test
    visualizer.hide_errors()

    assert get_num_visualized_features(visualizer) == len(error_features)
    assert tree_node.itemVisibilityChecked() is False


def test_add_new_errors_replaces_annotation_features_if_same_id(
    visualizer: QualityErrorVisualizer,
    error_features: List[ErrorFeature],
):

    visualizer.add_new_errors(error_features)
    assert get_num_visualized_features(visualizer) == len(error_features)

    new_errors = [
        ErrorFeature(
            "1", QualityErrorPriority.FATAL, QgsGeometry.fromWkt("Point(2 3)"), CRS
        )
    ]

    # Test
    visualizer.add_new_errors(new_errors)

    assert get_num_visualized_features(visualizer) == len(error_features)


def test_refresh_selected_errors_replaces_selected_features_only(
    visualizer: QualityErrorVisualizer, error_features: List[ErrorFeature]
):

    visualizer.add_new_errors(error_features)
    visualizer.refresh_selected_error(error_features[0])

    assert (
        f"selected-{error_features[0].id}"
        in visualizer._quality_error_layer._annotation_ids
    )

    # Test
    visualizer.refresh_selected_error(error_features[1])

    assert get_num_visualized_features(visualizer) == len(error_features) + 1

    assert sorted(visualizer._quality_error_layer._annotation_ids.keys()) == sorted(
        [
            str(error_features[0].id),
            str(error_features[1].id),
            str(error_features[2].id),
            f"selected-{error_features[1].id}",
        ]
    )


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
def test_zoom_to_geometries_and_flash(  # noqa: QGS105
    visualizer: QualityErrorVisualizer,
    qgis_iface: QgisInterface,
    preserve_scale: bool,
    input_geoms: List[QgsGeometry],
    should_zoom_to_feature: bool,
):
    qgis_iface.mapCanvas().setExtent(QgsRectangle(100, 100, 200, 200))
    original_extent = qgis_iface.mapCanvas().extent()
    error_features = []

    for geom in input_geoms:
        error_features.append(ErrorFeature("1", QualityErrorPriority.FATAL, geom, CRS))

    # Test
    visualizer.zoom_to_geometries_and_flash(error_features, preserve_scale)

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
