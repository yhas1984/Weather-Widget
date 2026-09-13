from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class HourlyForecast:
    time: datetime
    temperature: float
    apparent_temperature: float
    precipitation_probability: int
    weather_code: int
    is_day: bool


@dataclass(slots=True)
class DailyForecast:
    date: datetime
    temperature_max: float
    temperature_min: float
    precipitation_probability_max: int
    weather_code: int
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None


@dataclass(slots=True)
class WeatherData:
    city: str
    latitude: float
    longitude: float
    temperature: float
    apparent_temperature: float
    humidity: int
    wind_speed: float
    pressure: float
    cloud_cover: int
    precipitation: float
    precipitation_probability: int
    weather_code: int
    is_day: bool
    timezone: str
    updated_at: datetime
    hourly: list[HourlyForecast] = field(default_factory=list)
    daily: list[DailyForecast] = field(default_factory=list)
    source: str = "Open-Meteo"
    stale: bool = False

    @property
    def age_minutes(self) -> int:
        return max(0, int((datetime.now().astimezone() - self.updated_at.astimezone()).total_seconds() // 60))
