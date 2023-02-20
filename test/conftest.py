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

from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture
from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry
from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis_plugin_tools.tools.messages import MsgBar

from quality_result_gui.api.quality_api_client import QualityResultClient
from quality_result_gui.api.types.quality_error import (
    QualityError,
    QualityErrorPriority,
    QualityErrorsByFeature,
    QualityErrorsByFeatureType,
    QualityErrorsByPriority,
    QualityErrorType,
)


class MockQualityResultClient(QualityResultClient):
    def get_results(self) -> Optional[List[QualityErrorsByPriority]]:
        return []

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem("EPSG:3067")


@pytest.fixture()
def mock_api_client() -> QualityResultClient:
    return MockQualityResultClient()


@pytest.fixture()
def bypass_log_if_fails(mocker: MockerFixture) -> None:
    """Throws unhandled exception even though it is caught with log_if_fails"""

    def mock_msg_bar(*args: Any, **kwargs: Any):
        if (
            len(args) > 1
            and isinstance(e := args[1], Exception)
            and (trace := e.__traceback__) is not None
            # Do not bypass exceptions loggers from qgis_plugin_tools tasks.py
            and not trace.tb_frame.f_code.co_filename.endswith("tasks.py")
        ):
            raise e

    mocker.patch.object(MsgBar, "exception", mock_msg_bar)


@pytest.fixture()
def quality_errors() -> List[QualityErrorsByPriority]:
    return [
        QualityErrorsByPriority(
            QualityErrorPriority.FATAL,
            [
                QualityErrorsByFeatureType(
                    "building_part_area",
                    [
                        QualityErrorsByFeature(
                            "building_part_area",
                            "123c1e9b-fade-410d-9b7e-f7ad32317883",
                            [
                                QualityError(
                                    QualityErrorPriority.FATAL,
                                    "building_part_area",
                                    "123c1e9b-fade-410d-9b7e-f7ad32317883",
                                    1,
                                    "1",
                                    QualityErrorType.GEOMETRY,
                                    None,
                                    "Invalid geometry",
                                    "Extra info",
                                    QgsGeometry.fromWkt("POINT ((5 5))"),
                                    False,
                                ),
                                QualityError(
                                    QualityErrorPriority.FATAL,
                                    "building_part_area",
                                    "123c1e9b-fade-410d-9b7e-f7ad32317883",
                                    2,
                                    "2",
                                    QualityErrorType.ATTRIBUTE,
                                    "vtj_prt",
                                    "Invalid value",
                                    "Extra info",
                                    QgsGeometry.fromWkt(
                                        "POLYGON((0 0, 0 5, 5 5, 5 0, 0 0))"
                                    ),
                                    True,
                                ),
                            ],
                        ),
                        QualityErrorsByFeature(
                            "building_part_area",
                            "604eb499-cff7-4d28-bb31-154106480eca",
                            [
                                QualityError(
                                    QualityErrorPriority.FATAL,
                                    "building_part_area",
                                    "604eb499-cff7-4d28-bb31-154106480eca",
                                    3,
                                    "3",
                                    QualityErrorType.ATTRIBUTE,
                                    "height_absolute",
                                    "Invalidvalue",
                                    "Extra info",
                                    QgsGeometry.fromWkt(
                                        "POLYGON((10 10, 10 15, 15 15, 15 10, 10 10))"
                                    ),
                                    False,
                                )
                            ],
                        ),
                    ],
                ),
                QualityErrorsByFeatureType(
                    "chimney_point",
                    [
                        QualityErrorsByFeature(
                            "chimney_point",
                            "7067408f-e7ff-4be4-9def-fe17e9b6bdb2",
                            [
                                QualityError(
                                    QualityErrorPriority.FATAL,
                                    "chimney_point",
                                    "7067408f-e7ff-4be4-9def-fe17e9b6bdb2",
                                    4,
                                    "4",
                                    QualityErrorType.ATTRIBUTE,
                                    "height_relative",
                                    "Invalid value",
                                    "Extra info",
                                    QgsGeometry.fromWkt(
                                        "POLYGON((20 20, 20 25, 25 25, 25 20, 20 20))"
                                    ),
                                    False,
                                )
                            ],
                        ),
                    ],
                ),
            ],
        ),
        QualityErrorsByPriority(
            QualityErrorPriority.WARNING,
            [
                QualityErrorsByFeatureType(
                    "building_part_area",
                    [
                        QualityErrorsByFeature(
                            "building_part_area",
                            "2b89a0b0-33f8-4241-b169-70b4a8c0f941",
                            [
                                QualityError(
                                    QualityErrorPriority.WARNING,
                                    "building_part_area",
                                    "2b89a0b0-33f8-4241-b169-70b4a8c0f941",
                                    102,
                                    "102",
                                    QualityErrorType.ATTRIBUTE,
                                    "floors_above_ground",
                                    "Missing value",
                                    "Extra info",
                                    QgsGeometry.fromWkt(
                                        "POLYGON((30 30, 30 35, 35 35, 35 30, 30 30))"
                                    ),
                                    False,
                                )
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ]


@pytest.fixture()
def error_feature_types() -> list[str]:
    """Unique feature types in quality_errors fixture"""
    return ["building_part_area", "chimney_point"]


@pytest.fixture()
def error_feature_attributes() -> list[str]:
    """Unique feature types in quality_errors fixture"""
    return [
        "floors_above_ground",
        "height_absolute",
        "height_relative",
        "vtj_prt",
    ]


@pytest.fixture()
def get_submenu_from_menu() -> Callable[[QMenu, str], Optional[QMenu]]:
    def _get_submenu_from_menu(menu: QMenu, menu_title: str) -> Optional[QMenu]:
        menu_items = [
            action.menu()
            for action in menu.actions()
            if action.menu() is not None and action.menu().title() == menu_title
        ]

        if len(menu_items) == 1:
            return menu_items[0]
        return None

    return _get_submenu_from_menu


@pytest.fixture()
def get_checked_menu_items() -> Callable[[QMenu], List[str]]:
    def _get_checked_menu_items(menu: QMenu) -> List[str]:
        return [
            action.text()
            for action in menu.actions()
            if action.isCheckable() and action.isChecked()
        ]

    return _get_checked_menu_items


@pytest.fixture()
def get_action_from_menu() -> Callable[[QMenu, str], Optional[QAction]]:
    def _get_action_from_menu(menu: QMenu, action_title: str) -> Optional[QAction]:
        action_items = [
            action for action in menu.actions() if action_title == action.text()
        ]

        if len(action_items) == 1:
            return action_items[0]
        return None

    return _get_action_from_menu


@pytest.fixture()
def is_action_present(
    get_action_from_menu: Callable[[QMenu, str], Optional[QAction]]
) -> Callable[[QMenu, str], bool]:
    def _is_action_present(menu: QMenu, action_title: str) -> bool:
        return bool(get_action_from_menu(menu, action_title))

    return _is_action_present


@pytest.fixture()
def trigger_action(
    get_action_from_menu: Callable[[QMenu, str], Optional[QAction]]
) -> Callable[[QMenu, str], None]:
    def _trigger_action(menu: QMenu, action_title: str) -> None:
        action = get_action_from_menu(menu, action_title)
        assert (
            action is not None
        ), f"Could not find action for menu title: {action_title}"
        action.trigger()

    return _trigger_action
