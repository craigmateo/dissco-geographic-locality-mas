"""Extract structured geographic context from DiSSCo specimen records."""
import re
import spacy
import langdetect
import requests
# from geoparser import Geoparser
# from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

def extract_coordinates(specimen):
    if specimen.get("latitude") and specimen.get("longitude"):
        return specimen
    if specimen.get("locality"):
        text = specimen.get("locality")
        latitude = None
        longitude = None
        # TODO: Add "O" for "Ost" or "Ouest" 
        # TODO: Add additional parsing methods to sum up certain cases
        # First case: Decimal degrees with no hemisphere or hemisphere at the end
        match = re.search(r'(-?\d{1,3}\.\d+)\s*[°]?\s*([NS]?)\s*[\s,;/]+\s*(-?\d{1,3}\.\d+)\s*[°]?\s*([EW]?)', text)
        if match:
            lat, lat_hem, lon, lon_hem = match.groups()
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        # Second case: Decimal degrees with no hemisphere or hemisphere at the beginning+
        elif re.search(r'([NS])\s*(-?\d{1,3}\.\d+)\s*[\s,;/]+\s*([EW])\s*(-?\d{1,3}\.\d+)', text):
            match = re.search(r'([NS])\s*(-?\d{1,3}\.\d+)\s*[\s,;/]+\s*([EW])\s*(-?\d{1,3}\.\d+)', text)
            lat_hem, lat, lon_hem, lon = match.groups()
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        # Third case: Degrees, minutes, seconds with hemisphere at the end
        elif re.search(r'(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*([NS])\s*[\s,;/]+\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*([EW])', text):
            match = re.search(r'(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*([NS])\s*[\s,;/]+\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*([EW])', text)
            lat_deg, lat_min, lat_sec, lat_hem, lon_deg, lon_min, lon_sec, lon_hem = match.groups()
            lat = float(lat_deg) + float(lat_min)/60 + float(lat_sec)/3600
            lon = float(lon_deg) + float(lon_min)/60 + float(lon_sec)/3600
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        # Fourth case: Degrees, minutes, seconds with hemisphere at the beginning
        elif re.search(r'([NS])\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*[\s,;/]+\s*([EW])\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?', text):
            match = re.search(r'([NS])\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?\s*[\s,;/]+\s*([EW])\s*(\d{1,3})[°]\s*(\d{1,2})[\'’]\s*(\d{1,2}(?:\.\d+)?)["”]?', text)
            lat_hem, lat_deg, lat_min, lat_sec, lon_hem, lon_deg, lon_min, lon_sec = match.groups()
            lat = float(lat_deg) + float(lat_min)/60 + float(lat_sec)/3600
            lon = float(lon_deg) + float(lon_min)/60 + float(lon_sec)/3600
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        # Fifth case: Degrees and decimal minutes with hemisphere at the end
        elif re.search(r'(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*([NS])\s*[\s,;/]+\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*([EW])', text):
            match = re.search(r'(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*([NS])\s*[\s,;/]+\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*([EW])', text)
            lat_deg, lat_min, lat_hem, lon_deg, lon_min, lon_hem = match.groups()
            lat = float(lat_deg) + float(lat_min)/60
            lon = float(lon_deg) + float(lon_min)/60
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        # Sixth case: Degrees and decimal minutes with hemisphere at the beginning
        elif re.search(r'([NS])\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*[\s,;/]+\s*([EW])\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?', text):
            match = re.search(r'([NS])\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?\s*[\s,;/]+\s*([EW])\s*(\d{1,3})[°]\s*(\d{1,2}\.\d+)[\'’]?', text)
            lat_hem, lat_deg, lat_min, lon_hem, lon_deg, lon_min = match.groups()
            lat = float(lat_deg) + float(lat_min)/60
            lon = float(lon_deg) + float(lon_min)/60
            latitude, longitude = parse_coordinates(lat, lat_hem, lon, lon_hem)
        specimen["latitude"] = latitude
        specimen["longitude"] = longitude 
    return specimen

def parse_coordinates(lat, lat_hem, lon, lon_hem): # TODO: Will become parse_decimal_coordinates and parse_dms_coordinates
    lat = float(lat)
    lon = float(lon)
    if lat_hem.upper() == 'S':
        lat = -lat
    if lon_hem.upper() == 'W':
        lon = -lon
    return lat, lon

def extract_distance(specimen):
    if specimen.get("locality"):
        text = specimen.get("locality")
        if re.search(r'\b(km|kilometer|kilometers|mi|mile|miles|m|meter|meters)\b', text, re.IGNORECASE):
            distance_in_text = True
        coordinates_in_text = True if specimen.get("latitude") and specimen.get("longitude") else False
        # Coordinates with N/S/E/W may be confused with distance
        if not coordinates_in_text and distance_in_text:
            units_and_values = re.search(r'(\d+(\.\d+)?)\s*(km|kilometer|kilometers|mi|mile|miles|m|meter|meters)', text, re.IGNORECASE)
            if units_and_values:
                distance_value, _, distance_unit = units_and_values.groups()
                specimen["distance"] = {
                    "value": float(distance_value),
                    "unit": distance_unit.lower()
                }
            direction_match_pattern = r'\b(north|south|east|west|northeast|northwest|southeast|southwest|' + \
                                     r'n|s|e|w|ne|nw|se|sw|north-east|north-west|south-east|south-west)\b' + \
                                    r'nördlich|südlich|östlich|westlich|nordöstlich|nordwestlich|südöstlich|südwestlich)\b'
            # TODO: Add further direction patterns or use the translation service depending on the language detected
    return specimen

def detect_language(text):
    try:        
        return langdetect.detect(text)
    except langdetect.lang_detect_exception.LangDetectException:
        return None
    
def request_wikibase_api(toponym):
    wikidata_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={toponym}&language=en&format=json&limit=5"
    mail = ""
    headers = {
        "User-Agent": f"hackathon-disambiguator/1.0 ({mail.split('@')[0]}; {mail})"
    }
    response = requests.get(wikidata_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def get_wikidata_object(wikidata_id):
    wikidata_url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
    mail = ""
    headers = {
        "User-Agent": f"hackathon-disambiguator/1.0 ({mail.split('@')[0]}; {mail})"
    }
    response = requests.get(wikidata_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def extract_toponyms(specimen):
    locality_text = specimen.get("locality")
    # TODO: check for language of locality_text determining the spacy model to use for named entity recognition
    # INFO: Disambiguation not required in this subtask
    # language = detect_language(locality_text)
    nlp = spacy.load("en_core_web_lg")  # TODO: Load the proper model based on detected language
    doc = nlp(locality_text)
    toponyms = [ent for ent in doc.ents if ent.label_ in ['LOC', 'GPE']]
    print(f"Extracted toponyms: {[ent.text for ent in toponyms]}")
    # toponyms = filter_toponyms(toponyms) # TODO: Implement filter_toponyms to remove false positives such as "bahnhof"
    wikidata_results = dict()
    # for toponym in toponyms:
    #     wikidata_result = request_wikibase_api(toponym.text)
    #     if wikidata_result:
    #         wikidata_results[toponym.text] = wikidata_result
    # TODO: Plausibility check for toponyms, e.g. if a country is given or coordinates
    # TODO: Add geonames or gazetteer lookup for toponyms by using wikidata provided alternative names
    # TODO: Check if URLs should be added to the result as wellwikidata_result
    return wikidata_results

# # test extract_coordinates with a sample specimen
# specimen = {
#     "id": "specimen1",
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, 22°7'18.7536\"N 91°0'53.144\"E"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, N22°7'18.7536\", E91°0'53.144\"E"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, N 22°7.3126' E 91°0.8857'"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, 51°29.52' N 91°14.14' E"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, 51.492 N 91.531 E I"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, N 51.492 E 91.531 Bangladesh"
#     # "locality": "Katakhali, Hatiya Jahajmara, mouth of river, -51.492, 91.531 Bangladesh"
#     "locality": "Small stream in young pine forest, 70 km N of Rovaniemi"
# }
# # print(extract_coordinates(specimen))
# print(extract_toponyms(specimen))
