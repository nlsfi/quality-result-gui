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

from typing import Any, Iterator, Optional
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from pytestqt.qtbot import QtBot

from quality_result_gui.api.quality_api_client import (
    QualityResultClient,
    QualityResultClientError,
    QualityResultServerError,
)
from quality_result_gui.quality_data_fetcher import (
    BackgroundQualityResultsFetcher,
    CheckStatus,
)


@pytest.fixture()
def quality_result_fetcher(
    mock_api_client: QualityResultClient,
) -> Iterator[BackgroundQualityResultsFetcher]:
    quality_result_fetcher = BackgroundQualityResultsFetcher(
        mock_api_client, poll_interval=10
    )
    yield quality_result_fetcher
    quality_result_fetcher.stop()
    quality_result_fetcher.deleteLater()


@pytest.mark.parametrize(
    (
        "response_from_api",
        "expected_run_status",
        "results_emitted",
        "api_exception",
    ),
    [
        (None, CheckStatus.RESULT_ONGOING, False, None),
        (None, CheckStatus.RESULT_FAILED, False, QualityResultClientError),
        (None, CheckStatus.RESULT_FAILED, False, QualityResultServerError),
        (
            [],
            CheckStatus.RESULT_UPDATED,
            True,
            None,
        ),
    ],
    ids=[
        "ongoing",
        "client_error_raised",
        "server_error_raised",
        "results_updated",
    ],
)
def test_run_background_check_status_signals(
    mocker: MockerFixture,
    quality_result_fetcher: BackgroundQualityResultsFetcher,
    qtbot: QtBot,
    response_from_api: Optional[Any],
    expected_run_status: Optional[CheckStatus],
    results_emitted: bool,
    api_exception: Optional[Exception],
):
    if api_exception is not None:
        mocker.patch.object(
            quality_result_fetcher._api_client,
            "get_results",
            side_effect=api_exception,
        )
    else:
        mocker.patch.object(
            quality_result_fetcher._api_client,
            "get_results",
            return_value=response_from_api,
        )

    mock_callback = MagicMock()

    quality_result_fetcher.results_received.connect(mock_callback)

    with qtbot.waitSignal(
        quality_result_fetcher.status_changed,
        timeout=200,
        check_params_cb=lambda status: status == expected_run_status,
    ):
        quality_result_fetcher.set_checks_enabled(True)

    if results_emitted is True:
        assert mock_callback.call_count > 0
    else:
        mock_callback.assert_not_called()
