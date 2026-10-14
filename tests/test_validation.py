from geographic_locality_mas.validation import validate_coordinates


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
