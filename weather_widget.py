import sys
import requests
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QBrush, QPolygonF, QRadialGradient
import math
import random
from datetime import datetime
import os
import json
os.environ["QT_QPA_PLATFORM"] = "xcb"

# Configurar DPI antes de crear la aplicación
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

# ---------------- CONFIGURACIÓN ----------------
UPDATE_INTERVAL = 5 * 60 * 1000  # 5 minutos para APIs reales
ICON_STYLE = "emoji"  # "emoji" | "flat" | "minimal"

# APIs gratuitas reales disponibles
WEATHER_APIS = [
    {
        "name": "Open-Meteo",
        "url": "http://api.open-meteo.com/v1/forecast",
        "type": "open-meteo"
    },
    {
        "name": "WeatherAPI Free",
        "url": "http://api.weatherapi.com/v1/current.json",
        "key": "38e4aa14266b819aa523d444730e1161",
        "type": "weatherapi"
    },
    {
        "name": "7Timer",
        "url": "http://www.7timer.info/bin/api.pl",
        "type": "7timer"
    }
]

WEATHER_TRANSLATE = {
    "clear sky": "Despejado", "clear": "Despejado", "sunny": "Soleado",
    "partly cloudy": "Parcialmente Nublado", "few clouds": "Pocas Nubes",
    "scattered clouds": "Nubes Dispersas", "broken clouds": "Nublado",
    "cloudy": "Nublado", "overcast clouds": "Cubierto", "overcast": "Cubierto",
    "mist": "Neblina", "fog": "Niebla", "haze": "Bruma",
    "light rain": "Lluvia Ligera", "moderate rain": "Lluvia Moderada",
    "heavy rain": "Lluvia Intensa", "rain": "Lluvia", "drizzle": "Llovizna",
    "showers": "Chubascos", "thunderstorm": "Tormenta", "thunder": "Tormenta",
    "snow": "Nieve", "light snow": "Nieve Ligera", "heavy snow": "Nevada Intensa",
    "sleet": "Aguanieve", "hail": "Granizo", "windy": "Ventoso"
}

# ---------------- CLASE WIDGET ----------------
class WeatherWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.show_extra_info = False
        self.icon_style = ICON_STYLE
        self.weather = {
            "temp": "N/A", "desc": "Cargando...", "cloud": 0,
            "humidity": "N/A", "windspeed": "N/A", "feelslike": "N/A",
            "raw_desc": "clear", "pressure": "N/A", "visibility": "N/A"
        }
        self.resize(280, 215)
        self.window_id = None
        self.setup_attempts = 0
        self.config = self.load_config()
        self.manual_city = self.config.get('manual_city', None)
        
        # Variables de arrastre y animación
        self.drag_position = QPoint()
        self.press_pos = QPoint()
        self.is_dragging = False
        self.current_height = 135.0
        self.target_height = 135.0
        self.is_closing = False

        # Cargar datos en caché si existen
        cache = self.config.get('cache', {})
        if cache:
            self.weather = cache.get('weather', self.weather)
            self.city = cache.get('city', "Madrid")
            print(f"📦 Datos en caché cargados para {self.city}")
        else:
            self.city = "Madrid"  # Ciudad por defecto

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDock, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setWindowTitle("WeatherWidget-Desktop")

        main = QWidget(self)
        main.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(main)



        self.rain_drops = [{"x": random.randint(0, 40), "y": random.randint(0, 40)} for _ in range(15)]
        self.snow_flakes = [{"x": random.randint(0, 100), "y": random.randint(0, 100),
                           "size": random.uniform(2, 6)} for _ in range(20)]
        self.clouds = [{"x": random.randint(-50, 50), "y": random.randint(-10, 10),
                      "s": random.uniform(0.8,1.3)} for _ in range(4)]
        self.sun_angle, self.lightning_flash = 0, 0
        self.is_day = True

        screen = QApplication.primaryScreen().geometry()
        self.base_pos = QPoint(screen.width() - self.width() - 60, screen.height() - self.height() - 60)
        self.move(self.base_pos)

        self.position_timer = QTimer(self)
        self.position_timer.timeout.connect(self.maintain_position)
        self.position_timer.start(30000)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(UPDATE_INTERVAL)

        QTimer.singleShot(1000, self.update_weather)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(100)

    def maintain_position(self):
        if not self.isVisible():
            self.show()
        self.lower()

    def update_weather(self):
        print("🌤️ Actualizando datos meteorológicos...")
        try:
            coords = self.get_coordinates()
            if coords:
                lat, lon, city = coords
                self.city = city
                print(f"📍 Ubicación: {city} ({lat}, {lon})")

                weather_data = None
                weather_data = self.get_openmeteo_weather(lat, lon)
                if not weather_data:
                    weather_data = self.get_weatherapi_weather(lat, lon)
                if not weather_data:
                    weather_data = self.get_7timer_weather(lat, lon)

                if weather_data:
                    self.weather.update(weather_data)
                    
                    # Guardar en caché
                    self.save_config('cache', {'weather': self.weather, 'city': self.city})
                    
                    print("✅ Datos meteorológicos actualizados")
                    print(f"🌡️ {self.weather['temp']}°C - {self.weather['desc']}")
                else:
                    print("❌ No se pudieron obtener datos meteorológicos")
            else:
                print("❌ No se pudo obtener ubicación")

        except Exception as e:
            print(f"⚠️ Error al actualizar: {e}")

        current_hour = datetime.now().hour
        self.is_day = 6 <= current_hour <= 20
        self.update()

    def get_coordinates(self):
        # 1. Intentar usar ciudad manual si existe
        if self.manual_city:
            print(f"🔎 Buscando coordenadas para ciudad manual: {self.manual_city}")
            coords = self.get_coordinates_from_city(self.manual_city)
            if coords: return coords
            
        # 2. Geolocalización automática por IP
        try:
            response = requests.get("https://ipapi.co/json/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('latitude'), data.get('longitude'), data.get('city', 'Madrid')
        except: pass
        try:
            response = requests.get("http://ip-api.com/json/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('lat'), data.get('lon'), data.get('city', 'Madrid')
        except: pass
        return 40.4168, -3.7038, "Madrid"

    def get_openmeteo_weather(self, lat, lon):
        try:
            params = {
                'latitude': lat, 'longitude': lon,
                'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,surface_pressure',
                'timezone': 'auto'
            }
            response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()['current']
                code = data.get('weather_code', 0)
                desc, raw_desc = self.wmo_to_description(code)
                return {
                    "temp": str(int(data['temperature_2m'])), "desc": desc, "raw_desc": raw_desc,
                    "humidity": str(int(data['relative_humidity_2m'])),
                    "windspeed": str(int(data['wind_speed_10m'] * 3.6)),
                    "feelslike": str(int(data['temperature_2m'] + 2)),
                    "pressure": str(int(data['surface_pressure'])),
                    "cloud": self.weather_code_to_cloud(code), "visibility": "10"
                }
        except Exception as e: print(f"❌ Open-Meteo error: {e}")
        return None

    def get_7timer_weather(self, lat, lon):
        try:
            params = {'lon': lon, 'lat': lat, 'product': 'civil', 'output': 'json'}
            response = requests.get("https://www.7timer.info/bin/api.pl", params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()['dataseries'][0]
                desc, raw_desc = self.seven_timer_to_description(data['weather'])
                return {
                    "temp": str(data['temp2m']), "desc": desc, "raw_desc": raw_desc,
                    "humidity": str(data.get('rh2m', 60)), "windspeed": str(data['wind10m']['speed']),
                    "feelslike": str(data['temp2m'] + 1), "pressure": "1013",
                    "cloud": self.seven_timer_to_cloud(data['weather']), "visibility": "10"
                }
        except Exception as e: print(f"❌ 7Timer error: {e}")
        return None

    def get_weatherapi_weather(self, lat, lon):
        api_key = WEATHER_APIS[1].get("key")
        if not api_key or api_key == "demo": return None
        try:
            params = {'key': api_key, 'q': f"{lat},{lon}", 'aqi': 'no'}
            response = requests.get("http://api.weatherapi.com/v1/current.json", params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()['current']
                desc = data['condition']['text']
                translated = WEATHER_TRANSLATE.get(desc.lower(), desc)
                return {
                    "temp": str(int(data['temp_c'])), "desc": translated, "raw_desc": desc.lower(),
                    "humidity": str(data['humidity']), "windspeed": str(int(data['wind_kph'])),
                    "feelslike": str(int(data['feelslike_c'])), "pressure": str(int(data['pressure_mb'])),
                    "cloud": data['cloud'], "visibility": str(int(data['vis_km']))
                }
        except Exception as e: print(f"❌ WeatherAPI error: {e}")
        return None

    def wmo_to_description(self, code):
        wmo_codes = {
            0: ("Despejado", "clear"),
            1: ("Mayormente Despejado", "clear"),
            2: ("Parcialmente Nublado", "partly cloudy"),
            3: ("Nublado", "cloudy"),
            4: ("Muy Nublado", "overcast"),
            5: ("Niebla Ligera", "fog"),
            6: ("Niebla Moderada", "fog"),
            7: ("Niebla Densa", "fog"),
            8: ("Niebla Ligera con Escarcha", "fog"),
            9: ("Niebla Densa con Escarcha", "fog"),
            10: ("Llovizna Ligera", "drizzle"),
            11: ("Llovizna Moderada", "drizzle"),
            12: ("Llovizna Intensa", "drizzle"),
            13: ("Lluvia Ligera", "light rain"),
            14: ("Lluvia Moderada", "moderate rain"),
            15: ("Lluvia Intensa", "heavy rain"),
            16: ("Chubascos Ligeros", "showers"),
            17: ("Chubascos Moderados", "showers"),
            18: ("Chubascos Intensos", "showers"),
            19: ("Nieve Ligera", "light snow"),
            20: ("Nieve Moderada", "snow"),
            21: ("Nieve Intensa", "heavy snow"),
            22: ("Aguanieve Ligera", "sleet"),
            23: ("Aguanieve Moderada", "sleet"),
            24: ("Aguanieve Intensa", "sleet"),
            25: ("Granizo Ligero", "hail"),
            26: ("Granizo Moderado", "hail"),
            27: ("Granizo Intenso", "hail"),
            28: ("Tormenta Ligera", "thunderstorm"),
            29: ("Tormenta Moderada", "thunderstorm"),
            30: ("Tormenta Intensa", "thunderstorm"),
            31: ("Tormenta con Lluvia Ligera", "thunderstorm"),
            32: ("Tormenta con Lluvia Moderada", "thunderstorm"),
            33: ("Tormenta con Lluvia Intensa", "thunderstorm"),
            34: ("Tormenta con Nieve Ligera", "thunderstorm"),
            35: ("Tormenta con Nieve Moderada", "thunderstorm"),
            36: ("Tormenta con Nieve Intensa", "thunderstorm"),
            45: ("Niebla", "fog"),
            48: ("Niebla Helada", "fog"),
            51: ("Llovizna Ligera", "drizzle"),
            53: ("Llovizna Moderada", "drizzle"),
            55: ("Llovizna Intensa", "drizzle"),
            56: ("Llovizna Helada Ligera", "drizzle"),
            57: ("Llovizna Helada Intensa", "drizzle"),
            61: ("Lluvia Ligera", "light rain"),
            63: ("Lluvia Moderada", "moderate rain"),
            65: ("Lluvia Intensa", "heavy rain"),
            66: ("Lluvia Helada Ligera", "light rain"),
            67: ("Lluvia Helada Intensa", "heavy rain"),
            71: ("Nieve Ligera", "light snow"),
            73: ("Nieve Moderada", "snow"),
            75: ("Nieve Intensa", "heavy snow"),
            77: ("Granos de Nieve", "snow"),
            80: ("Chubascos de Lluvia Ligeros", "showers"),
            81: ("Chubascos de Lluvia Moderados", "showers"),
            82: ("Chubascos de Lluvia Violentos", "showers"),
            85: ("Chubascos de Nieve Ligeros", "snow"),
            86: ("Chubascos de Nieve Intensos", "snow"),
            95: ("Tormenta", "thunderstorm"),
            96: ("Tormenta con Granizo Ligero", "thunderstorm"),
            99: ("Tormenta con Granizo Intenso", "thunderstorm")
        }
        return wmo_codes.get(code, ("Desconocido", "clear"))

    def weather_code_to_cloud(self, code):
        if code in [0, 1]: return 10
        elif code == 2: return 50
        elif code == 3: return 80
        elif code in [45, 48]: return 90
        elif code in range(51, 66): return 70
        elif code in range(71, 76): return 85
        else: return 60

    def seven_timer_to_description(self, weather_type):
        seven_timer_map = {
            'clear': ("Despejado", "clear"), 'pcloudy': ("Parcialmente Nublado", "partly cloudy"),
            'mcloudy': ("Mayormente Nublado", "cloudy"), 'cloudy': ("Nublado", "overcast"),
            'humid': ("Húmedo", "fog"), 'lightrain': ("Lluvia Ligera", "light rain"),
            'oshower': ("Chubascos", "showers"), 'ishower': ("Chubascos Aislados", "showers"),
            'lightsnow': ("Nieve Ligera", "light snow"), 'rain': ("Lluvia", "rain"),
            'snow': ("Nieve", "snow"), 'rainsnow': ("Lluvia y Nieve", "sleet"),
            'ts': ("Tormenta", "thunderstorm"), 'tsrain': ("Tormenta con Lluvia", "thunderstorm")
        }
        return seven_timer_map.get(weather_type, ("Desconocido", "clear"))

    def seven_timer_to_cloud(self, weather_type):
        cloud_map = {
            'clear': 5, 'pcloudy': 40, 'mcloudy': 70, 'cloudy': 90,
            'humid': 80, 'lightrain': 75, 'oshower': 70, 'ishower': 60,
            'lightsnow': 80, 'rain': 85, 'snow': 90, 'rainsnow': 85,
            'ts': 95, 'tsrain': 95
        }
        return cloud_map.get(weather_type, 50)

    def closeEvent(self, event):
        self.is_closing = True
        print("🚪 Cerrando widget...")
        event.accept()

    def hideEvent(self, event):
        if hasattr(self, 'is_closing') and self.is_closing:
            event.accept()
        else:
            # Prevenir que el gestor de ventanas lo oculte al "Mostrar Escritorio"
            event.ignore()
            QTimer.singleShot(0, self.restore_widget)

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                # Prevenir la minimización y restaurar inmediatamente al fondo
                event.ignore()
                QTimer.singleShot(0, self.restore_widget)
        super().changeEvent(event)

    def restore_widget(self):
        if hasattr(self, 'is_closing') and self.is_closing:
            return
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.show()
        self.lower()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.press_pos = event.globalPosition().toPoint()
            self.is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.base_pos = new_pos
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            # Si se movió menos de 5 píxeles, es considerado un clic
            dist = (event.globalPosition().toPoint() - self.press_pos).manhattanLength()
            if dist < 5:
                self.show_extra_info = not self.show_extra_info
                self.target_height = 195.0 if self.show_extra_info else 135.0
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("🎨 Estilo Colorido", lambda: setattr(self, 'icon_style', 'emoji') or self.update())
        menu.addAction("📱 Estilo Plano", lambda: setattr(self, 'icon_style', 'flat') or self.update())
        menu.addAction("⚪ Estilo Minimal", lambda: setattr(self, 'icon_style', 'minimal') or self.update())
        menu.addSeparator()
        menu.addAction("🔄 Actualizar Clima", self.update_weather)
        menu.addAction("🏙️ Cambiar Ciudad", self.prompt_change_city)
        menu.addAction("📍 Reposicionar", lambda: self.move(self.base_pos))
        menu.addSeparator()

        interval_menu = menu.addMenu("⏱️ Intervalo de Actualización")
        current_minutes = self.weather_timer.interval() // 60000
        for minutes in [5, 10, 15, 30, 60]:
            action = interval_menu.addAction(f"{minutes} min")
            action.setCheckable(True)
            if current_minutes == minutes: action.setChecked(True)
            action.triggered.connect(lambda _, m=minutes: self.change_update_interval(m))

        menu.exec(event.globalPos())

    def change_update_interval(self, minutes):
        new_interval = minutes * 60 * 1000
        self.weather_timer.setInterval(new_interval)
        print(f"⏱️ Intervalo cambiado a {minutes} minutos")
        self.update_weather()

    def animate(self):
        for drop in self.rain_drops: drop["y"] = (drop["y"] + 6) % 60
        for flake in self.snow_flakes:
            flake["y"] = (flake["y"] + 2) % 120
            flake["x"] += math.sin(flake["y"] * 0.1) * 0.5
        for cloud in self.clouds:
            cloud["x"] += 0.3
            if cloud["x"] > 150: cloud["x"] = -80
        self.sun_angle = (self.sun_angle + 1.5) % 360
        if "tormenta" in self.weather["desc"].lower():
            self.lightning_flash = (self.lightning_flash + 1) % 120
            
        # Interpolación suave de altura para el efecto expandible
        self.current_height += (self.target_height - self.current_height) * 0.25
        
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        icon_type = self.decide_icon()
        if self.icon_style == "emoji": self.draw_weather_icon(p, 85, 75, icon_type)
        else: self.draw_simple_weather(p, 85, 75, icon_type)
        self.draw_weather_text(p)

    def decide_icon(self):
        desc = self.weather["raw_desc"]
        cloud = self.weather["cloud"]
        if any(k in desc for k in ["thunder", "storm"]): return "thunderstorm"
        if any(k in desc for k in ["snow", "blizzard"]): return "snow"
        if any(k in desc for k in ["rain", "shower", "drizzle"]): return "rain"
        if any(k in desc for k in ["mist", "fog"]): return "fog"
        if "hail" in desc: return "hail"
        if cloud < 20: return "clear"
        if cloud < 50: return "partly_cloudy"
        if cloud < 80: return "cloudy"
        return "overcast"

    def draw_weather_icon(self, p, x, y, icon_type):
        actions = {
            "clear": lambda: self.draw_sun(p, x, y, 28) if self.is_day else self.draw_moon_and_stars(p, x, y),
            "partly_cloudy": lambda: (self.draw_sun(p, x-15, y-10, 22) if self.is_day else self.draw_moon_and_stars(p, x-15, y-10), self.draw_stylized_clouds(p, x, y, 0.8)),
            "cloudy": lambda: self.draw_stylized_clouds(p, x, y, 1.0),
            "overcast": lambda: self.draw_heavy_clouds(p, x, y),
            "rain": lambda: (self.draw_rain_clouds(p, x, y), self.draw_animated_rain(p, x, y)),
            "thunderstorm": lambda: (self.draw_storm_clouds(p, x, y), self.draw_lightning(p, x, y), self.draw_animated_rain(p, x, y)),
            "snow": lambda: (self.draw_snow_clouds(p, x, y), self.draw_animated_snow(p, x, y)),
            "fog": lambda: self.draw_fog_effect(p, x, y),
            "hail": lambda: (self.draw_hail_clouds(p, x, y), self.draw_hail(p, x, y))
        }
        if icon_type in actions: actions[icon_type]()

    def draw_sun(self, p, x, y, r):
        grad = QRadialGradient(x, y, r)
        grad.setColorAt(0, QColor(255,255,180)); grad.setColorAt(1, QColor(255,180,50))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(x-r), int(y-r), int(2*r), int(2*r))
        p.setPen(QPen(QColor(255,200,80,180), 3, cap=Qt.PenCapStyle.RoundCap))
        for i in range(12):
            a = i*30+self.sun_angle
            sx, sy = x+math.cos(math.radians(a))*(r+8), y+math.sin(math.radians(a))*(r+8)
            ex, ey = x+math.cos(math.radians(a))*(r+18), y+math.sin(math.radians(a))*(r+18)
            p.drawLine(int(sx),int(sy),int(ex),int(ey))

    def draw_moon_and_stars(self, p, x, y):
        grad = QRadialGradient(x-5, y-5, 25)
        grad.setColorAt(0, QColor(240,240,255)); grad.setColorAt(1, QColor(200,200,240))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x-25,y-25,50,50)
        sgrad = QRadialGradient(x+8, y-5, 20)
        sgrad.setColorAt(0, QColor(0,0,0,100)); sgrad.setColorAt(1, QColor(0,0,0,0))
        p.setBrush(QBrush(sgrad)); p.drawEllipse(x-5,y-25,40,50)
        for i, (sx, sy) in enumerate([(x+35,y-20), (x-40,y-15), (x+25,y+30), (x-30,y+25)]):
            alpha = int(150+100*math.sin((self.sun_angle+i*90)*math.pi/180))
            self.draw_star(p, sx, sy, 4, QColor(255,255,200,alpha))

    def draw_star(self, p, x, y, s, color):
        p.setPen(QPen(color,2))
        p.drawLine(int(x),int(y-s),int(x),int(y+s)); p.drawLine(int(x-s),int(y),int(x+s),int(y))
        p.drawLine(int(x-s*.7),int(y-s*.7),int(x+s*.7),int(y+s*.7)); p.drawLine(int(x-s*.7),int(y+s*.7),int(x+s*.7),int(y-s*.7))

    def draw_stylized_clouds(self, p, x, y, scale):
        grad = QLinearGradient(x,y-20*scale,x,y+20*scale)
        grad.setColorAt(0, QColor(250,250,250,200)); grad.setColorAt(1, QColor(200,200,200,180))
        p.setBrush(QBrush(grad)); p.setPen(QPen(QColor(180,180,180,100),1))
        for cx,cy,r in [(x-25*scale,y-5*scale,30*scale),(x+5*scale,y-15*scale,35*scale),(x+25*scale,y-8*scale,28*scale)]:
            p.drawEllipse(QPointF(cx,cy), r, r)

    def draw_heavy_clouds(self, p, x, y):
        grad = QLinearGradient(x,y-25,x,y+25)
        grad.setColorAt(0,QColor(120,120,120,220)); grad.setColorAt(1,QColor(80,80,80,200))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        for i in range(5): p.drawEllipse(QPointF(x+(i-2)*15,y+math.sin(i)*5),20+(i%2)*10,20+(i%2)*10)

    def draw_rain_clouds(self, p, x, y):
        grad = QLinearGradient(x,y-20,x,y+20)
        grad.setColorAt(0,QColor(80,80,100,220)); grad.setColorAt(1,QColor(120,120,140,180))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x-35,y-15,70,30); p.drawEllipse(x-25,y-20,50,25)

    def draw_animated_rain(self, p, x, y):
        p.setPen(QPen(QColor(100,150,255,180), 2, cap=Qt.PenCapStyle.RoundCap))
        for drop in self.rain_drops:
            dx, dy = x+drop["x"]-20, y+drop["y"]+15
            p.drawLine(int(dx),int(dy),int(dx-2),int(dy+8))

    def draw_storm_clouds(self, p, x, y):
        grad = QLinearGradient(x,y-25,x,y+25)
        grad.setColorAt(0,QColor(40,40,50,240)); grad.setColorAt(1,QColor(30,30,40,220))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x-40,y-20,80,40); p.drawEllipse(x-30,y-25,60,35)

    def draw_lightning(self, p, x, y):
        if self.lightning_flash < 10:
            p.setPen(QPen(QColor(255,255,100,200),3))
            p.drawPolyline(QPolygonF([QPointF(x+5,y+10),QPointF(x-3,y+25),QPointF(x+8,y+25),QPointF(x-5,y+40)]))

    def draw_snow_clouds(self, p, x, y):
        grad = QLinearGradient(x,y-15,x,y+15)
        grad.setColorAt(0,QColor(200,200,220,200)); grad.setColorAt(1,QColor(160,160,180,180))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x-30,y-12,60,24); p.drawEllipse(x-20,y-18,40,20)

    def draw_animated_snow(self, p, x, y):
        p.setBrush(QBrush(QColor(255,255,255,200))); p.setPen(Qt.PenStyle.NoPen)
        for flake in self.snow_flakes: p.drawEllipse(QPointF(x+flake["x"]-50,y+flake["y"]-20),flake["size"],flake["size"])

    def draw_fog_effect(self, p, x, y):
        for i in range(4):
            alpha = 100-i*20
            grad = QLinearGradient(x,y-15+i*8,x,y-5+i*8)
            grad.setColorAt(0,QColor(200,200,200,alpha)); grad.setColorAt(1,QColor(220,220,220,alpha+20))
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x-35,y-15+i*6,70,8,4,4)

    def draw_hail_clouds(self, p, x, y): self.draw_rain_clouds(p, x, y)

    def draw_hail(self, p, x, y):
        p.setBrush(QBrush(QColor(200,220,255,180))); p.setPen(QPen(QColor(150,180,220,150),1))
        for i in range(8):
            hx = x+(i*15)%40-20; hy = y+20+(self.sun_angle+i*20)%30
            size = 4+(i%3); p.drawEllipse(int(hx),int(hy),size,size)

    def draw_simple_weather(self, p, cx, cy, icon_type):
        p.setBrush(QBrush(QColor(200,200,200))); p.setPen(QPen(QColor(150,150,150),2))
        p.drawEllipse(cx-20,cy-10,40,20)

    def draw_weather_text(self, p):
        p.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255)); p.drawText(155, 48, self.city)

        temp_str = f"{self.weather['temp']}°C"
        try: t = int(self.weather['temp'])
        except (ValueError, TypeError): t = None

        temp_color = QColor(255, 255, 255)
        if t is not None:
            if t <= 0: temp_color = QColor(100, 180, 255)
            elif t <= 15: temp_color = QColor(120, 220, 255)
            elif t <= 25: temp_color = QColor(255, 210, 100)
            else: temp_color = QColor(255, 140, 90)

        p.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        p.setPen(temp_color); p.drawText(155, 88, temp_str)

        p.setFont(QFont("Inter", 11))
        p.setPen(QColor(220, 225, 235)); p.drawText(155, 112, self.weather["desc"])

        if self.current_height > 155:
            p.setFont(QFont("Inter", 10))
            p.setPen(QColor(210, 215, 225))
            # Coordenadas limpias y elegantes con iconos emoji
            p.drawText(24, 155, f"💧 Humedad: {self.weather['humidity']}%")
            p.drawText(24, 172, f"💨 Viento: {self.weather['windspeed']} km/h")
            p.drawText(24, 189, f"🌡️ Sensación: {self.weather['feelslike']}°C")

    # ------------------- NUEVAS FUNCIONES PARA SELECCIÓN DE CIUDAD -------------------

    def load_config(self):
        """Carga la configuración guardada (ciudad manual, estilo, etc)"""
        try:
            config_path = os.path.expanduser("~/.config/weather_widget_config.json")
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    return json.load(f)
        except: pass
        return {}

    def save_config(self, key, value):
        """Guarda una configuración específica"""
        try:
            config_path = os.path.expanduser("~/.config/weather_widget_config.json")
            config = self.load_config()
            config[key] = value
            import json
            with open(config_path, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error guardando config: {e}")

    def prompt_change_city(self):
        """Muestra un diálogo para cambiar la ciudad manualmente"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, 'Cambiar Ciudad', 'Introduce el nombre de tu ciudad:')
        if ok and text:
            self.manual_city = text
            self.save_config('manual_city', text)
            print(f"🏙️ Ciudad cambiada manualmente a: {text}")
            self.update_weather()

    def get_coordinates_from_city(self, city_name):
        """Obtiene coordenadas a partir del nombre de una ciudad (Geocoding)"""
        try:
            # Usando Open-Meteo Geocoding API (Gratuita y no requiere key)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=es&format=json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    return result['latitude'], result['longitude'], result['name']
        except Exception as e:
            print(f"Error en geocoding: {e}")
        return None

    def create_autostart_entry(self):
        """Creates a .desktop entry for autostart on Linux"""
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            if not os.path.exists(autostart_dir):
                os.makedirs(autostart_dir)
            
            # Determine executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exec_cmd = f'"{sys.executable}"'
            else:
                # Running as script
                exec_cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            
            desktop_file = os.path.join(autostart_dir, "WeatherWidget.desktop")
            
            content = f"""[Desktop Entry]
Type=Application
Name=WeatherWidget
Exec={exec_cmd}
Icon=weather-overcast
Comment=Desktop Weather Widget
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
            with open(desktop_file, "w") as f:
                f.write(content)
            print(f"✅ Autostart configurado en: {desktop_file}")
            
        except Exception as e:
            print(f"⚠️ Error configurando autostart: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        # Configure autostart on first show
        QTimer.singleShot(1000, self.create_autostart_entry)

# ---------------- EJECUCIÓN ----------------
if __name__ == "__main__":
    if hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except: pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    w = WeatherWidget()
    w.show()
    w.lower()

    print("🚀 Widget de clima DESKTOP iniciado")

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n🛑 Cerrando widget...")
        w.close()
        app.quit()
        sys.exit(0)
