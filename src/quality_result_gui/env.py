#  Copyright (C) 2023 National Land Survey of Finland
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

import os
from pathlib import Path

IS_DEVELOPMENT_MODE = os.environ.get("IS_DEVELOPMENT_MODE", "0").lower() in (
    "1",
    "true",
    "yes",
)

TEST_JSON_FILE_PATH = (
    str(
        (
            Path(__file__).parent
            / "dev_tools/example_quality_errors/quality_errors.json"
        ).resolve()
    )
    if IS_DEVELOPMENT_MODE
    else None
)
