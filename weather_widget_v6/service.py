from __future__ import annotations

from datetime import datetime
import requests

from .models import DailyForecast, HourlyForecast, WeatherData

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
IP_LOCATION_URL = "https://ipapi.co/json/"


class WeatherService:
    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WeatherWidget/6.0"})

    def geocode(self, city: str, count: int = 5) -> list[dict]:
        response = self.session.get(
            GEOCODING_URL,
            params={"name": city, "count": count, "language": "es", "format": "json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("results", [])

    def locate(self, manual_city: str = "") -> tuple[float, float, str]:
        if manual_city:
            results = self.geocode(manual_city, 1)
            if results:
                item = results[0]
                label = ", ".join(filter(None, [item.get("name"), item.get("admin1")]))
                return float(item["latitude"]), float(item["longitude"]), label
        try:
            response = self.session.get(IP_LOCATION_URL, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("latitude") is not None and data.get("longitude") is not None:
                return float(data["latitude"]), float(data["longitude"]), data.get("city") or "Ubicación actual"
        except requests.RequestException:
            pass
        return 40.4168, -3.7038, "Madrid"

    def fetch(self, lat: float, lon: float, city: str) -> WeatherData:
        current_fields = ",".join([
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation", "weather_code", "cloud_cover", "surface_pressure",
            "wind_speed_10m", "is_day",
        ])
        hourly_fields = ",".join([
            "temperature_2m", "apparent_temperature", "precipitation_probability",
            "weather_code", "is_day",
        ])
        daily_fields = ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "sunrise", "sunset",
        ])
        response = self.session.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": current_fields,
                "hourly": hourly_fields,
                "daily": daily_fields,
                "forecast_days": 7,
                "timezone": "auto",
                "wind_speed_unit": "kmh",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        current = payload["current"]
        hourly = payload["hourly"]
        daily = payload["daily"]

        current_time = datetime.fromisoformat(current["time"])
        now_index = min(range(len(hourly["time"])), key=lambda i: abs(datetime.fromisoformat(hourly["time"][i]) - current_time))
        hourly_items = []
        for i in range(now_index, min(now_index + 12, len(hourly["time"]))):
            hourly_items.append(HourlyForecast(
                time=datetime.fromisoformat(hourly["time"][i]),
                temperature=float(hourly["temperature_2m"][i]),
                apparent_temperature=float(hourly["apparent_temperature"][i]),
                precipitation_probability=int(hourly["precipitation_probability"][i] or 0),
                weather_code=int(hourly["weather_code"][i]),
                is_day=bool(hourly["is_day"][i]),
            ))

        daily_items = []
        for i, date_value in enumerate(daily["time"][:5]):
            daily_items.append(DailyForecast(
                date=datetime.fromisoformat(date_value),
                temperature_max=float(daily["temperature_2m_max"][i]),
                temperature_min=float(daily["temperature_2m_min"][i]),
                precipitation_probability_max=int(daily["precipitation_probability_max"][i] or 0),
                weather_code=int(daily["weather_code"][i]),
                sunrise=datetime.fromisoformat(daily["sunrise"][i]),
                sunset=datetime.fromisoformat(daily["sunset"][i]),
            ))

        probability = int(hourly["precipitation_probability"][now_index] or 0)
        return WeatherData(
            city=city,
            latitude=lat,
            longitude=lon,
            temperature=float(current["temperature_2m"]),
            apparent_temperature=float(current["apparent_temperature"]),
            humidity=int(current["relative_humidity_2m"]),
            wind_speed=float(current["wind_speed_10m"]),
            pressure=float(current["surface_pressure"]),
            cloud_cover=int(current["cloud_cover"]),
            precipitation=float(current["precipitation"]),
            precipitation_probability=probability,
            weather_code=int(current["weather_code"]),
            is_day=bool(current["is_day"]),
            timezone=payload.get("timezone", "auto"),
            updated_at=datetime.now().astimezone(),
            hourly=hourly_items,
            daily=daily_items,
        )
