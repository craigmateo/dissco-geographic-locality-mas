"""Shared test fixtures: the benchmark and mocked gazetteer HTTP.

No test calls a real API: see gazetteer_mocks.py.
"""

from datetime import date
from pathlib import Path

import pytest
from gazetteer_mocks import FakeGazetteers, read_json, ssr_entry  # noqa: F401

from geographic_locality_mas import indigenous_names as ina

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 14)
TEST_KEY = "test-key-0123456789abcdef"   # never a real key
BENCHMARK = read_json(ROOT / "data" / "benchmark-indigenous.json")


def short_id(record):
    return record["specimen_id"].rsplit("/", 1)[-1]


def as_location(record):
    """The location fields of a benchmark record (what the module reads)."""
    keys = ["specimen_id", "event_index", "country", "county", "locality",
            "latitude", "longitude", "coordinate_uncertainty_m"]
    return {k: record.get(k) for k in keys}


@pytest.fixture
def gazetteers(monkeypatch):
    """Mocked SSR + NLS. Also sets a fake MML_API_KEY and turns off throttling."""
    fake = FakeGazetteers()
    monkeypatch.setattr(ina, "SESSION", fake)
    monkeypatch.setattr(ina, "throttle", lambda host, rate: None)
    monkeypatch.setenv("MML_API_KEY", TEST_KEY)
    return fake
