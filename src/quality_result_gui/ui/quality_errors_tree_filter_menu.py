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


import logging
from typing import TYPE_CHECKING, Optional

from qgis.PyQt.QtWidgets import QAction, QMenu, QWidget
from qgis_plugin_tools.tools.i18n import tr

if TYPE_CHECKING:
    from quality_result_gui.quality_errors_filters import FilterMenu

LOGGER = logging.getLogger(__name__)


class QualityErrorsTreeFilterMenu(QMenu):
    """
    Menu for filtering rows in feature tree view inside quality errors dialog.


    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.reset_separator = self.addSeparator()
        self.reset_action = QAction(tr("Reset filters"), self)
        self.addAction(self.reset_action)

    def add_filter_menu(self, menu: "FilterMenu") -> None:
        """Adds a menu into this menu as a sub menu

        Args:
            menu (FilterMenu): menu to be added
        """

        self.insertMenu(self.reset_separator, menu)  # insert before the separator
        self.reset_action.triggered.connect(menu._select_all)

    def is_any_filter_active(self, menu: Optional[QMenu] = None) -> bool:
        """Checks if any of menu's checkbox are unchecked

        Recursively travels the menu and its submenus to check if any filter is active

        Args:
            parent (Optional[QMenu], optional): Menu to be checked for. If None, checks
              this menu. Defaults to None.

        Returns:
            bool: Returns True if any of checkboxes in this or any sub menu is checked.
              False otherwise
        """

        menu = menu or self
        for action in menu.actions():
            if action.isCheckable() and action.isChecked() is False:
                return True
            sub_menu = action.menu()
            if sub_menu and self.is_any_filter_active(sub_menu):
                return True
        return False
