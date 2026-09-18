"""
LRS-2 — Market Microstructure Research
Indicator: Order Book Imbalance (OBI) and Micro-Price
L3_RESEARCH_ENGINES/market_microstructure/indicators/obi.py

PURPOSE:
Pure calculation logic only. No I/O, no CLOB fetching, no printing.
This module is imported by diagnostic and analysis scripts that
need OBI/micro-price values from raw order book data.

FORMULAS:
OBI  = (V_bid - V_ask) / (V_bid + V_ask)
       Range: -1 to +1. Positive = more bid pressure. Negative = more ask pressure.
       Uses total volume across all book levels (standard definition).

Micro-price = (best_bid * V_ask + best_ask * V_bid) / (V_bid + V_ask)
              Volume-weighted blend of best bid and ask.
              Accounts for order book pressure unlike simple midpoint.

ASSUMPTIONS AND LIMITATIONS:
- OBI uses total volume across ALL book levels, not just the inside market.
- Micro-price assumes best bid/ask sizes are meaningful — may not hold in thin books.
- No predictive claim is made by this module. Calculation only.
"""


def compute_obi_and_microprice(bids: list, asks: list, best_bid: float, best_ask: float) -> dict:
    """
    Compute Order Book Imbalance and Micro-Price from raw book levels.

    OBI = (V_bid - V_ask) / (V_bid + V_ask)
    Micro-price = (best_bid * V_ask + best_ask * V_bid) / (V_bid + V_ask)

    Receives:
        bids (list[dict]): each {"price": str, "size": str}
        asks (list[dict]): each {"price": str, "size": str}
        best_bid (float or None)
        best_ask (float or None)

    Returns:
        dict with obi, micro_price, v_bid, v_ask, and error (if any).
    """
    try:
        v_bid = sum(float(b["size"]) for b in bids if "size" in b)
        v_ask = sum(float(a["size"]) for a in asks if "size" in a)
    except (ValueError, TypeError) as e:
        return {"obi": None, "micro_price": None, "v_bid": None, "v_ask": None, "error": str(e)}

    total = v_bid + v_ask
    if total == 0:
        return {"obi": None, "micro_price": None, "v_bid": v_bid, "v_ask": v_ask, "error": "Zero total volume"}

    obi = round((v_bid - v_ask) / total, 4)

    if best_bid is None or best_ask is None:
        return {"obi": obi, "micro_price": None, "v_bid": v_bid, "v_ask": v_ask, "error": "Missing best bid/ask for micro-price"}

    micro_price = round((best_bid * v_ask + best_ask * v_bid) / total, 6)

    return {"obi": obi, "micro_price": micro_price, "v_bid": round(v_bid, 2), "v_ask": round(v_ask, 2), "error": None}
