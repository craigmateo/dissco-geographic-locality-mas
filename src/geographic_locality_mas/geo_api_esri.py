import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import requests
import json

def check_coord_esri(p_loc, max_location=5):
    url_esri="https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&outSR=%7B%22wkid%22%3A102100%7D&outFields=*&maxLocations="+str(max_location)+"&SingleLine="
    place=urllib.parse.quote(p_loc)
    #print(place)
    full_url=url_esri+place
    returned={"source_type": "ESRI", "source_url":"https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?", "max_len":max_location }
    returned_datas=[]
    i=0
    try:
        with urlopen(full_url, timeout=30) as response:
            payload = json.load(response)
            #print(payload)
            if "candidates" in payload:
                for cand in payload["candidates"]:
                    #print(i)
                    #print("----")
                    #print(cand)
                    if "attributes" in cand:
                        data=cand["attributes"]
                        #print("::::")
                        #print(data)
                        if len(data)>0:
                            reply={}
                            reply["addr_type"]=str(data["Addr_type"]);
                            reply["type"]=str(data["Type"]);
                            reply["long_label"]=str(data["LongLabel"]);
                            reply["country_name"]=str(data["CntryName"]);
                            reply["country_code"]=str(data["Country"]);
                            reply["longitude"]=str(data["X"]);
                            reply["latitude"]=str(data["Y"]);
                            returned_datas.append(reply)
                        #print(reply)
                    i=i+1
                    
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"API request failed: {exc}", file=sys.stderr)
        sys.exit(1)
    returned["response"]=returned_datas
    return returned