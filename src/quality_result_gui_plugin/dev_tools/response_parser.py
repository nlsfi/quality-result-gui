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
    QualityErrorType,
)


@dataclass
class QualityErrorResponse:
    quality_results: List[QualityError] = field(init=False)
    _errors_obj: List[Dict[str, Any]]

    def __post_init__(self) -> None:
        self.quality_results = [
            QualityError(
                priority=QualityErrorPriority(error_obj["priority"]),
                feature_type=error_obj["feature_type"],
                feature_id=error_obj["feature_id"],
                error_id=error_obj["error_id"],
                unique_identifier=error_obj["unique_identifier"],
                error_type=QualityErrorType(error_obj["error_type"]),
                attribute_name=error_obj["attribute_name"],
                error_description=error_obj["error_description"],
                error_extra_info=error_obj.get("extra_info", None),
                geometry=QgsGeometry.fromWkt(error_obj["wkt_geom"]),
                is_user_processed=error_obj["is_user_processed"],
            )
            for error_obj in self._errors_obj
        ]
