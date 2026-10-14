from  urllib import parse
from  urllib import request
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import requests
import json
import sys

ENDPOINT_SEARCH = "https://www.wikidata.org/w/api.php";
ENDPOINT_SPARQL="https://query.wikidata.org/sparql"
TOKEN="UOUT_TOKEN"

#NOT_FUNCTIONAL_HARD_TO_PARSE OAUTH_TOKEN + SLOW SPARQL SEARCH + TOO MANY RESULTS API
def check_coord_wikidata(p_loc, max_location=5, lang="en"):
    global ENDPOINT_SEARCH
    global ENDPOINT_SPARQL
    global TOKEN
    lower_term=p_loc.lower()
    
    params = {
    "action": "wbsearchentities",
    "search": p_loc,
    "language": lang,
    "uselang": lang,
    "type": "item",
    "limit": max_location,
    "format": "json",
    }
    data = parse.urlencode(params).encode()
    req =  request.Request(ENDPOINT_SEARCH, data=data)
    req.add_header("Accept", "application/sparql-results+json")
    req.add_header("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36")
    req.add_header("Authorization", "Bearer "+TOKEN)
    try:
        with urlopen(req, timeout=30) as response:
            payload = json.load(response)
            print(payload)
            if "search" in payload:
                items=payload["search"]
                print(items)
                for item in items:
                    print(item)
                    print(json.dumps(item, indent=2, ensure_ascii=False))
                    if "label" in item:
                        
                        label_arr=item["label"].split(" ")
                        label_arr=[x.lower() for x in label_arr]
                        print(label_arr)
                        if lower_term in label_arr:
                            print("FOUND")
                            pid=item["id"]
                            
                            data = parse.urlencode(params).encode()
                            query_sparql='SELECT ?label ?description ?coordinates ?type ?typeLabel ?country ?country_iso WHERE { VALUES ?item { wd:'+pid+' } OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) IN ( "en")) } OPTIONAL { ?item schema:description ?description FILTER(LANG(?description) IN ("en")) } OPTIONAL { ?item wdt:P625 ?coordinates } OPTIONAL {?item wdt:P31 ?type . ?type rdfs:label ?typeLabel . FILTER(LANG(?typeLabel) = "en")}  OPTIONAL {        ?item wdt:P17 ?country .        OPTIONAL {            ?country rdfs:label ?countryLabel .            FILTER(LANG(?countryLabel) = "en")        }        OPTIONAL {            ?country wdt:P297 ?country_iso .        }    }}'
                            data2 = parse.urlencode({"query":query_sparql}).encode()
                            req2=  request.Request(ENDPOINT_SPARQL, data=data2)
                            req2.add_header("Accept", "application/sparql-results+json")
                            req2.add_header("user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36")
                            req2.add_header("Authorization", "Bearer "+TOKEN)
                            with urlopen(req2, timeout=30) as response2:
                                print(response2.getcode())
                                print(response2)
                                payload2 = json.load(response2)
                                print(payload2)
                                print(json.dumps(payload2, indent=2, ensure_ascii=False))
                                if "results" in payload2:
                                    res=payload2["results"]
                                    print(json.dumps(res, indent=2, ensure_ascii=False))
                                    if "bindings" in res:
                                        for bind in res["bindings"]:
                                            print(bind)
                            
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"API request failed: {exc}", file=sys.stderr)
        #sys.exit(1)