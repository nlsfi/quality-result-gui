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

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot

from quality_result_gui.ui.quality_errors_dock import QualityErrorsDockWidget


def test_quality_errors_dock_opens_and_closes(
    qgis_new_project: None,
    qtbot: QtBot,
):

    dock_widget = QualityErrorsDockWidget()
    qtbot.addWidget(dock_widget)

    dock_widget.show()

    assert dock_widget.isVisible() is True

    dock_widget.close()

    assert dock_widget.isVisible() is False


@pytest.mark.parametrize(
    "has_filters_active",
    [True, False],
    ids=[
        "has active filters",
        "does not have active filters",
    ],
)
def test_update_filter_menu_icon_state(mocker: MockerFixture, has_filters_active: bool):

    dock_widget = QualityErrorsDockWidget()
    m_is_any_filter_active = mocker.patch.object(
        dock_widget.filter_menu,
        "is_any_filter_active",
        return_value=has_filters_active,
        autospec=True,
    )

    dock_widget._update_filter_menu_icon_state()

    m_is_any_filter_active.assert_called_once()

    assert dock_widget.filter_button.isDown() is has_filters_active
