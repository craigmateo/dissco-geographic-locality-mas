"""Fetch sample specimens from the DiSSCo Sandbox API."""

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uuid

from src.geographic_locality_mas.extraction import extract_localities
from src.geographic_locality_mas.geo_api_esri import check_coord_esri
from src.geographic_locality_mas.geo_api_wikidata import check_coord_wikidata
from src.geographic_locality_mas.parser_geo_text import parser_geo_text

API_URL = "https://sandbox.dissco.tech/api/digital-specimen/v1/search"
GAZETTERS=["ESRI"]#["ESRI",  'WIKIDATA']


def browse_spec(p_data, gazetters):
    #print(json.dumps(p_data, indent=4))
   
    returned=[]
    for spec in p_data:
        #elem=p_data.copy()
        returned_full=[]
        item_resp={}
        locality=extract_localities(spec)
        print(locality)
        if locality is not None:
            
            if len(locality)>0:
                for l in locality:
                    if "locality" in l:
                        specimen_id=l["specimen_id"]
                        georef_api_annotation=[]
                        place=l["locality"]
                        print(place)
                        loc_list=parser_geo_text(place)
                        print(loc_list)
                        for loc in loc_list:
                            if "ESRI" in gazetters:
                                returned_esri=check_coord_esri(loc)
                                vuuid=uuid.uuid4()                                
                                georef_api_annotation.append({"uuid":str(vuuid), "id":None, "gazetteer": "ESRI", "original_place": place, "searched_term": loc, "results": returned_esri})
                            if "WIKIDATA" in gazetters:
                                #NOT_FUNCTIONAL_HARD_TO_PARSE OAUTH_TOKEN + SLOW SPARQL SEARCH + TOO MANY RESULTS API
                                returned_wikidata=check_coord_wikidata(loc)
                        returned_full.append({"specimen_id":specimen_id, "georef_api_annotation":georef_api_annotation })
            
        spec2=spec.copy()    
        #spec2={}
        spec2["gazetter_check"]=returned_full
        returned.append(spec2)
    return returned
 

        
def main():
    global GAZETTERS
    params = urlencode({"pageSize": 5, "pageNumber": 1})
    url = f"{API_URL}?{params}"

    print(f"Fetching specimens from {url}", file=sys.stderr)

    try:
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"API request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    records = payload.get("data", [])
    records_georef=browse_spec(records, GAZETTERS)
    
    print(records_georef)
    #sys.exit()
    result = {
        "source": API_URL,
        "specimens_retrieved": len(records),
        "specimens_loc": records_georef
       
       
    }
    print(result)
    #sys.exit()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
