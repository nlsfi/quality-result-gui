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

from unittest.mock import ANY

import pytest
from qgis.core import QgsAnnotationLayer, QgsGeometry, QgsProject
from quality_result_gui.api.types.quality_error import QualityErrorPriority
from quality_result_gui.quality_error_visualizer import QualityError
from quality_result_gui.quality_layer import QualityErrorLayer


def _create_test_quality_error(
    priority: QualityErrorPriority, unique_id: str, geom: QgsGeometry
) -> QualityError:
    return QualityError(
        priority, ANY, ANY, ANY, unique_id, ANY, ANY, ANY, ANY, geom, ANY
    )


@pytest.fixture()
def quality_layer(qgis_new_project: None) -> QualityErrorLayer:
    return QualityErrorLayer()


@pytest.fixture()
def quality_layer_created(
    quality_layer: QualityErrorLayer,
) -> QualityErrorLayer:
    annotation_layer = quality_layer.get_annotation_layer()
    assert isinstance(annotation_layer, QgsAnnotationLayer)
    QgsProject.instance().addMapLayer(annotation_layer)
    return quality_layer


def test_find_layer_from_project_when_not_added_to_project_should_do_nothing(
    quality_layer: QualityErrorLayer,
):
    annotation_layer = quality_layer.find_layer_from_project()

    assert annotation_layer is None


def test_find_layer_from_project_when_added_to_project_should_return_annotation_layer(
    quality_layer_created: QualityErrorLayer,
):
    annotation_layer = quality_layer_created.find_layer_from_project()

    assert isinstance(annotation_layer, QgsAnnotationLayer)
    assert isinstance(quality_layer_created.annotation_layer, QgsAnnotationLayer)


@pytest.mark.parametrize(
    ("priority"),
    [
        (QualityErrorPriority.FATAL),
        (QualityErrorPriority.WARNING),
        (QualityErrorPriority.INFO),
    ],
    ids=[
        "error",
        "warning",
        "info",
    ],
)
@pytest.mark.parametrize(
    ("geometry", "num_resulting_annotations"),
    [
        (QgsGeometry.fromWkt("Point(1 1)"), 1),
        (QgsGeometry.fromWkt("PointZ(1 1 0)"), 1),
        (QgsGeometry.fromWkt("MultiPointZ((1 1 0), (2 2 0))"), 2),
        (QgsGeometry.fromWkt("Linestring(1 1, 2 2)"), 1),
        (QgsGeometry.fromWkt("LinestringZ(1 1 0, 2 2 0)"), 1),
        (QgsGeometry.fromWkt("MultiLinestringZ((1 1 0, 2 2 0), (5 1 0, 5 2 0))"), 2),
        (QgsGeometry.fromWkt("Polygon((0 0, 0 1, 1 1, 1 0, 0 0))"), 1),
        (QgsGeometry.fromWkt("PolygonZ((0 0 0, 0 1 0, 1 1 0, 1 0 0, 0 0 0))"), 1),
        (
            QgsGeometry.fromWkt(
                "MultiPolygonZ(((0 0 0, 0 1 0, 1 1 0, 1 0 0, 0 0 0)),((10 10 0, 10 11 0, 11 11 0, 11 10 0, 10 10 0)))"
            ),
            2,
        ),
        (
            QgsGeometry.fromWkt(
                "MultiPolygonZ (((0 0 0, 0 3 0, 3 3 0, 3 0 0, 0 0 0),"
                "(1 2 0, 1 1 0, 2 1 0, 2 2 0, 1 2 0)),"
                "((10 10 0, 10 11 0, 11 11 0, 11 10 0, 10 10 0)))"
            ),
            2,
        ),
    ],
    ids=[
        "Point",
        "PointZ",
        "MultiPointZ",
        "Linestring",
        "LinestringZ",
        "MultiLinestringZ",
        "Polygon",
        "PolygonZ",
        "MultiPolygonZ",
        "MultiPolygonZ with hole",
    ],
)
def test_add_or_replace_annotation_with_new_quality_errors(
    quality_layer_created: QualityErrorLayer,
    priority: QualityErrorPriority,
    geometry: QgsGeometry,
    num_resulting_annotations: int,
):
    assert not geometry.isNull(), "Input WKT was not valid"

    # Test
    quality_layer_created.add_or_replace_annotation(
        _create_test_quality_error(priority, "1", geometry), False
    )

    annotation_layer = quality_layer_created.annotation_layer
    assert list(quality_layer_created._annotation_ids.keys()) == ["1"]
    assert len(annotation_layer.items()) == num_resulting_annotations

    for key in annotation_layer.items():
        assert key in sum(quality_layer_created._annotation_ids.values(), [])
        item = annotation_layer.item(key)
        assert not item.geometry().isEmpty()
        assert item.zIndex() == -priority.value


@pytest.mark.parametrize(
    ("old_geom", "num_old_items", "new_geom", "expected_geoms_as_wkt"),
    [
        (
            QgsGeometry.fromWkt("Point(1 1)"),
            1,
            QgsGeometry.fromWkt("Point(5 5)"),
            ["POINT(5 5)"],
        ),
        (
            QgsGeometry.fromWkt("MultiPoint((1 1), (2 2))"),
            2,
            QgsGeometry.fromWkt("MultiPoint((5 5), (6 6))"),
            ["POINT(5 5)", "POINT(6 6)"],
        ),
        (
            QgsGeometry.fromWkt("MultiPoint((1 1), (2 2))"),
            2,
            QgsGeometry.fromWkt("Point(5 5)"),
            ["POINT(5 5)"],
        ),
        (
            QgsGeometry.fromWkt("MultiPoint((1 1), (2 2), (3 3))"),
            3,
            QgsGeometry.fromWkt("MultiPoint((5 5), (6 6))"),
            ["POINT(5 5)", "POINT(6 6)"],
        ),
        (
            QgsGeometry.fromWkt("MultiPoint((1 1), (2 2))"),
            2,
            QgsGeometry.fromWkt("MultiPoint((3 3), (5 5), (6 6))"),
            ["POINT(3 3)", "POINT(5 5)", "POINT(6 6)"],
        ),
    ],
    ids=[
        "singlegeometry",
        "multigeometry",
        "multigeometry to single geometry",
        "multigeometry to multigeometry with less parts",
        "multigeometry to multigeometry with more parts",
    ],
)
def test_add_or_replace_annotation_with_updated_quality_errors(
    quality_layer_created: QualityErrorLayer,
    old_geom: QgsGeometry,
    num_old_items: int,
    new_geom: QgsGeometry,
    expected_geoms_as_wkt: list[str],
):
    assert not old_geom.isNull(), "Input WKT was not valid"
    assert not new_geom.isNull(), "Input WKT was not valid"

    # Setup
    quality_layer_created.add_or_replace_annotation(
        _create_test_quality_error(QualityErrorPriority.FATAL, "1", old_geom), False
    )
    annotation_layer = quality_layer_created.annotation_layer
    assert len(annotation_layer.items()) == num_old_items

    # Test
    quality_layer_created.add_or_replace_annotation(
        _create_test_quality_error(QualityErrorPriority.FATAL, "1", new_geom), False
    )

    assert len(annotation_layer.items()) == len(expected_geoms_as_wkt)

    for key in annotation_layer.items():
        assert annotation_layer.item(key).geometry().asWkt() in expected_geoms_as_wkt


@pytest.mark.parametrize(
    ("geometry", "num_annotations_per_feature"),
    [
        (QgsGeometry.fromWkt("Point(1 1)"), 1),
        (QgsGeometry.fromWkt("MultiPoint((1 1), (2 2))"), 2),
    ],
    ids=["singlegeometry", "multigeometry"],
)
def test_remove_annotations(
    quality_layer_created: QualityErrorLayer,
    geometry: QgsGeometry,
    num_annotations_per_feature: int,
):
    assert not geometry.isNull(), "Input WKT was not valid"

    # Setup
    quality_errors = [
        _create_test_quality_error(QualityErrorPriority.FATAL, "1", geometry),
        _create_test_quality_error(QualityErrorPriority.FATAL, "2", geometry),
    ]
    quality_layer_created.add_or_replace_annotation(quality_errors[0], False)
    quality_layer_created.add_or_replace_annotation(quality_errors[1], False)

    annotation_layer = quality_layer_created.annotation_layer
    assert len(annotation_layer.items()) == 2 * num_annotations_per_feature

    # Test: remove second item
    quality_layer_created.remove_annotations(quality_errors[1:2])

    assert len(annotation_layer.items()) == num_annotations_per_feature
    assert list(quality_layer_created._annotation_ids.keys()) == ["1"]


def test_remove_annotations_with_different_id_prefix_should_not_be_removed(
    quality_layer_created: QualityErrorLayer,
):
    # Setup
    quality_error = _create_test_quality_error(
        QualityErrorPriority.FATAL, "1", QgsGeometry.fromWkt("Point(1 1)")
    )

    quality_layer_created.add_or_replace_annotation(quality_error, False)

    annotation_layer = quality_layer_created.annotation_layer
    assert len(annotation_layer.items()) == 1

    # Test
    quality_layer_created.remove_annotations([quality_error], "test_prefix")

    assert len(annotation_layer.items()) == 1


def test_remove_annotations_if_id_not_found_should_do_nothing(
    quality_layer_created: QualityErrorLayer,
):
    # Test
    quality_layer_created.remove_annotations(
        [_create_test_quality_error(QualityErrorPriority.FATAL, "1", QgsGeometry())]
    )

    assert len(quality_layer_created.annotation_layer.items()) == 0
