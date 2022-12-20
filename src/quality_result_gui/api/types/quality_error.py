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
from typing import Any, List, Optional

from qgis.core import QgsGeometry
from qgis_plugin_tools.tools.i18n import tr


class QualityErrorType(Enum):
    ATTRIBUTE = 1
    GEOMETRY = 2
    TOPOLOGY = 3
    CONTINUITY = 4


ERROR_TYPE_LABEL = {
    QualityErrorType.ATTRIBUTE: tr("Attribute error"),
    QualityErrorType.GEOMETRY: tr("Geometry error"),
    QualityErrorType.TOPOLOGY: tr("Topology error"),
    QualityErrorType.CONTINUITY: tr("Continuity error"),
}


class QualityErrorPriority(Enum):
    FATAL = 1
    WARNING = 2
    INFO = 3


ERROR_PRIORITY_LABEL = {
    QualityErrorPriority.FATAL: tr("Fatal"),
    QualityErrorPriority.WARNING: tr("Warning"),
    QualityErrorPriority.INFO: tr("Info"),
}


USER_PROCESSED_LABEL = tr("Show user processed")


@dataclass
class QualityError:
    priority: QualityErrorPriority
    feature_type: str
    feature_id: str
    error_id: int
    unique_identifier: str
    error_type: QualityErrorType
    attribute_name: Optional[str]
    error_description_fi: str
    error_description_sv: str
    error_description_en: str
    geometry: QgsGeometry
    is_user_processed: bool

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


@dataclass
class QualityErrorsByFeature:
    feature_type: str
    feature_id: str
    errors: List[QualityError]


@dataclass
class QualityErrorsByFeatureType:
    feature_type: str
    errors: List[QualityErrorsByFeature]

    def get_all_errors(self) -> List[QualityError]:
        errors = [errors_by_feature.errors for errors_by_feature in self.errors]
        return [item for sub_list in errors for item in sub_list]


@dataclass
class QualityErrorsByPriority:
    priority: QualityErrorPriority
    errors: List[QualityErrorsByFeatureType]

    def get_all_errors(self) -> List[QualityError]:
        errors = [
            errors_by_feature_type.get_all_errors()
            for errors_by_feature_type in self.errors
        ]
        return [item for sub_list in errors for item in sub_list]
