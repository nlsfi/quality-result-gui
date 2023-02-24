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

from typing import Iterator

import pytest
from pytest_mock import MockerFixture
from qgis.core import QgsSettings
from qgis.utils import iface

from quality_result_gui_plugin import classFactory
from quality_result_gui_plugin.dev_tools.dev_tools_dialog import DevToolsDialog
from quality_result_gui_plugin.plugin import QualityResultGuiPlugin


@pytest.fixture()
def plugin(mocker: MockerFixture) -> Iterator[QualityResultGuiPlugin]:
    settings = QgsSettings()
    settings.setValue("locale/userLocale", "en_US")
    settings.sync()

    # pytest-qgis mock iface has no removePluginMenu method, patch that here
    mocker.patch.object(iface, "removePluginMenu", create=True)

    plugin = classFactory(iface)

    assert plugin.show_dev_tools_dialog_action is None
    assert plugin.dev_tools_dialog is None

    plugin.initGui()

    yield plugin

    plugin.unload()


@pytest.mark.skip("Stucks when dialog opens")
def test_dev_tool_action_shows_dialog(
    mocker: MockerFixture, plugin: "QualityResultGuiPlugin"
):
    m_show = mocker.patch.object(DevToolsDialog, "show")
    assert plugin.show_dev_tools_dialog_action is not None

    plugin.show_dev_tools_dialog_action.trigger()

    assert isinstance(plugin.dev_tools_dialog, DevToolsDialog)
    m_show.assert_called_once()
