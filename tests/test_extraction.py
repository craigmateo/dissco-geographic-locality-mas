from geographic_locality_mas.extraction import extract_localities


def test_extracts_locality():
    specimen = {
        "id": "test-specimen",
        "attributes": {
            "ods:hasEvents": [{
                "ods:hasLocation": {
                    "dwc:country": "Greece",
                    "dwc:locality": "Milos"
                }
            }]
        }
    }

    result = extract_localities(specimen)

    assert len(result) == 1
    assert result[0]["country"] == "Greece"
    assert result[0]["locality"] == "Milos"
    assert result[0]["latitude"] is None


def test_missing_events():
    assert extract_localities({"attributes": {}}) == []
