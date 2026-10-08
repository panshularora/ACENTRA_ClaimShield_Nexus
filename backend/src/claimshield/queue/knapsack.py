from __future__ import annotations


def expected_value(case: dict, *, horizon_days: int, recovery: float) -> float:
    """Expected recoverable dollars: P(confirm) x recovery rate x (flagged + run-rate to the horizon).

    Dollars only. Member harm ranks cases through the composite score and the priority-override
    lane; it is not converted into pseudo-dollars here.
    """
    run_rate = case["flagged_dollars"] * (horizon_days / 90.0)
    dollars = case["flagged_dollars"] + run_rate
    return float(case["p_confirm"] * recovery * dollars)


def knapsack_select(cases: list[dict], *, capacity_hours: float, value_key: str = "ev") -> list[dict]:
    if capacity_hours < 0.5 or not cases:
        return []
    units = int(round(capacity_hours * 2))  # half hours
    n = len(cases)
    weights = [max(1, int(round(c["estimated_hours"] * 2))) for c in cases]
    values = [float(c.get(value_key, c.get("composite", c.get("ev", 0.0))) or 0.0) for c in cases]
    dp = [[0.0] * (units + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w = weights[i - 1]
        v = values[i - 1]
        for u in range(units + 1):
            dp[i][u] = dp[i - 1][u]
            if w <= u:
                dp[i][u] = max(dp[i][u], dp[i - 1][u - w] + v)
    chosen: list[int] = []
    u = units
    for i in range(n, 0, -1):
        if dp[i][u] != dp[i - 1][u]:
            chosen.append(i - 1)
            u -= weights[i - 1]
    chosen.reverse()
    return [cases[i] for i in chosen]
