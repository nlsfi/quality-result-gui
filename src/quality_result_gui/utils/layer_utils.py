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

from typing import List, Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsLayerTree,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.utils import iface as utils_iface

iface: QgisInterface = utils_iface

SUPPORTED_GEOMETRIES = ["MultiPoint", "MultiLineString", "MultiPolygon"]
BOUNDING_BOX_BUFFER_COEFFICIENT = 0.1


def set_visibility_checked(layer: QgsVectorLayer, checked: bool) -> None:
    root: QgsLayerTree = QgsProject.instance().layerTreeRoot()

    tree_node = root.findLayer(layer.id())
    if tree_node is not None:
        tree_node.setItemVisibilityCheckedRecursive(checked)


def zoom_to_geometries_and_flash(
    geometries: List[QgsGeometry],
    crs: QgsCoordinateReferenceSystem,
    preserve_scale: bool = False,
    min_extent_height: Optional[int] = None,
) -> None:
    view_extent = get_extent_from_geometries(geometries)
    if view_extent is None:
        return

    if crs != QgsProject.instance().crs():
        view_extent = transform_bounding_box(
            view_extent, crs, QgsProject.instance().crs()
        )
    # Only move canvas
    if preserve_scale is True:
        iface.mapCanvas().setCenter(view_extent.center())
    # Move canvas and zoom to geometries
    else:
        if min_extent_height is not None and view_extent.height() < min_extent_height:
            view_extent = (
                QgsGeometry.fromPointXY(view_extent.center())
                .buffer(min_extent_height / 2, 1)
                .boundingBox()
            )
        iface.mapCanvas().setExtent(view_extent)
    iface.mapCanvas().flashGeometries(geometries, crs)


def get_extent_from_geometries(geometries: List[QgsGeometry]) -> Optional[QgsRectangle]:
    if len(geometries) == 0:
        return None

    view_extent = geometries[0].buffer(BOUNDING_BOX_BUFFER_COEFFICIENT, 2).boundingBox()
    for geometry in geometries:
        view_extent.combineExtentWith(geometry.boundingBox())

    return view_extent.buffered(view_extent.height() * BOUNDING_BOX_BUFFER_COEFFICIENT)


def transform_bounding_box(
    rectangle: QgsRectangle,
    crs: str,
    target_crs: str,
) -> QgsRectangle:
    """
    Transform bounding box from one crs to other.
    """
    trans = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem(crs),
        QgsCoordinateReferenceSystem(target_crs),
        QgsProject.instance(),
    )
    return trans.transformBoundingBox(rectangle)
