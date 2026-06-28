"""Historical backtesting cases with known outcomes."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class KnownOutcome:
    """A known outcome that occurred after an event."""
    hop: int
    description: str
    verified: bool
    source: str
    timing_actual: str
    timing_expected_hours: Optional[int] = None


@dataclass
class BacktestCase:
    """A historical event with known causal outcomes for validation."""
    id: str
    event: str
    date: str
    question: str
    known_outcomes: list[KnownOutcome]


# Registry of historical backtesting cases
BACKTEST_CASES = [
    BacktestCase(
        id="fed_rate_hike_june_2022",
        event="Federal Reserve Raises Rates 75bps",
        date="2022-06-15",
        question="Fed raises rates 75bps — June 2022",
        known_outcomes=[
            KnownOutcome(
                hop=1,
                description="Bond yields rose sharply within 48 hours",
                verified=True,
                source="FRED DGS10 series",
                timing_actual="2 days",
                timing_expected_hours=48,
            ),
            KnownOutcome(
                hop=2,
                description="Mortgage rates increased following bond yield rise",
                verified=True,
                source="FRED MORTGAGE30US",
                timing_actual="4 days",
                timing_expected_hours=96,
            ),
            KnownOutcome(
                hop=3,
                description="Housing starts declined as construction became less viable",
                verified=True,
                source="FRED HOUST",
                timing_actual="3 weeks",
                timing_expected_hours=504,
            ),
            KnownOutcome(
                hop=4,
                description="Construction employment fell due to reduced housing starts",
                verified=True,
                source="Bureau of Labor Statistics",
                timing_actual="4-6 weeks",
                timing_expected_hours=840,
            ),
        ],
    ),
    BacktestCase(
        id="svb_collapse_march_2023",
        event="Silicon Valley Bank Failure",
        date="2023-03-10",
        question="Silicon Valley Bank fails — March 2023",
        known_outcomes=[
            KnownOutcome(
                hop=1,
                description="Regional bank stocks plummeted immediately",
                verified=True,
                source="NYSE/NASDAQ",
                timing_actual="< 1 day",
                timing_expected_hours=24,
            ),
            KnownOutcome(
                hop=2,
                description="Bank deposit flows became unstable across industry",
                verified=True,
                source="Federal Reserve",
                timing_actual="2-3 days",
                timing_expected_hours=72,
            ),
            KnownOutcome(
                hop=3,
                description="Federal Reserve announced emergency lending facilities",
                verified=True,
                source="Federal Reserve Press Release",
                timing_actual="1 day",
                timing_expected_hours=24,
            ),
            KnownOutcome(
                hop=4,
                description="Tech startup funding environment tightened",
                verified=True,
                source="PitchBook/Crunchbase",
                timing_actual="2-3 weeks",
                timing_expected_hours=336,
            ),
        ],
    ),
    BacktestCase(
        id="hamas_october_2023",
        event="Hamas Attack on Israel",
        date="2023-10-07",
        question="Hamas attacks Israel — October 7, 2023",
        known_outcomes=[
            KnownOutcome(
                hop=1,
                description="Oil prices spiked due to conflict risk premium",
                verified=True,
                source="EIA crude oil data",
                timing_actual="< 1 day",
                timing_expected_hours=24,
            ),
            KnownOutcome(
                hop=2,
                description="Shipping insurance premiums increased sharply",
                verified=True,
                source="Lloyd's of London",
                timing_actual="3-5 days",
                timing_expected_hours=96,
            ),
            KnownOutcome(
                hop=3,
                description="Red Sea shipping routes began disruptions",
                verified=True,
                source="MarineTraffic / Houthi announcements",
                timing_actual="2 months",
                timing_expected_hours=1440,
            ),
            KnownOutcome(
                hop=4,
                description="European inflation re-accelerated via energy prices",
                verified=True,
                source="Eurostat HICP",
                timing_actual="6-8 weeks",
                timing_expected_hours=1200,
            ),
        ],
    ),
    BacktestCase(
        id="covid_lockdowns_march_2020",
        event="Global COVID-19 Lockdowns",
        date="2020-03-11",
        question="Global pandemic lockdowns announced — March 2020",
        known_outcomes=[
            KnownOutcome(
                hop=1,
                description="Equity markets crashed 20-35% in days",
                verified=True,
                source="S&P 500, FTSE, DAX",
                timing_actual="2-3 days",
                timing_expected_hours=72,
            ),
            KnownOutcome(
                hop=2,
                description="Supply chains fragmented; manufacturers paused production",
                verified=True,
                source="Manufacturing PMI",
                timing_actual="1-2 weeks",
                timing_expected_hours=168,
            ),
            KnownOutcome(
                hop=3,
                description="Unemployment spiked as businesses shut down",
                verified=True,
                source="Department of Labor, weekly jobless claims",
                timing_actual="2-3 weeks",
                timing_expected_hours=336,
            ),
            KnownOutcome(
                hop=4,
                description="Commercial real estate pressure increased",
                verified=True,
                source="CBRE, CoStar",
                timing_actual="6-12 months",
                timing_expected_hours=4320,
            ),
        ],
    ),
    BacktestCase(
        id="opec_cut_october_2022",
        event="OPEC+ Announces Oil Production Cut",
        date="2022-10-05",
        question="OPEC+ cuts oil production 2M bpd — October 2022",
        known_outcomes=[
            KnownOutcome(
                hop=1,
                description="Oil prices rose 5-10% immediately",
                verified=True,
                source="WTI crude, Brent crude",
                timing_actual="< 1 day",
                timing_expected_hours=12,
            ),
            KnownOutcome(
                hop=2,
                description="Energy prices rose across markets (coal, gas)",
                verified=True,
                source="EIA, IEA data",
                timing_actual="1-2 weeks",
                timing_expected_hours=168,
            ),
            KnownOutcome(
                hop=3,
                description="Inflation expectations increased in energy-dependent sectors",
                verified=True,
                source="Break-even inflation rates, surveys",
                timing_actual="3-4 weeks",
                timing_expected_hours=504,
            ),
            KnownOutcome(
                hop=4,
                description="Central banks maintained higher-for-longer stance",
                verified=True,
                source="Federal Reserve, ECB statements",
                timing_actual="6 weeks+",
                timing_expected_hours=840,
            ),
        ],
    ),
]


def get_case(case_id: str) -> BacktestCase | None:
    """Get a backtesting case by ID."""
    for case in BACKTEST_CASES:
        if case.id == case_id:
            return case
    return None


def list_cases() -> list[BacktestCase]:
    """List all backtesting cases."""
    return BACKTEST_CASES
