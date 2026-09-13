CONDITIONS = {
    0: ("Despejado", "clear"), 1: ("Mayormente despejado", "clear"),
    2: ("Parcialmente nublado", "partly"), 3: ("Nublado", "cloudy"),
    45: ("Niebla", "fog"), 48: ("Niebla helada", "fog"),
    51: ("Llovizna ligera", "drizzle"), 53: ("Llovizna", "drizzle"), 55: ("Llovizna intensa", "drizzle"),
    56: ("Llovizna helada", "drizzle"), 57: ("Llovizna helada intensa", "drizzle"),
    61: ("Lluvia ligera", "rain"), 63: ("Lluvia", "rain"), 65: ("Lluvia intensa", "rain"),
    66: ("Lluvia helada", "rain"), 67: ("Lluvia helada intensa", "rain"),
    71: ("Nieve ligera", "snow"), 73: ("Nieve", "snow"), 75: ("Nieve intensa", "snow"), 77: ("Granos de nieve", "snow"),
    80: ("Chubascos ligeros", "rain"), 81: ("Chubascos", "rain"), 82: ("Chubascos intensos", "rain"),
    85: ("Chubascos de nieve", "snow"), 86: ("Nieve intensa", "snow"),
    95: ("Tormenta", "storm"), 96: ("Tormenta con granizo", "storm"), 99: ("Tormenta fuerte", "storm"),
}


def condition(code: int) -> tuple[str, str]:
    return CONDITIONS.get(code, ("Tiempo variable", "cloudy"))


def glyph(code: int, is_day: bool = True) -> str:
    _, kind = condition(code)
    return {
        "clear": "☀" if is_day else "☾",
        "partly": "☀" if is_day else "☾",
        "cloudy": "☁", "fog": "≋", "drizzle": "☂",
        "rain": "☂", "snow": "✻", "storm": "ϟ",
    }.get(kind, "☁")
