"""שרת MCP פשוט למזג אוויר, מבוסס Open-Meteo (חינמי, ללא מפתח API)."""
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "שמיים בהירים", 1: "בהיר ברובו", 2: "מעונן חלקית", 3: "מעונן",
    45: "ערפל", 48: "ערפל קפוא",
    51: "טפטוף קל", 53: "טפטוף", 55: "טפטוף כבד",
    61: "גשם קל", 63: "גשם", 65: "גשם כבד",
    71: "שלג קל", 73: "שלג", 75: "שלג כבד",
    80: "ממטרים קלים", 81: "ממטרים", 82: "ממטרים חזקים",
    95: "סופת רעמים", 96: "סופת רעמים עם ברד", 99: "סופת רעמים חזקה עם ברד",
}


async def _get(url: str, params: dict) -> dict | None:
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None


@mcp.tool()
async def get_weather(city: str, days: int = 3) -> str:
    """מחזיר מזג אוויר נוכחי ותחזית לכמה ימים קדימה לעיר מסוימת.

    Args:
        city: שם העיר (למשל "Tel Aviv" או "תל אביב")
        days: מספר ימי תחזית (1 עד 7)
    """
    days = max(1, min(days, 7))

    geo = await _get(GEO_URL, {"name": city, "count": 1, "language": "he"})
    if not geo or not geo.get("results"):
        return f"לא מצאתי את המיקום '{city}'."
    place = geo["results"][0]

    data = await _get(FORECAST_URL, {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "timezone": "auto",
        "forecast_days": days,
    })
    if not data:
        return "לא הצלחתי להביא נתוני מזג אוויר כרגע."

    cur = data["current"]
    desc = WEATHER_CODES.get(cur["weather_code"], "לא ידוע")
    lines = [
        f"מזג אוויר ב{place['name']}, {place.get('country', '')}",
        f"עכשיו: {cur['temperature_2m']}°C, {desc}, "
        f"לחות {cur['relative_humidity_2m']}%, רוח {cur['wind_speed_10m']} קמ\"ש",
        "",
        "תחזית:",
    ]
    d = data["daily"]
    for i, day in enumerate(d["time"]):
        lines.append(
            f"{day}: {d['temperature_2m_min'][i]}°–{d['temperature_2m_max'][i]}°C, "
            f"{WEATHER_CODES.get(d['weather_code'][i], '')}, "
            f"סיכוי לגשם {d['precipitation_probability_max'][i]}%"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    # stdio: Claude Desktop מפעיל את השרת כתהליך משנה
    mcp.run(transport="stdio")
