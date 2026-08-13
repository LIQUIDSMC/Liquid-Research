"""
Program B — Market Microstructure Research
Indicator: Near-Book Depth Imbalance
programs/program_b/indicators/near_book_depth.py

PURPOSE:
Pure calculation logic only. No I/O, no CLOB fetching, no printing.
Tests whether volume concentrated near the current market price
(top N book levels) carries different information than total book
volume (which is what OBI in indicators/obi.py measures).

FORMULA:
Near-OBI = (V_bid_top_n - V_ask_top_n) / (V_bid_top_n + V_ask_top_n)

Same structure as total-book OBI, but only sums the top N price
levels closest to the midpoint on each side, not the entire book.

HYPOTHESIS BEING TESTED:
A large resting order far from the current price may reflect a
passive limit order, not active near-term sentiment. Near-book
depth may be a cleaner signal of immediate pressure than total
book volume. If Near-OBI and total OBI are nearly always equal,
near-book depth adds no new information. If they diverge
meaningfully, that is a real, informative finding worth further
investigation.

ASSUMPTIONS AND LIMITATIONS:
- N=5 is a starting parameter, not a validated optimal value.
- "Top N levels" means N levels closest to the best bid/ask price,
  not N levels by any other ordering.
- No predictive claim is made by this module. Calculation only.
"""


def compute_near_book_obi(bids: list, asks: list, n: int = 5) -> dict:
    """
    Compute Near-Book Depth Imbalance using only the top N price
    levels closest to the midpoint on each side.

    Receives:
        bids (list[dict]): each {"price": str, "size": str}
        asks (list[dict]): each {"price": str, "size": str}
        n (int): number of price levels to include per side (default 5)

    Returns:
        dict with near_obi, v_bid_top_n, v_ask_top_n, and error (if any).
    """
    try:
        # Re-sort so index 0 is always the BEST price on each side, then
        # slice [:n] to get the n levels closest to the midpoint.
        # Best bid = highest price a buyer will pay -> sort descending.
        bid_prices = sorted(
            [(float(b["price"]), float(b["size"])) for b in bids if "price" in b and "size" in b],
            key=lambda x: x[0],
            reverse=True,
        )
        # Best ask = lowest price a seller will accept -> sort ascending.
        ask_prices = sorted(
            [(float(a["price"]), float(a["size"])) for a in asks if "price" in a and "size" in a],
            key=lambda x: x[0],
        )
    except (ValueError, TypeError) as e:
        return {"near_obi": None, "v_bid_top_n": None, "v_ask_top_n": None, "error": str(e)}

    top_bids = bid_prices[:n]
    top_asks = ask_prices[:n]

    v_bid_top_n = sum(size for _, size in top_bids)
    v_ask_top_n = sum(size for _, size in top_asks)

    total = v_bid_top_n + v_ask_top_n
    if total == 0:
        return {"near_obi": None, "v_bid_top_n": v_bid_top_n, "v_ask_top_n": v_ask_top_n, "error": "Zero total volume in top N levels"}

    near_obi = round((v_bid_top_n - v_ask_top_n) / total, 4)

    return {
        "near_obi": near_obi,
        "v_bid_top_n": round(v_bid_top_n, 2),
        "v_ask_top_n": round(v_ask_top_n, 2),
        "error": None,
    }
