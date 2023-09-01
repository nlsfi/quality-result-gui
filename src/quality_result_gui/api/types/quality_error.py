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

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from qgis.core import QgsGeometry
from qgis_plugin_tools.tools.i18n import tr


class QualityErrorType(Enum):
    ATTRIBUTE = 1
    GEOMETRY = 2
    TOPOLOGY = 3
    CONTINUITY = 4

    @staticmethod
    def get_attribute_error_type_label() -> str:
        return tr("Attribute error")

    @staticmethod
    def get_geometry_error_type_label() -> str:
        return tr("Geometry error")

    @staticmethod
    def get_topology_error_type_label() -> str:
        return tr("Topology error")

    @staticmethod
    def get_continuity_error_type_label() -> str:
        return tr("Continuity error")


ERROR_TYPE_LABEL = {
    QualityErrorType.ATTRIBUTE: lambda: QualityErrorType.get_attribute_error_type_label(),  # noqa: E501
    QualityErrorType.GEOMETRY: lambda: QualityErrorType.get_geometry_error_type_label(),
    QualityErrorType.TOPOLOGY: lambda: QualityErrorType.get_topology_error_type_label(),
    QualityErrorType.CONTINUITY: lambda: QualityErrorType.get_continuity_error_type_label(),  # noqa: E501
}


class QualityErrorPriority(Enum):
    FATAL = 1
    WARNING = 2
    INFO = 3

    @staticmethod
    def get_fatal_error_priority_label() -> str:
        return tr("Fatal")

    @staticmethod
    def get_warning_error_priority_label() -> str:
        return tr("Warning")

    @staticmethod
    def get_info_error_priority_label() -> str:
        return tr("Info")


ERROR_PRIORITY_LABEL = {
    QualityErrorPriority.FATAL: lambda: QualityErrorPriority.get_fatal_error_priority_label(),  # noqa: E501
    QualityErrorPriority.WARNING: lambda: QualityErrorPriority.get_warning_error_priority_label(),  # noqa: E501
    QualityErrorPriority.INFO: lambda: QualityErrorPriority.get_info_error_priority_label(),  # noqa: E501
}


@dataclass
class QualityError:
    priority: QualityErrorPriority
    feature_type: str
    feature_id: str
    error_id: int
    unique_identifier: str
    error_type: QualityErrorType
    attribute_name: Optional[str]
    error_description: str
    error_extra_info: str
    geometry: QgsGeometry
    is_user_processed: bool

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)
