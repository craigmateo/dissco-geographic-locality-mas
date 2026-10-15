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


def test_extracts_bare_opends_specimen():
    specimen = {
        "@id": "https://doi.org/SANDBOX/TEST-123",
        "ods:hasEvents": [
            {
                "ods:hasLocation": {
                    "dwc:country": "Greece",
                    "dwc:locality": "Milos",
                    "ods:hasGeoreference": {
                        "dwc:decimalLatitude": 36.74,
                        "dwc:decimalLongitude": 24.43,
                    },
                }
            }
        ],
    }

    result = extract_localities(specimen)

    assert len(result) == 1
    assert result[0]["specimen_id"] == "https://doi.org/SANDBOX/TEST-123"
    assert result[0]["event_index"] == 0
    assert result[0]["target"] == "$['ods:hasEvents'][0]['ods:hasLocation']"
    assert result[0]["country"] == "Greece"
    assert result[0]["locality"] == "Milos"
    assert result[0]["latitude"] == 36.74
    assert result[0]["longitude"] == 24.43
