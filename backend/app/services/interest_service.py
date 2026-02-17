from datetime import date
from decimal import Decimal


def calculate_deposit_interest(
    principal: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    maturity_date: date,
    interest_type: str,
    tax_rate: Decimal,
) -> dict:
    """
    예금 이자 계산 (단리/복리)

    Returns:
        elapsed_months, total_months,
        accrued_interest_pretax, accrued_interest_aftertax,
        maturity_amount, total_value_krw
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    p = float(principal)

    elapsed_days = max(0, (min(as_of_date, maturity_date) - start_date).days)
    total_days = max(1, (maturity_date - start_date).days)
    elapsed_months = max(0, round(elapsed_days / 30.44))
    total_months = max(1, round(total_days / 30.44))

    if interest_type == "compound":
        accrued_pretax = p * ((1 + rate / 12) ** elapsed_months - 1)
        maturity_pretax = p * ((1 + rate / 12) ** total_months - 1)
    else:
        accrued_pretax = p * rate * elapsed_days / 365
        maturity_pretax = p * rate * total_days / 365

    accrued_aftertax = accrued_pretax * (1 - tax)
    maturity_aftertax = maturity_pretax * (1 - tax)
    maturity_amount = p + maturity_aftertax
    total_value = p + accrued_aftertax

    return {
        "elapsed_months": elapsed_months,
        "total_months": total_months,
        "accrued_interest_pretax": round(accrued_pretax),
        "accrued_interest_aftertax": round(accrued_aftertax),
        "maturity_amount": round(maturity_amount),
        "total_value_krw": round(total_value),
    }


def calculate_savings_interest(
    monthly_amount: Decimal,
    annual_rate: Decimal,
    start_date: date,
    as_of_date: date,
    maturity_date: date,
    tax_rate: Decimal,
) -> dict:
    """
    적금 이자 계산 (정액적립식 단리)

    Returns:
        paid_count, total_months, total_paid,
        accrued_interest_pretax, accrued_interest_aftertax,
        maturity_amount, total_value_krw
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    m = float(monthly_amount)

    elapsed_days = max(0, (min(as_of_date, maturity_date) - start_date).days)
    total_days = max(1, (maturity_date - start_date).days)
    total_months = max(1, round(total_days / 30.44))
    paid_count = max(0, min(round(elapsed_days / 30.44), total_months))

    total_paid = m * paid_count

    # 정액적립식 단리: m × (rate/12) × n(n+1)/2
    accrued_pretax = m * (rate / 12) * paid_count * (paid_count + 1) / 2
    maturity_pretax = m * (rate / 12) * total_months * (total_months + 1) / 2

    accrued_aftertax = accrued_pretax * (1 - tax)
    maturity_aftertax = maturity_pretax * (1 - tax)
    maturity_amount = m * total_months + maturity_aftertax
    total_value = total_paid + accrued_aftertax

    return {
        "paid_count": paid_count,
        "total_months": total_months,
        "total_paid": round(total_paid),
        "accrued_interest_pretax": round(accrued_pretax),
        "accrued_interest_aftertax": round(accrued_aftertax),
        "maturity_amount": round(maturity_amount),
        "total_value_krw": round(total_value),
    }


def calculate_parking_interest(
    principal: Decimal,
    annual_rate: Decimal,
    tax_rate: Decimal,
) -> dict:
    """
    CMA/파킹통장 일일이자 계산

    Returns:
        daily_interest, monthly_interest, total_value_krw
    """
    rate = float(annual_rate) / 100
    tax = float(tax_rate) / 100
    p = float(principal)

    daily_interest = round(p * rate / 365)
    monthly_interest = round(daily_interest * 30 * (1 - tax))

    return {
        "daily_interest": daily_interest,
        "monthly_interest": monthly_interest,
        "total_value_krw": round(p),
    }
