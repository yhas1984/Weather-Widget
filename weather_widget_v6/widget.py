from __future__ import annotations

import math
import random
from datetime import datetime

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QThreadPool, QTimer, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QInputDialog, QMainWindow, QMenu

from .conditions import condition, glyph
from .config import load_settings, save_settings
from .service import WeatherService
from .worker import WeatherWorker


class PremiumWeatherWidget(QMainWindow):
    COLLAPSED = 190
    EXPANDED = 430

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.service = WeatherService()
        self.pool = QThreadPool.globalInstance()
        self.weather = None
        self.loading = False
        self.offline_message = ""
        self.expanded = False
        self.current_height = float(self.COLLAPSED)
        self.target_height = float(self.COLLAPSED)
        self.drag_origin = QPoint()
        self.dragging = False
        self.phase = 0.0
        self.particles = [
            {"x": random.random(), "y": random.random(), "speed": random.uniform(.0015, .005), "size": random.uniform(1.2, 3.0), "depth": random.random()}
            for _ in range(34)
        ]

        self.setWindowTitle("Weather Widget 6")
        self.resize(360, self.COLLAPSED)
        self.setMinimumWidth(340)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        screen = self.screen().availableGeometry()
        saved = self.settings.get("position")
        if isinstance(saved, list) and len(saved) == 2:
            self.move(int(saved[0]), int(saved[1]))
        else:
            self.move(screen.right() - self.width() - 28, screen.bottom() - self.height() - 28)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(max(5, int(self.settings.get("update_minutes", 15))) * 60_000)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(50)

        QTimer.singleShot(150, self.refresh_weather)

    def refresh_weather(self):
        if self.loading:
            return
        self.loading = True
        self.offline_message = ""
        worker = WeatherWorker(self.service, self.settings.get("manual_city", ""))
        worker.signals.result.connect(self.on_weather)
        worker.signals.error.connect(self.on_weather_error)
        worker.signals.finished.connect(self.on_worker_finished)
        self.pool.start(worker)
        self.update()

    def on_weather(self, weather):
        self.weather = weather
        self.offline_message = ""
        self.update()

    def on_weather_error(self, message: str):
        self.offline_message = "Sin conexión · mostrando último estado" if self.weather else "No se pudo actualizar el clima"
        self.update()

    def on_worker_finished(self):
        self.loading = False
        self.update()

    def animate(self):
        animations = bool(self.settings.get("animations", True))
        if not animations or not self.isVisible():
            return
        self.phase = (self.phase + .018) % (math.pi * 2)
        for particle in self.particles:
            particle["y"] += particle["speed"]
            if particle["y"] > 1.08:
                particle["y"] = -.05
                particle["x"] = random.random()
        delta = self.target_height - self.current_height
        if abs(delta) > .25:
            self.current_height += delta * .18
            self.resize(self.width(), int(self.current_height))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.dragging = False
            self._press_global = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if (event.globalPosition().toPoint() - self._press_global).manhattanLength() > 5:
                self.dragging = True
                self.move(event.globalPosition().toPoint() - self.drag_origin)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self.settings["position"] = [self.x(), self.y()]
                save_settings(self.settings)
            else:
                self.expanded = not self.expanded
                self.target_height = float(self.EXPANDED if self.expanded else self.COLLAPSED)
            self.dragging = False

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        refresh = menu.addAction("Actualizar ahora")
        city = menu.addAction("Cambiar ciudad…")
        menu.addSeparator()
        theme_menu = menu.addMenu("Apariencia")
        atmospheric = theme_menu.addAction("Atmospheric")
        glass = theme_menu.addAction("Glass")
        minimal = theme_menu.addAction("Minimal")
        animation = menu.addAction("Animaciones")
        animation.setCheckable(True)
        animation.setChecked(bool(self.settings.get("animations", True)))
        menu.addSeparator()
        quit_action = menu.addAction("Salir")
        chosen = menu.exec(event.globalPos())
        if chosen == refresh:
            self.refresh_weather()
        elif chosen == city:
            self.change_city()
        elif chosen in (atmospheric, glass, minimal):
            self.settings["theme"] = chosen.text()
            save_settings(self.settings)
            self.update()
        elif chosen == animation:
            self.settings["animations"] = animation.isChecked()
            save_settings(self.settings)
            self.update()
        elif chosen == quit_action:
            self.close()

    def change_city(self):
        city, ok = QInputDialog.getText(self, "Cambiar ciudad", "Ciudad:", text=self.settings.get("manual_city", ""))
        if ok and city.strip():
            self.settings["manual_city"] = city.strip()
            save_settings(self.settings)
            self.refresh_weather()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(6, 6, self.width() - 12, self.height() - 12)
        self.draw_card(painter, card)
        if not self.weather:
            self.draw_loading(painter, card)
            return
        self.draw_atmosphere(painter, card)
        self.draw_header(painter)
        self.draw_hero(painter)
        if self.current_height > 255:
            opacity = min(1.0, max(0.0, (self.current_height - 245) / 80))
            painter.setOpacity(opacity)
            self.draw_hourly(painter)
            self.draw_details(painter)
            if self.current_height > 365:
                self.draw_daily(painter)
            painter.setOpacity(1.0)

    def draw_card(self, p: QPainter, rect: QRectF):
        theme = self.settings.get("theme", "Atmospheric")
        path = QPainterPath()
        path.addRoundedRect(rect, 24, 24)
        if theme == "Minimal":
            p.fillPath(path, QColor(12, 16, 24, 170))
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            if self.weather:
                _, kind = condition(self.weather.weather_code)
                palettes = {
                    "clear": ((20, 72, 128), (19, 27, 55)), "partly": ((39, 76, 112), (24, 31, 51)),
                    "cloudy": ((54, 66, 82), (24, 31, 43)), "fog": ((72, 82, 91), (35, 42, 52)),
                    "rain": ((32, 59, 82), (18, 27, 42)), "drizzle": ((38, 64, 84), (20, 31, 45)),
                    "snow": ((75, 104, 128), (35, 51, 70)), "storm": ((42, 38, 66), (18, 20, 35)),
                }
                start, end = palettes.get(kind, palettes["cloudy"])
                if not self.weather.is_day:
                    start = tuple(max(8, int(c * .48)) for c in start)
                    end = tuple(max(5, int(c * .62)) for c in end)
            else:
                start, end = (42, 60, 88), (17, 23, 37)
            gradient.setColorAt(0, QColor(*start, 238))
            gradient.setColorAt(1, QColor(*end, 245))
            p.fillPath(path, gradient)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1))
        p.drawPath(path)

    def draw_atmosphere(self, p: QPainter, rect: QRectF):
        if self.settings.get("theme") != "Atmospheric" or not self.settings.get("animations", True):
            return
        _, kind = condition(self.weather.weather_code)
        p.save()
        p.setClipRect(rect)
        if kind == "clear":
            glow = QRadialGradient(rect.right() - 48, rect.top() + 40, 105)
            glow.setColorAt(0, QColor(255, 205, 110, 58 if self.weather.is_day else 15))
            glow.setColorAt(1, QColor(255, 205, 110, 0))
            p.fillRect(rect, glow)
        elif kind in ("rain", "drizzle", "storm"):
            p.setPen(QPen(QColor(185, 215, 255, 50), 1.2))
            for particle in self.particles[:22]:
                x = rect.left() + particle["x"] * rect.width()
                y = rect.top() + particle["y"] * rect.height()
                p.drawLine(QPointF(x, y), QPointF(x - 4, y + 13 + 7 * particle["depth"]))
        elif kind == "snow":
            p.setPen(Qt.PenStyle.NoPen)
            for particle in self.particles:
                x = rect.left() + ((particle["x"] + math.sin(self.phase + particle["y"] * 8) * .015) % 1) * rect.width()
                y = rect.top() + particle["y"] * rect.height()
                p.setBrush(QColor(255, 255, 255, int(45 + 90 * particle["depth"])))
                s = particle["size"]
                p.drawEllipse(QPointF(x, y), s, s)
        p.restore()

    def draw_header(self, p: QPainter):
        p.setPen(QColor(244, 247, 252))
        p.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        city = self.weather.city.split(",")[0]
        p.drawText(25, 36, city)
        p.setFont(QFont("Inter", 8))
        p.setPen(QColor(222, 230, 240, 165))
        status = "Actualizando…" if self.loading else (self.offline_message or f"Actualizado hace {self.weather.age_minutes} min")
        p.drawText(25, 54, status)
        p.setPen(QColor(255, 255, 255, 145))
        p.setFont(QFont("Inter", 14))
        p.drawText(self.width() - 43, 38, "↻")

    def draw_hero(self, p: QPainter):
        desc, _ = condition(self.weather.weather_code)
        p.setPen(QColor(255, 255, 255, 235))
        p.setFont(QFont("Inter", 48, QFont.Weight.Light))
        p.drawText(25, 130, glyph(self.weather.weather_code, self.weather.is_day))
        p.setFont(QFont("Inter", 42, QFont.Weight.DemiBold))
        p.drawText(112, 118, f"{round(self.weather.temperature)}°")
        p.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        p.setPen(QColor(230, 235, 243, 210))
        p.drawText(114, 141, desc)
        p.setFont(QFont("Inter", 9))
        p.setPen(QColor(218, 226, 238, 170))
        p.drawText(25, 169, f"Sensación {round(self.weather.apparent_temperature)}°   ·   Lluvia {self.weather.precipitation_probability}%   ·   Viento {round(self.weather.wind_speed)} km/h")

    def draw_hourly(self, p: QPainter):
        items = self.weather.hourly[:6]
        if not items:
            return
        top = 208
        p.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        p.setPen(QColor(225, 232, 242, 150))
        p.drawText(25, top, "PRÓXIMAS HORAS")
        cell_w = (self.width() - 44) / len(items)
        for i, item in enumerate(items):
            x = 22 + i * cell_w
            if i == 0:
                p.setBrush(QColor(255, 255, 255, 18)); p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(x, top + 12, cell_w - 5, 72), 12, 12)
            p.setPen(QColor(230, 235, 244, 175)); p.setFont(QFont("Inter", 8))
            p.drawText(int(x + 7), top + 31, "Ahora" if i == 0 else item.time.strftime("%Hh"))
            p.setPen(QColor(255, 255, 255, 225)); p.setFont(QFont("Inter", 14))
            p.drawText(int(x + 9), top + 52, glyph(item.weather_code, item.is_day))
            p.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            p.drawText(int(x + 7), top + 72, f"{round(item.temperature)}°")

    def draw_details(self, p: QPainter):
        y = 315
        metrics = [("Humedad", f"{self.weather.humidity}%"), ("Lluvia", f"{self.weather.precipitation_probability}%"), ("Viento", f"{round(self.weather.wind_speed)} km/h")]
        w = (self.width() - 50) / 3
        for i, (label, value) in enumerate(metrics):
            x = 22 + i * w
            p.setBrush(QColor(255, 255, 255, 13)); p.setPen(QPen(QColor(255, 255, 255, 18), 1))
            p.drawRoundedRect(QRectF(x, y - 17, w - 6, 50), 12, 12)
            p.setPen(QColor(220, 228, 239, 140)); p.setFont(QFont("Inter", 7))
            p.drawText(int(x + 9), y, label.upper())
            p.setPen(QColor(250, 251, 253, 220)); p.setFont(QFont("Inter", 9, QFont.Weight.DemiBold))
            p.drawText(int(x + 9), y + 19, value)

    def draw_daily(self, p: QPainter):
        y = 387
        p.setPen(QColor(225, 232, 242, 145)); p.setFont(QFont("Inter", 8, QFont.Weight.DemiBold))
        p.drawText(25, y, "PRÓX