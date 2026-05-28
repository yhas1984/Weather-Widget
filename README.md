# Weather Widget

Widget de escritorio para Linux que muestra el clima en tiempo real con iconos animados y efectos visuales.

## Características

| Feature | Descripción |
|---------|-------------|
| **Iconos animados** | Sol, luna, nubes, lluvia, nieve, tormenta con animaciones |
| **Clima en tiempo real** | Datos de Open-Meteo, WeatherAPI y 7Timer |
| **Geolocalización** | Detecta tu ubicación por IP automáticamente |
| **Ciudad manual** | Cambiar ciudad con un clic |
| **Expandible** | Clic para ver humedad, viento y sensación térmica |
| **Transparente** | Fondo translúcido, siempre al fondo |
| **Arrastrable** | Mover el widget con el ratón |
| **Auto-inicio** | Se ejecuta automáticamente al iniciar sesión |
| **Múltiples estilos** | Colorido (emoji), plano o minimal |

## Requisitos

- Python 3.8+
- PyQt6
- requests
- Linux (GNOME, KDE o similar)

## Instalación rápida

```bash
git clone https://github.com/yhas1984/Weather-Widget.git
cd Weather-Widget
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python weather_widget.py
```

## Uso

```bash
python weather_widget.py
```

El widget aparecerá en la esquina inferior derecha de la pantalla.

### Interacciones

| Acción | Efecto |
|--------|--------|
| **Clic** | Expandir/colapsar detalles |
| **Arrastrar** | Mover widget |
| **Clic derecho** | Menú de opciones |
| **Cambiar ciudad** | Menú contextual → Cambiar Ciudad |

## APIs Meteorológicas

| API | Prioridad | Descripción |
|-----|-----------|-------------|
| Open-Meteo | 1ª | Gratuita, sin key |
| WeatherAPI | 2ª | Requiere API key |
| 7Timer | 3ª | Gratuita, alternativa |

## Estructura

```
Weather-Widget/
├── weather_widget.py    # Widget principal (PyQt6)
├── appPyQt.py           # Versión alternativa
├── requirements.txt     # Dependencias
└── .gitignore
```

## Solución de problemas

**Error de Qt platform plugin:**
```bash
sudo apt install libxcb-xinerama0
```

**Error de API:**
El widget usa múltiples APIs como respaldo. Si una falla, usa la siguiente automáticamente.

## Licencia

MIT
