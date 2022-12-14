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
from enum import Enum, auto
from typing import List, Optional

from qgis.PyQt.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from quality_result_gui.api.quality_api_client import (
    QualityResultClient,
    QualityResultClientError,
    QualityResultServerError,
)

BACKGROUND_POLL_INTERVAL = 30 * 1000

LOGGER = logging.getLogger(__name__)


class CheckStatus(Enum):
    CHECKING = auto()
    RESULT_ONGOING = auto()
    RESULT_UPDATED = auto()
    RESULT_FAILED = auto()


class PollingWorker(QObject):
    status_changed = pyqtSignal(CheckStatus)
    results_received = pyqtSignal(list)

    _timer: Optional[QTimer]
    _poll_interval: int
    _last_ready_run_id: Optional[int]

    def __init__(
        self,
        api_client: QualityResultClient,
        parent: Optional[QObject] = None,
        poll_interval: int = BACKGROUND_POLL_INTERVAL,
    ) -> None:
        super().__init__(parent)
        self._timer = None
        self._poll_interval = poll_interval
        self._last_ready_run_id = None
        self._api_client = api_client

    @pyqtSlot()
    def start(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_api)
        self._timer.start(self._poll_interval)

    @pyqtSlot()
    def _check_api(self) -> None:
        self.status_changed.emit(CheckStatus.CHECKING)

        try:
            results = self._api_client.get_results()

            if results is None:
                self.status_changed.emit(CheckStatus.RESULT_ONGOING)
            else:
                self.status_changed.emit(CheckStatus.RESULT_UPDATED)
                self.results_received.emit(results)

        except (QualityResultClientError, QualityResultServerError) as e:
            LOGGER.warning(
                f"failed to check quality results api: {str(e)}", stack_info=True
            )
            self.status_changed.emit(CheckStatus.RESULT_FAILED)


class BackgroundQualityResultsFetcher(QObject):
    _thread: Optional[QThread]
    _worker: Optional[PollingWorker]
    _poll_interval: int

    _check_requested = pyqtSignal()
    status_changed = pyqtSignal(CheckStatus)
    results_received = pyqtSignal(list)

    def __init__(
        self,
        api_client: QualityResultClient,
        parent: Optional[QObject] = None,
        poll_interval: int = BACKGROUND_POLL_INTERVAL,
    ) -> None:
        super().__init__(parent)
        self._thread = None
        self._worker = None
        self._poll_interval = poll_interval
        self._api_client = api_client

    @pyqtSlot(bool)
    def set_checks_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start()
            self._check_requested.emit()
        else:
            self.stop()

    @pyqtSlot(CheckStatus)
    def _worker_status_changed(self, status: CheckStatus) -> None:
        self.status_changed.emit(status)

    @pyqtSlot(list)
    def _worker_results_received(self, results: List) -> None:
        self.results_received.emit(results)

    @pyqtSlot()
    def start(self) -> None:
        self.stop()
        self._thread = QThread(self)
        self._worker = PollingWorker(self._api_client, None, self._poll_interval)
        self._worker.moveToThread(self._thread)
        self._worker.status_changed.connect(self._worker_status_changed)
        self._worker.results_received.connect(self._worker_results_received)
        self._check_requested.connect(self._worker._check_api)
        self._thread.started.connect(self._worker.start)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @pyqtSlot()
    def stop(self) -> None:
        if self._thread is not None:
            if self._thread.isRunning():
                self._thread.quit()
            self._thread = None
