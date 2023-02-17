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

from unittest.mock import ANY

import pytest

from quality_result_gui.quality_errors_filters import FilterMenu


@pytest.fixture()
def simple_menu() -> FilterMenu:
    menu = FilterMenu("Test menu")

    for item in ["b", "c", "a"]:
        menu.add_checkable_action(item)

    return menu


def test_filter_menu_add_and_remove_filter_actions():
    menu_items = ["b", "c", "a"]

    menu = FilterMenu("Test menu")
    assert len(menu.actions()) == 0

    for item in menu_items:
        menu.add_checkable_action(item)

    assert [action.text() for action in menu.actions()] == menu_items

    menu.remove_user_actions()
    assert len(menu.actions()) == 0


@pytest.mark.parametrize(
    "enable",
    [True, False],
    ids=[
        "add select and deselect all",
        "remove select and deselect all",
    ],
)
@pytest.mark.parametrize(
    "option_added_before",
    [True, False],
    ids=[
        "already present",
        "not present",
    ],
)
def test_filter_menu_set_select_all_section_enabled_when_option_not_present(
    simple_menu: FilterMenu, enable: bool, option_added_before: bool
):
    original_menu_items = [action.text() for action in simple_menu.actions()]

    if option_added_before:
        simple_menu.set_select_all_section_enabled(True)

    # Test
    simple_menu.set_select_all_section_enabled(enable)

    if enable:
        assert len(simple_menu.actions()) == 6  # 5 + separator
        assert [action.text() for action in simple_menu.actions()][:2] == [
            "Select all",
            "Deselect all",
        ]
    else:
        assert len(simple_menu.actions()) == 3
        assert [
            action.text() for action in simple_menu.actions()
        ] == original_menu_items


@pytest.mark.parametrize(
    "sort",
    [True, False],
    ids=[
        "sorted",
        "not sorted",
    ],
)
def test_filter_menu_set_sorted(
    simple_menu: FilterMenu,
    sort: bool,
):
    original_menu_items = [action.text() for action in simple_menu.actions()]

    simple_menu.set_sorted(sort)
    if sort is True:
        assert [action.text() for action in simple_menu.actions()] == ["a", "b", "c"]
    else:
        assert [
            action.text() for action in simple_menu.actions()
        ] == original_menu_items


def test_filter_menu_set_sorted_works_with_select_all_option(
    simple_menu: FilterMenu,
):
    simple_menu.set_select_all_section_enabled(True)
    simple_menu.set_sorted(True)
    assert [action.text() for action in simple_menu.actions()] == [
        "Select all",
        "Deselect all",
        ANY,
        "a",
        "b",
        "c",
    ]
