import sys

from PyQt6.QtWidgets import QApplication

from .widget import PremiumWeatherWidget


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Weather Widget")
    app.setOrganizationName("WeatherWidget")
    widget = PremiumWeatherWidget()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
