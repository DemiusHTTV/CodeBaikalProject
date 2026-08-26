import datetime as dt
from decimal import Decimal

import pytest

from src.pipeline import _clean_value


@pytest.mark.parametrize(
    "raw, expected",
    [
        # AVG() отдаёт numeric с длинным хвостом — именно на это жаловались эксперты.
        (Decimal("3.5000000000000000"), 3.5),
        (Decimal("4.00"), 4.0),
        (Decimal("79.9"), 79.9),
        (Decimal("66.6666666666666667"), 66.67),
        # Округление половины вверх, а не «к чётному», как по умолчанию в Python.
        (Decimal("2.005"), 2.01),
    ],
)
def test_decimal_is_rounded_to_two_places(raw, expected):
    assert _clean_value(raw) == expected


def test_large_decimal_does_not_crash():
    assert _clean_value(Decimal("1E+40")) == pytest.approx(1e40)


def test_time_and_date_become_strings():
    assert _clean_value(dt.time(13, 40)) == "13:40:00"
    assert _clean_value(dt.date(2026, 8, 26)) == "2026-08-26"


@pytest.mark.parametrize("raw", [5, "Базы данных", True, None])
def test_other_types_pass_through_untouched(raw):
    assert _clean_value(raw) is raw
