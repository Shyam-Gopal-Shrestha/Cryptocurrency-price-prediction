from typing import Any, Dict, List


def build_portfolio_snapshot(
    rows,
    get_latest_price_and_change_fn,
    get_symbol_dataframe_fn,
    compute_risk_profile_fn,
) -> Dict[str, Any]:
    holdings: List[Dict[str, Any]] = []
    total_market_value = 0.0
    total_cost_basis = 0.0

    for row in rows:
        item = dict(row)
        symbol = item["symbol"]
        quantity = float(item["quantity"])
        avg_buy = float(item["avg_buy_price"])

        latest_price, _ = get_latest_price_and_change_fn(symbol)
        market_price = float(latest_price) if latest_price is not None else avg_buy

        cost_basis = quantity * avg_buy
        market_value = quantity * market_price
        unrealized_pl = market_value - cost_basis
        unrealized_pl_pct = (unrealized_pl / max(cost_basis, 1e-6)) * 100.0

        risk_score = None
        risk_level = None
        try:
            raw_df = get_symbol_dataframe_fn(symbol)
            risk_score, risk_level = compute_risk_profile_fn(raw_df)
        except Exception:
            pass

        total_market_value += market_value
        total_cost_basis += cost_basis
        holdings.append(
            {
                **item,
                "market_price": market_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_pct": unrealized_pl_pct,
                "risk_score": risk_score,
                "risk_level": risk_level,
            }
        )

    for holding in holdings:
        holding["allocation_pct"] = (
            (holding["market_value"] / max(total_market_value, 1e-6)) * 100.0 if total_market_value > 0 else 0.0
        )

    return {
        "holdings": holdings,
        "summary": {
            "total_market_value": total_market_value,
            "total_cost_basis": total_cost_basis,
            "total_unrealized_pl": total_market_value - total_cost_basis,
            "total_unrealized_pl_pct": (
                ((total_market_value - total_cost_basis) / max(total_cost_basis, 1e-6)) * 100.0
                if total_cost_basis > 0
                else 0.0
            ),
        },
    }
