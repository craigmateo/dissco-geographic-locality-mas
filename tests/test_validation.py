from geographic_locality_mas.validation import (
    validate_coordinates,
    validate_coordinates_with_tolerance,
)
import pytest

def test_missing_coordinates():
    result = validate_coordinates({
        "specimen_id": "example-1",
        "country": "Greece",
        "latitude": None,
        "longitude": None,
    })
    assert result["status"] == "unable_to_validate"


def test_invalid_latitude():
    result = validate_coordinates({
        "specimen_id": "example-2",
        "country": "Greece",
        "latitude": 120.0,
        "longitude": 23.0,
    })
    assert result["status"] == "invalid_coordinates"


def test_coordinates_inside_greece():
    result = validate_coordinates({
        "specimen_id": "example-3",
        "country": "Greece",
        "latitude": 37.98,
        "longitude": 23.73,
    })
    assert result["status"] == "consistent"


def test_coordinates_outside_greece():
    result = validate_coordinates({
        "specimen_id": "example-4",
        "country": "Greece",
        "latitude": 52.52,
        "longitude": 13.40,
    })
    assert result["status"] == "inconsistent"


def test_unknown_country():
    result = validate_coordinates({
        "specimen_id": "example-5",
        "country": "Unknownland",
        "latitude": 37.98,
        "longitude": 23.73,
    })
    assert result["status"] == "unable_to_validate"

def test_near_boundary_with_tolerance():
    specimen = {
        "specimen_id": "new-zealand-example",
        "country": "New Zealand",
        "latitude": -43.74483,
        "longitude": 169.17587,
    }

    result = validate_coordinates_with_tolerance(specimen)

    assert result["status"] == "near_boundary"
    assert 1.5 < result["boundary_distance_km"] < 2.5
    assert result["tolerance_km"] == 5.0


def test_large_discrepancy_remains_inconsistent():
    specimen = {
        "specimen_id": "austria-example",
        "country": "Austria",
        "latitude": 47.11417,
        "longitude": -11.68139,
    }

    original = specimen.copy()
    result = validate_coordinates_with_tolerance(specimen)

    assert result["status"] == "inconsistent"
    assert result["boundary_distance_km"] > 1000
    assert specimen == original


def test_ghana_discrepancy():
    specimen = {
        "specimen_id": "ghana-example",
        "country": "Ghana",
        "latitude": 5.44992,
        "longitude": 1.41785,
    }

    result = validate_coordinates_with_tolerance(specimen)

    assert result["status"] == "inconsistent"
    assert 60 < result["boundary_distance_km"] < 65


def test_consistent_coordinates_have_zero_distance():
    specimen = {
        "specimen_id": "greece-example",
        "country": "Greece",
        "latitude": 37.98,
        "longitude": 23.73,
    }

    result = validate_coordinates_with_tolerance(specimen)

    assert result["status"] == "consistent"
    assert result["boundary_distance_km"] == 0.0


def test_negative_tolerance_is_rejected():
    specimen = {
        "country": "Greece",
        "latitude": 37.98,
        "longitude": 23.73,
    }

    with pytest.raises(ValueError):
        validate_coordinates_with_tolerance(specimen, tolerance_km=-1)