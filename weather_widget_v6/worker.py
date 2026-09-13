from __future__ import annotations

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal()


class WeatherWorker(QRunnable):
    def __init__(self, service, manual_city: str = ""):
        super().__init__()
        self.service = service
        self.manual_city = manual_city
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            lat, lon, city = self.service.locate(self.manual_city)
            self.signals.result.emit(self.service.fetch(lat, lon, city))
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()
