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

from dataclasses import dataclass, field
from typing import Any, Dict, List

from qgis.core import QgsGeometry

from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorPriority,
    QualityErrorsByFeature,
    QualityErrorsByFeatureType,
    QualityErrorsByPriority,
    QualityErrorType,
)


@dataclass
class QualityErrorResponse:
    errors_by_priority: List[QualityErrorsByPriority] = field(init=False)
    _errors_obj: List[Dict[str, Any]]

    def __post_init__(self) -> None:
        self.errors_by_priority = self._parse_errors_by_priority(self._errors_obj)

    def _parse_errors_by_priority(
        self, errors_obj: List[Dict[str, Any]]
    ) -> List[QualityErrorsByPriority]:
        return [
            QualityErrorsByPriority(
                QualityErrorPriority(error_obj["priority"]),
                self._parse_errors_by_feature_type(
                    QualityErrorPriority(error_obj["priority"]), error_obj["errors"]
                ),
            )
            for error_obj in errors_obj
        ]

    def _parse_errors_by_feature_type(
        self, priority: QualityErrorPriority, errors_obj: List[Dict[str, Any]]
    ) -> List[QualityErrorsByFeatureType]:
        return [
            QualityErrorsByFeatureType(
                error_obj["feature_type"],
                self._parse_errors_by_feature(
                    priority, error_obj["feature_type"], error_obj["errors"]
                ),
            )
            for error_obj in errors_obj
        ]

    def _parse_errors_by_feature(
        self,
        priority: QualityErrorPriority,
        feature_type: str,
        errors_obj: List[Dict[str, Any]],
    ) -> List[QualityErrorsByFeature]:
        return [
            QualityErrorsByFeature(
                feature_type,
                error_obj["feature_id"],
                self._parse_errors(
                    priority, feature_type, error_obj["feature_id"], error_obj["errors"]
                ),
            )
            for error_obj in errors_obj
        ]

    def _parse_errors(
        self,
        priority: QualityErrorPriority,
        feature_type: str,
        feature_id: str,
        errors_obj: List[Dict[str, Any]],
    ) -> List[QualityError]:
        return [
            QualityError(
                priority,
                feature_type,
                feature_id,
                error_obj["error_id"],
                error_obj["unique_identifier"],
                QualityErrorType(error_obj["error_type"]),
                error_obj["attribute_name"],
                error_obj["error_description_fi"],
                error_obj["error_description_sv"],
                error_obj["error_description_en"],
                QgsGeometry.fromWkt(error_obj["wkt_geom"]),
                error_obj["is_user_processed"],
            )
            for error_obj in errors_obj
        ]
