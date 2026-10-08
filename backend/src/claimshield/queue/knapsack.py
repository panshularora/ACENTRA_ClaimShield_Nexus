from __future__ import annotations


def expected_value(case: dict, *, horizon_days: int, recovery: float, harm_lambda: float) -> float:
    run_rate = case["flagged_dollars"] * (horizon_days / 90.0)
    dollars = case["flagged_dollars"] + run_rate
    return case["p_confirm"] * recovery * dollars + harm_lambda * case["harm"] * max(1, case["members_affected"])


def knapsack_select(cases: list[dict], *, capacity_hours: float) -> list[dict]:
    units = max(1, int(round(capacity_hours * 2)))  # half hours
    n = len(cases)
    weights = [max(1, int(round(c["estimated_hours"] * 2))) for c in cases]
    values = [c.get("ev", 0.0) for c in cases]
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
