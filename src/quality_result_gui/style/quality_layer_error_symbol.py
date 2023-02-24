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

from abc import ABC, abstractmethod
from typing import Union

from qgis.core import (
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsSymbol,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor


class BaseSymbol(ABC):
    @abstractmethod
    def to_qgs_symbol(self, geometry_type: QgsWkbTypes.GeometryType) -> QgsSymbol:
        """
        Implement logic to generate the relevant symbol for the given geometry type.
        """
        raise NotImplementedError()

    @staticmethod
    def color_to_rgba_string(color: Union[str, QColor]) -> str:
        return ",".join(map(str, QColor(color).getRgb()))


class ErrorSymbol(BaseSymbol, ABC):
    def to_qgs_symbol(
        self, geometry_type: QgsWkbTypes.GeometryType, highlighted: bool = False
    ) -> QgsSymbol:
        if geometry_type == QgsWkbTypes.PolygonGeometry:
            return self._get_polygon_symbol(highlighted)
        if geometry_type == QgsWkbTypes.LineGeometry:
            return self._get_line_symbol(highlighted)
        if geometry_type == QgsWkbTypes.PointGeometry:
            return self._get_point_symbol(highlighted)
        raise NotImplementedError()

    @abstractmethod
    def _get_polygon_symbol(self, highlighted: bool) -> QgsFillSymbol:
        raise NotImplementedError()

    @abstractmethod
    def _get_line_symbol(self, highlighted: bool) -> QgsLineSymbol:
        raise NotImplementedError()

    @abstractmethod
    def _get_point_symbol(self, highlighted: bool) -> QgsMarkerSymbol:
        raise NotImplementedError()
