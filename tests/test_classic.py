import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

import weather_widget


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise weather_widget.requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload


class ClassicWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_patch = patch.dict(os.environ, {"XDG_CONFIG_HOME": self.temp.name})
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.temp.cleanup()

    def widget(self):
        result = weather_widget.WeatherWidget()
        result.weather_timer.stop()
        result.position_timer.stop()
        result.anim_timer.stop()
        return result

    def test_open_meteo_uses_real_units_apparent_temperature_and_daylight(self):
        payload = {"current": {
            "temperature_2m": 20.8,
            "apparent_temperature": 17.9,
            "relative_humidity_2m": 61,
            "weather_code": 2,
            "wind_speed_10m": 12.7,
            "surface_pressure": 1012.4,
            "visibility": 8500,
            "is_day": 0,
        }}
        widget = self.widget()
        try:
            with patch("weather_widget.requests.get", return_value=FakeResponse(payload)):
                data = widget.get_openmeteo_weather(1, 2)
            self.assertEqual(data["windspeed"], "12")
            self.assertEqual(data["feelslike"], "17")
            self.assertEqual(data["visibility"], "8.5")
            self.assertFalse(data["is_day"])
        finally:
            widget.close()

    def test_refresh_does_not_block_ui_thread(self):
        widget = self.widget()
        try:
            widget.get_coordinates = lambda: (time.sleep(.15) or (1, 2, "Test"))
            widget.get_openmeteo_weather = lambda *_: {
                "temp": "20", "desc": "Despejado", "raw_desc": "clear",
                "humidity": "50", "windspeed": "10", "feelslike": "20",
                "pressure": "1013", "cloud": 10, "visibility": "10", "is_day": True,
            }
            widget.get_weatherapi_weather = lambda *_: None
            widget.get_7timer_weather = lambda *_: None
            tick = []
            loop = QEventLoop()
            QTimer.singleShot(20, lambda: tick.append(True))
            QTimer.singleShot(60, loop.quit)
            widget.update_weather()
            loop.exec()
            self.assertTrue(tick)
            self.assertTrue(widget.weather_loading)
            deadline = time.monotonic() + 1
            while widget.weather_loading and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertFalse(widget.weather_loading)
            self.assertEqual(widget.city, "Test")
        finally:
            widget.close()

    def test_invalid_manual_city_never_falls_back_to_ip(self):
        widget = self.widget()
        widget.manual_city = "No existe"
        widget.get_coordinates_from_city = lambda _city: None
        try:
            with patch("weather_widget.requests.get") as get:
                with self.assertRaisesRegex(RuntimeError, "No se encontró"):
                    widget.get_coordinates()
                get.assert_not_called()
        finally:
            widget.close()

    def test_obsolete_network_result_is_ignored(self):
        widget = self.widget()
        widget.weather_request_id = 2
        original = dict(widget.weather)
        try:
            widget.weather_updated(1, {"city": "Old", "weather": {"temp": "99"}, "is_day": True})
            self.assertEqual(widget.weather, original)
            self.assertNotEqual(widget.city, "Old")
        finally:
            widget.close()

    def test_expand_and_collapse_resize_the_actual_window(self):
        widget = self.widget()
        try:
            widget.current_height = widget.target_height = 195
            widget.animate()
            self.assertEqual(widget.height(), 195)
            widget.current_height = widget.target_height = 135
            widget.animate()
            self.assertEqual(widget.height(), 135)
        finally:
            widget.close()

    def test_style_interval_and_cache_are_persisted_atomically(self):
        widget = self.widget()
        try:
            widget.set_icon_style("minimal")
            with patch.object(widget, "update_weather"):
                widget.change_update_interval(30)
            widget.save_config("cache", {"city": "Valencia", "weather": {"temp": "22"}})
            data = widget.load_config()
            self.assertEqual(data["icon_style"], "minimal")
            self.assertEqual(data["update_minutes"], 30)
            self.assertEqual(data["cache"]["city"], "Valencia")
            self.assertFalse(list(Path(self.temp.name).glob(".*.json.*")))
        finally:
            widget.close()

    def test_package_launcher_does_not_force_xcb(self):
        script = Path(__file__).parents[1] / "packaging" / "build-deb.sh"
        self.assertNotIn("export QT_QPA_PLATFORM", script.read_text(encoding="utf-8"))

    def test_window_position_is_restored_on_next_start(self):
        first = self.widget()
        first.move(120, 90)
        first.save_position()
        first.close()

        second = self.widget()
        try:
            self.assertEqual((second.x(), second.y()), (120, 90))
            self.assertEqual(second.config["position"], {"x": 120, "y": 90})
        finally:
            second.close()

    def test_unreachable_saved_position_falls_back_to_visible_screen(self):
        config_path = Path(self.temp.name) / "weather_widget_config.json"
        config_path.write_text(
            '{"position": {"x": 999999999999999999999, "y": -999999999999999999999}}',
            encoding="utf-8",
        )
        widget = self.widget()
        try:
            self.assertTrue(
                any(screen.availableGeometry().contains(widget.geometry()) for screen in QApplication.screens())
            )
        finally:
            widget.close()


if __name__ == "__main__":
    unittest.main()
