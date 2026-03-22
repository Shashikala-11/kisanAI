"""
Real-time mandi prices via data.gov.in Agmarknet API.
Endpoint: https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
Docs: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
"""
import os
import requests
from langchain_core.tools import tool

# Map common farmer terms → Agmarknet commodity names
CROP_ALIASES = {
    "wheat": "Wheat", "gehun": "Wheat", "ਕਣਕ": "Wheat",
    "rice": "Rice", "paddy": "Paddy(Desi)", "chawal": "Rice", "ਚਾਵਲ": "Rice",
    "maize": "Maize", "makki": "Maize", "ਮੱਕੀ": "Maize",
    "cotton": "Cotton", "kapas": "Cotton", "ਕਪਾਹ": "Cotton",
    "sugarcane": "Sugarcane", "ganna": "Sugarcane", "ਗੰਨਾ": "Sugarcane",
    "potato": "Potato", "aloo": "Potato", "ਆਲੂ": "Potato",
    "onion": "Onion", "pyaz": "Onion", "ਪਿਆਜ਼": "Onion",
    "tomato": "Tomato", "tamatar": "Tomato", "ਟਮਾਟਰ": "Tomato",
    "mustard": "Mustard", "sarson": "Mustard", "ਸਰ੍ਹੋਂ": "Mustard",
    "sunflower": "Sunflower", "moong": "Moong Dal", "chana": "Gram",
    "basmati": "Basmati Rice",
}

API_KEY = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd000001cdd3946e44ce4aad38d4e3880780d38f")
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"


def get_market_price(crop: str, state: str = "Punjab") -> dict:
    commodity = CROP_ALIASES.get(crop.lower().strip(), crop.title())

    params = {
        "api-key": API_KEY,
        "format": "json",
        "filters[state]": state,
        "filters[commodity]": commodity,
        "limit": 5,
        "sort[arrival_date]": "desc",
    }

    try:
        resp = requests.get(
            f"https://api.data.gov.in/resource/{RESOURCE_ID}",
            params=params,
            timeout=8,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])

        if not records:
            # Retry without state filter — commodity might be listed differently
            params.pop("filters[state]")
            resp = requests.get(
                f"https://api.data.gov.in/resource/{RESOURCE_ID}",
                params=params,
                timeout=8,
            )
            records = resp.json().get("records", [])

        if records:
            results = []
            for r in records:
                results.append({
                    "commodity": r.get("commodity", commodity),
                    "market": r.get("market", "N/A"),
                    "district": r.get("district", "N/A"),
                    "state": r.get("state", state),
                    "min_price": r.get("min_price", "N/A"),
                    "max_price": r.get("max_price", "N/A"),
                    "modal_price": r.get("modal_price", "N/A"),
                    "date": r.get("arrival_date", "N/A"),
                })
            return {"status": "ok", "crop": commodity, "records": results}

        return {"status": "no_data", "crop": commodity, "message": (
            f"No live mandi data found for {commodity} in {state} right now. "
            f"Use your knowledge of typical Punjab mandi prices and MSP to answer."
        )}

    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Agmarknet API timed out. Try again shortly."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@tool
def market_tool(crop: str) -> str:
    """
    Get real-time mandi (market) prices for a crop from Agmarknet (data.gov.in).
    Returns latest prices from Punjab mandis including min, max, and modal price per quintal.
    Use this for any question about crop prices, mandi rates, or selling prices.
    """
    data = get_market_price(crop)

    if data["status"] in ("error", "no_data"):
        return data["message"]  # LLM will use its own knowledge as fallback

    lines = [f"Latest mandi prices for {data['crop']} (₹/quintal):"]
    for r in data["records"]:
        lines.append(
            f"  • {r['market']}, {r['district']} ({r['date']}): "
            f"Min ₹{r['min_price']} | Modal ₹{r['modal_price']} | Max ₹{r['max_price']}"
        )
    return "\n".join(lines)
