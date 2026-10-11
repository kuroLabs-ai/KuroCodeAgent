"""
community_hub/tools/currency_converter.py
Foreign exchange conversion utility.
"""

def currency_converter(amount: float, from_curr: str = "USD", to_curr: str = "EUR") -> dict:
    """Convert currency using standard baseline rates."""
    rates_to_usd = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "JPY": 154.5,
        "EGP": 49.2,
        "CAD": 1.38,
    }
    f = from_curr.upper()
    t = to_curr.upper()
    if f not in rates_to_usd or t not in rates_to_usd:
        return {"success": False, "error": f"Unsupported currency pair {f}->{t}"}
    usd_val = amount / rates_to_usd[f]
    res = round(usd_val * rates_to_usd[t], 4)
    return {
        "success": True,
        "amount": amount,
        "from": f,
        "to": t,
        "result": res,
    }
