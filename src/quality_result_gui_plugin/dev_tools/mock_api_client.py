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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from qgis.core import QgsCoordinateReferenceSystem

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import QualityErrorsByPriority
from quality_result_gui_plugin.dev_tools.response_parser import QualityErrorResponse


@dataclass
class MockQualityResultClient(QualityResultClient):
    json_file_path: Path

    def get_results(self) -> Optional[List[QualityErrorsByPriority]]:
        """
        Retrieve latest quality errors from API

        Returns:
            None: if no results available
            List[QualityErrorsByPriority]: if results available

        Raises:
            QualityResultClientError: if request fails
            QualityResultServerError: if check failed in backend
        """
        return QualityErrorResponse(
            json.loads(self.json_file_path.read_text())
        ).errors_by_priority

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem("EPSG:3067")
