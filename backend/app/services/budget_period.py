from calendar import monthrange
from datetime import date


def get_budget_period(today: date, salary_day: int = 1) -> tuple[date, date]:
    """급여일 기준 예산 기간 계산.

    salary_day=1: 일반 달력 기준 (1일~말일)
    salary_day=25: 전월 25일 ~ 당월 24일

    Returns:
        (period_start, period_end) tuple
    """
    if salary_day == 1:
        # Default: calendar month
        _, last_day = monthrange(today.year, today.month)
        return today.replace(day=1), today.replace(day=last_day)

    if today.day >= salary_day:
        # Current period: this month's salary_day ~ next month's salary_day - 1
        period_start = today.replace(day=salary_day)

        # Next month
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)

        _, next_last = monthrange(next_month.year, next_month.month)
        end_day = min(salary_day - 1, next_last)
        period_end = date(next_month.year, next_month.month, end_day)
    else:
        # Current period: previous month's salary_day ~ this month's salary_day - 1
        if today.month == 1:
            prev_month = date(today.year - 1, 12, 1)
        else:
            prev_month = date(today.year, today.month - 1, 1)

        _, prev_last = monthrange(prev_month.year, prev_month.month)
        start_day = min(salary_day, prev_last)
        period_start = date(prev_month.year, prev_month.month, start_day)

        _, this_last = monthrange(today.year, today.month)
        end_day = min(salary_day - 1, this_last)
        period_end = today.replace(day=end_day)

    return period_start, period_end
