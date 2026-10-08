from __future__ import annotations

import numpy as np


def luhn_check_digit(body: str) -> str:
    total = 0
    reverse = body[::-1]
    for i, ch in enumerate(reverse):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return str((10 - (total % 10)) % 10)


def is_luhn(number: str) -> bool:
    if not number.isdigit() or len(number) < 2:
        return False
    return luhn_check_digit(number[:-1]) == number[-1]


def random_npi(rng: np.random.Generator) -> str:
    body = "".join(str(int(rng.integers(0, 10))) for _ in range(9))
    return body + luhn_check_digit(body)
