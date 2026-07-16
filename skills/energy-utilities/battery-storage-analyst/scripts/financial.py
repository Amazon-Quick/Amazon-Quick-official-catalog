"""Project-finance metrics for battery storage: NPV, IRR, payback, and LCOS.

numpy_financial is not available in the Amazon Quick sandbox, so these are
implemented directly with the standard library. Cash flows are a list in nominal
dollars indexed by year, with year 0 as the capital outlay (negative). See
references/financial-model.md for how the cash flow series is assembled.
"""

from __future__ import annotations


def npv(rate: float, cash_flows: list[float]) -> float:
    """Net present value of a cash flow series discounted at `rate` (e.g. WACC)."""
    return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cash_flows))


def irr(
    cash_flows: list[float],
    low: float = -0.9,
    high: float = 1.0,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> float | None:
    """Internal rate of return via bisection. Returns None if no sign change exists."""
    f_low = npv(low, cash_flows)
    f_high = npv(high, cash_flows)
    if f_low * f_high > 0:
        return None
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2.0


def payback_year(cash_flows: list[float]) -> int | None:
    """First year index where cumulative (undiscounted) cash flow turns non-negative."""
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0:
            return t
    return None


def lcos(
    capital: float,
    opex_by_year: list[float],
    discharged_by_year: list[float],
    rate: float,
) -> float | None:
    """Levelized cost of stored energy: discounted cost over discounted discharge.

    Units follow the inputs ($/kWh if discharge is in kWh). Returns None when no
    energy is discharged.
    """
    disc_cost = capital + sum(
        o / (1.0 + rate) ** (t + 1) for t, o in enumerate(opex_by_year)
    )
    disc_energy = sum(
        e / (1.0 + rate) ** (t + 1) for t, e in enumerate(discharged_by_year)
    )
    if disc_energy == 0:
        return None
    return disc_cost / disc_energy
