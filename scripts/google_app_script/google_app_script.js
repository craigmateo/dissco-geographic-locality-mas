var url_nominatim="https://nominatim.openstreetmap.org/search.php?format=json&limit=100";
var url_geonames="http://api.geonames.org/searchJSON?username=ftheeten";
var url_darwin_rmca="https://darwinweb.africamuseum.be/dw_georef/ws.php?";
var url_darwin_rbins="https://darwin.naturalsciences.be/dw_georef/ws.php?";
var url_photon="https://photon.komoot.io/api/?";
var url_esri="https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&outSR=%7B%22wkid%22%3A102100%7D&outFields=*&SingleLine=";
var url_srtm="https://ows.mundialis.de/services/service?service=WMS&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&FORMAT=image%2Fjpeg&TRANSPARENT=true&QUERY_LAYERS=TOPO-WMS&STYLES&LAYERS=TOPO-WMS&exceptions=application%2Fvnd.ogc.se_inimage&INFO_FORMAT=application%2Fjson&FEATURE_COUNT=50&X=0&Y=0&SRS=EPSG%3A4326&WIDTH=10&HEIGHT=10&BBOX="
var url_srtm_rdc="https://edit.africamuseum.be/geoserver/canathist_gis/wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=canathist_gis%3Acongo_rdc_srtm_merged&FORMAT=application%2Fprs.coverage%2Bjson";
var sheet_darwin_rmca="darwin_rmca";
var sheet_darwin_rbins="darwin_rbins";
var sheet_geonames="geonames";
var sheet_nominatim="nominatim";
var sheet_photon_name="photon";
var sheet_source="source";
var sheet_menu_name="menu";
var sheet_esri_name="esri";
var sheet_srtm_name="srtm_mundialis";
var sheet_srtm_drc_name="srtm_drc_rmca";
var spreadsheet_id= SpreadsheetApp.getActiveSpreadsheet().getId()/*"1yiQWAO7Mta43X6oyZBUAaQaUpp9CS5zOxdmTLkTICCU";*/
var url_viewer="https://darwin.naturalsciences.be/can_service/index.html?";
 var cols_results={
  "all": 6,
  "dw_rmca": 7,
  "dw_rbins": 8,
  "esri": 9,
  "photon" : 10,
  "osm": 11,
  "geonames": 12
 }

  var results_colors={
  "dw_rmca": "#3399CC",
  "dw_rbins": "#339900",
  "esri":  "#7766CC",
  "photon" :  "#3300CC",
   "osm": "#DD55CC",
  "geonames": "#FF0099"
 }



function nb_to_excel_letter(param)
{
    
    var asc=String.fromCharCode(param+64);
    return asc;
}

function build_url_viewer()
{
  Logger.log("build_url");
  var target=-1;
  var tmp_dict=Array();
  for (const [key, value] of Object.entries(cols_results)) 
    {
      if(key=="all")
      {
        target=value;
       
      }
      else
      {
        tmp_dict.push(value)
      }
    }
    Logger.log(tmp_dict);
      var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
      var src_sheet = sheetActive.getSheetByName("source");
      var lastRow = src_sheet.getLastRow();
      if(lastRow>=2)
       {
          for(var i=2; i<=lastRow; i++ )
          {
            //Logger.log(i)
            var params=Array();
            var cell_ref=src_sheet.getRange(i, 2);
            var ref_value=cell_ref.getValue();
            //Logger.log("val=");
            //Logger.log(ref_value);
            if(ref_value.length>0)
            {
              for(var j=0; j<tmp_dict.length; j++)
              {
                Logger.log("====>");
                Logger.log("row=");
                Logger.log(i);
                Logger.log("src=");
                Logger.log(tmp_dict[j]);
                  Logger.log( src_sheet[j]);
                var cell = src_sheet.getRange(i, tmp_dict[j]);
                Logger.log("param=");
                console.log(cell.getValue());
                if(cell.getValue().length>0)
                {
                  params.push(cell.getValue());
                  //Logger.log("push");
                }
              }
              //Logger.log("param_final");
              //Logger.log(params);
              var cell_target = src_sheet.getRange(i, target);
              var param_str=params.join("&");
              var full_url=url_viewer+param_str+"&sheet_id="+spreadsheet_id;
              //cell_target.setValue(full_url);
              cell_target.setFormula('=HYPERLINK("'+full_url+'", "link_to_viewer")')
            }
              
          }
       }
}

function flush_all_result_links()
{
   var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
  var sheet = sheetActive.getSheetByName("source");
  var lastRow = sheet.getLastRow();
  if(lastRow>=2)
  {
    for (const [key, value] of Object.entries(cols_results)) 
    {
       var letterCol=nb_to_excel_letter(value);
       
       var range=sheet.getRange(letterCol+"2:"+letterCol+lastRow.toString());
       Logger.log(range);
       range.clear();
       sheet.autoResizeColumn(value);
    }
  }
}

 function flush_write_coord_form_map(src, src_sheet, i, p_acc)
{
  //Logger.log("p_acc=")
  //Logger.log(p_acc)
  var target_col=cols_results[src];
  var target_color=results_colors[src];
  if(i==2)
  {
    
    var lastRow = src_sheet.getLastRow();
    if(lastRow>=2)
    {
      var letterCol=nb_to_excel_letter(target_col);
      var range=src_sheet.getRange(letterCol+"2:"+letterCol+lastRow.toString());
      range.clear(); //.clearFormat();
    }
  }
  Logger.log(p_acc);
  p_acc=p_acc.map((w)=> w.replace(";","_"));
  p_acc=p_acc.map((w)=> w.replace("+","_"));
   p_acc=p_acc.map((w)=> w.replace("&"," et "));
  var coords_str=p_acc.join(";")
  
  
  target_color=target_color.replace("#", "%23")
  console.log(i)
  var cell = src_sheet.getRange(i, target_col);
  cell.setValue(src+"="+target_color+"+"+encodeURI(coords_str))

}

function delete_sheet_photon()
{
  delete_sheet(sheet_photon_name)
}

function delete_sheet_nominatim()
{
  delete_sheet("nominatim")
}

function delete_sheet_geonames()
{
  delete_sheet("geonames")
}

function delete_sheet_darwin_rmca()
{
  delete_sheet("darwin_rmca")
}

function delete_sheet_darwin_rbins()
{
  delete_sheet("darwin_rbins")
}

function delete_sheet_esri()
{
  delete_sheet(sheet_esri_name)
}

function delete_sheet_srtm()
{
  delete_sheet(sheet_srtm_name)
}

function delete_sheet_srtm_drc()
{
  delete_sheet(sheet_srtm_drc_name)
}

function delete_source()
{
  delete_sheet("source")
}

function delete_sheet(sheet_name)
{

   var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
   
    var sheet = sheetActive.getSheetByName(sheet_name);
   
     var lastRow = sheet.getLastRow();
      
     Logger.log(lastRow)
     if(lastRow>2)
     {
      
        var range=sheet.getRange("2:"+lastRow.toString())
        range.clear(); //.clearFormat();
        //range.clearContent();
        //sheet.deleteRows(2, lastRow);
     }
     SpreadsheetApp.getActiveSpreadsheet().toast("deletion done");
}

function return_from_json(json, field)
{
  if(field in json)
  {
    return json[field];    
  }
  else
  {
    return "";
  }
}

function activate_sheet_nominatim() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_nominatim);
  sheetgeo.activate()
}
function activate_sheet_geonames() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_geonames);
  sheetgeo.activate()
}   

function activate_darwin_rmca() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_darwin_rmca);
  sheetgeo.activate()
}   

function activate_sheet_source() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_source);
  sheetgeo.activate()
} 
function activate_photon_name() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_photon_name);
  sheetgeo.activate()
} 

function activate_darwin_rbins() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_darwin_rbins);
  sheetgeo.activate()
}

function activate_esri() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_esri_name);
  sheetgeo.activate()
}


function activate_srtm() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_srtm_name);
  sheetgeo.activate()
}

function activate_srtm_drc() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_srtm_drc_name);
  sheetgeo.activate()
}


function activate_menu() 
 {
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_menu_name);
  sheetgeo.activate()
}

function go_darwin_rmca()
{
   go_darwin(url_darwin_rmca, sheet_darwin_rmca, "dw_rmca")
      var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_darwin_rmca);
  sheetgeo.activate()
}

function go_darwin_rbins()
{
   go_darwin(url_darwin_rbins, sheet_darwin_rbins, "dw_rbins")
      var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_darwin_rbins);
  sheetgeo.activate()
}

function go_esri()
{
    var returned=Array(); 
    var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
    var sheet = sheetActive.getSheetByName("source");
    var sheet_esri = sheetActive.getSheetByName(sheet_esri_name);
    var data = sheet.getDataRange().getValues();
    var i=0;
    
    var old_i=-1;
    var acc_coord=Array();
    var src="esri";
    var i2=1
    data.forEach(function (row) {
     
      if(i>0)
      {
          if(i!=old_i && i>1)
          {
              
              flush_write_coord_form_map(src, sheet, i, acc_coord)
              old_i=i;
               i2=1;
               //Logger.log("i2 reset");
              acc_coord=[];
          }
          id=row[0]
          place=row[1];
          country=row[2];
          if(place.length>0)
            { 
                place=place.replace(/\.(?!\s)/g, ". ");
                var tmp_url=url_esri+encodeURIComponent(place);
                 Logger.log(tmp_url)
                 var response = UrlFetchApp.fetch(tmp_url);
                 var code = response.getResponseCode();
                 //Logger.log(code);
                 var text = response.getContentText();
                 //Logger.log(text);
                var data_tmp=JSON.parse(text);
                
                if("candidates" in data_tmp)
                {
                  data_tmp2=data_tmp["candidates"];
                   
                  data_tmp2.forEach(function(row)
                  {
                     var id_data=src+'_'+id.toString()+'_'+i2.toString();
                     //Logger.log(id_data)
                    data2=row["attributes"];
                    //Logger.log(data2);
                    
                    if(data2.length==0)
                    {
                          sheet_esri.appendRow([id, "NOT_FOUND (" +place+")" ]);
                          //returned.push(ids);
                    }
                    else
                    {
                          //sheet_esri.appendRow([id, "FOUND (" +place+")" ]);
                          var addr_type=data2["Addr_type"];
                          var type=data2["Type"];
                          var long_label=data2["LongLabel"];
                          var country_name=data2["CntryName"];
                          var country_code=data2["Country"];
                          var longitude=data2["X"];
                          var latitude=data2["Y"];
                         
                          if(longitude.toString().length>0 && latitude.toString().length>0 )
                          {
                            long_label=long_label.replace("|","_");
                            acc_coord.push(id_data+'||'+long_label+"|"+longitude.toString()+"_"+ latitude.toString())
                          }
                          sheet_esri.appendRow([id_data, id, place, addr_type, type, long_label, country_name, country_code, longitude, latitude ])
                    }
                    i2++;
                    Logger.log(i2);
                  });
                }
                else
                {
                   sheet_esri.appendRow([id_data, id, "NOT_FOUND (" +place+")" ])
                }
            }
            
      }
      i++;
    } );
     flush_write_coord_form_map(src, sheet, i, acc_coord);
     build_url_viewer();
      SpreadsheetApp.getActiveSpreadsheet().toast("ESRI done");
}

function go_darwin(url_darwin, name_sheet_dw, src)
{
  var returned=Array();
   var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
    var sheet = sheetActive.getSheetByName("source");
    var sheet_darwin = sheetActive.getSheetByName(name_sheet_dw);
    var data = sheet.getDataRange().getValues();
   var i=0;
   
   var old_i=-1

   var acc_coord=[];
    data.forEach(function (row) {
      if(i>0)
      {
          if(i!=old_i && i>1)
          {
              
              flush_write_coord_form_map(src, sheet, i, acc_coord)
              old_i=i;
              acc_coord=[];
          }
          var i2=1;
          id=row[0]
          place=row[1];
          country=row[2];
          if(place.length>0)
            { 
                place=place.replace(/\.(?!\s)/g, ". ");
                country=country.replace(/\.(?!\s)/g, ". ");
                 var tmp_url=url_darwin+"q="+encodeURIComponent(place)+"&country="+country+"&explode=true";
                 Logger.log(tmp_url)
                 var response = UrlFetchApp.fetch(tmp_url);
                 var code = response.getResponseCode();
                 //Logger.log(code);
                 var text = response.getContentText();
                 //Logger.log(text);
                var data2=JSON.parse(text);
                //Logger.log(data2);
                if(data2.length==0)
                {
                      sheet_darwin.appendRow([id, "NOT_FOUND (" +place+")" ])
                      //returned.push(ids);
                }
                else
                {
                  acc_coord=[];
                  data2.forEach(function (row2) {
                    
                    var id_data=src+'_'+i.toString()+'_'+ (i2+1).toString();
                    //Logger.log(id_data);
                    //Logger.log(row2);
                    var ids=row2["ids"];
                    var station_numbers=row2["station_numbers"];
                    var continent=row2["continent"];
                    var country=row2["country"];
                    var tag=row2["tag"];
                    var latitude="null";
                    if ("latitude" in row2)
                    {
                        if(row2["latitude"]!==null)
                        {
                          latitude=row2["latitude"];
                        }
                    }

                    var longitude="null"
                    if ("longitude" in row2)
                    {
                        if(row2["longitude"]!==null)
                        {
                          longitude=row2["longitude"];
                        }
                    }
                    var latitude_dms_degree=row2["latitude_dms_degree"];
                    var latitude_dms_minutes=row2["latitude_dms_minutes"];
                    var latitude_dms_seconds=row2["latitude_dms_seconds"];
                    var latitude_dms_direction=row2["latitude_dms_direction"];
                    var longitude_dms_degree=row2["longitude_dms_degree"];
                    var longitude_dms_minutes=row2["longitude_dms_minutes"];
                    var longitude_dms_seconds=row2["longitude_dms_seconds"];
                    var longitude_dms_direction=row2["longitude_dms_direction"];
                    var nb_Records=row2["nb_Records"];
                    var specimen_count_min=row2["specimen_count_min"];
                    var specimen_count_max=row2["specimen_count_max"];
                    var from_first_date=row2["from_first_date"];
                    var from_last_date=row2["from_last_date"];
                    var to_first_date=row2["to_first_date"];
                    var to_last_date=row2["to_last_date"];
                    var query=row2["query"];
                    var query_country=row2["query_country"];  
                    var nb_searched_terms=row2["nb_searched_terms"];  
                    var nb_found_terms=row2["nb_found_terms"];  
                    var searched_terms=row2["searched_terms"];  
                    var found_terms=row2["found_terms"];  
                    var nb_matching_localities=row2["nb_matching_localities"];  
                    //Logger.log("test coords");
                    if(longitude.toString().length>0 && latitude.toString().length>0 )
                    {
                      //Logger.log("long");
                      //Logger.log(longitude);
                      //Logger.log(longitude.toString());
                      tag=tag.replace("|","_")
                      acc_coord.push(id_data+'||'+tag+"|"+longitude.toString()+"_"+ latitude.toString());
                    }
                    if(! returned.includes(ids))
                    {
                      var added_row=[id_data, id,place,  ids,station_numbers,continent,country,tag,latitude,longitude,latitude_dms_degree,latitude_dms_minutes,latitude_dms_seconds,latitude_dms_direction,longitude_dms_degree,longitude_dms_minutes,longitude_dms_seconds,longitude_dms_direction,nb_Records,specimen_count_min,specimen_count_max,from_first_date,from_last_date,to_first_date,to_last_date,query_country, nb_searched_terms,nb_found_terms,searched_terms,found_terms , nb_matching_localities  ];
                      //Logger.log(added_row);
                      sheet_darwin.appendRow(added_row)
                      returned.push(ids);
                      
                    }
                    else
                    {
                      sheet_darwin.appendRow([id_data, id, "NOT FOUND OR POSSIBLE_DUPLICATE (" +place+")" ]);
                    }
                    i2++;
                  });
                }
            }
      }
      i=i+1
    });
     flush_write_coord_form_map(src, sheet, i, acc_coord);
     build_url_viewer()
     SpreadsheetApp.getActiveSpreadsheet().toast("Darwin done");
}

function go_photon()
{
    var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
    var sheet = sheetActive.getSheetByName("source");
    var sheet_photon = sheetActive.getSheetByName(sheet_photon_name);
    var data = sheet.getDataRange().getValues();
    var i=0;
    var old_i=-1;
    var acc_coord=Array();
    src="photon";
    data.forEach(function (row) {
      if(i>0)
      {
        //Logger.log(row);
        if(i!=old_i && i>1)
          {
              
              flush_write_coord_form_map(src, sheet, i, acc_coord)
              old_i=i;
              acc_coord=[];
          }
        id=row[0]
        place=row[1];
          if(place.length>0)
          {
            try
            {
              var tmp_url=url_photon+"q="+encodeURIComponent(place);
              //Logger.log(tmp_url);
              //Logger.log(tmp_url);
              var response = UrlFetchApp.fetch(tmp_url);
              var code = response.getResponseCode();
              //Logger.log(code);
              var text = response.getContentText();
              //Logger.log(text);
              var data2=JSON.parse(text);
              data2=data2["features"];
              for (let i2 = 0; i2 < data2.length; i2++)
              {
                //Logger.log(data2[i2]);
                var tmp=data2[i2]["properties"];
              
                //Logger.log(tmp)
                var geometry=data2[i]["geometry"];
                var id_data=src+'_'+i.toString()+'_'+(i2+1).toString();
                var subject_id=row[0];
                var subject_place=row[1];
                var osm_id=return_from_json(tmp, "osm_id");
                var name=return_from_json(tmp, "name");
                var country=return_from_json(tmp, "country");
                var countrycode=return_from_json(tmp, "countrycode");
                var state=return_from_json(tmp, "state");
                var county=return_from_json(tmp, "county");
                var district=return_from_json(tmp, "district");
                var city=return_from_json(tmp, "city");
                var type=return_from_json(tmp, "type");
                var osm_type=return_from_json(tmp, "osm_type");
                var osm_value=return_from_json(tmp, "osm_value");
                var importance=return_from_json(tmp, "importance");
                var lat=geometry["coordinates"][1];
                var long=geometry["coordinates"][0];
                if(long.toString().length>0 && lat.toString().length>0 )
                  {
                      name=name.replace("|","_")
                      var tmp_acc=id_data+"||"+name+"|"+long.toString()+"_"+ lat.toString();
                      
                      acc_coord.push(tmp_acc);
                      
                  }
                sheet_photon.appendRow([id_data, subject_id, subject_place, osm_id, name, country, countrycode, state, county, district, city, type,osm_type, osm_value, lat.toString(),long.toString(), importance]);
              }
            }
            catch (e) 
            {
              // Logs an ERROR message.
              Logger.log('myFunction() yielded an error: ' + e);
            }
          }
      }
      i=i+1;
    });
    flush_write_coord_form_map(src, sheet, i, acc_coord);
     build_url_viewer();
      SpreadsheetApp.getActiveSpreadsheet().toast("Photon done");
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheetgeo = ss.getSheetByName(sheet_photon_name);
      sheetgeo.activate()
}



function go_geonames()
{
    var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
    var sheet = sheetActive.getSheetByName("source");
    var sheet_geonames = sheetActive.getSheetByName("geonames");
    var data = sheet.getDataRange().getValues();
     var old_i=-1;
    var acc_coord=Array();
    var src="geonames";
   var i=0;
    data.forEach(function (row) {
      if(i>0)
      {
           if(i!=old_i && i>1)
          {
              
              flush_write_coord_form_map(src, sheet, i, acc_coord);
              old_i=i;
              acc_coord=[];
          }
          id=row[0]
          place=row[1];
          country=row[2];
          geoname_feature=row[3];
          country_iso=row[4];

           if(place.length>0)
            {  
                var explode_place=place.split(/[ ,;\///-]/);
                //Logger.log(explode_place);
                var tmp_url=url_geonames+"&q="+encodeURIComponent(place)+"&fcode="+geoname_feature+"&country="+country_iso;
                //Logger.log(tmp_url);
                var response = UrlFetchApp.fetch(tmp_url);
                var code = response.getResponseCode();
                //Logger.log(code);
                var text = response.getContentText();
                //Logger.log(text);
           
              var data2=JSON.parse(text);
              if("geonames" in data2)
              {
              for (let i2 = 1; i2 < data2["geonames"].length; i2++) 
                {
                 
                  var tmp=data2["geonames"][i2];
                  //Logger.log(tmp);
                  var id_data=src+'_'+i.toString()+'_'+i2.toString();
                  var subject_id=row[0];
                  var subject_place=row[1];
                  var subject_country=row[2];
                  var  name=return_from_json(tmp, "name");
                   var explode_name=name.split(/[ ,;\///-]/);
                    //Logger.log("-----------------------------");
                   //Logger.log("result");
                   //Logger.log(name);
                  // Logger.log(explode_place, explode_name);
                   //Logger.log(explode_name);
                   // Logger.log(explode_place);
                   var words_found=count_overlaps(explode_name, explode_place);
                   // Logger.log(words_found);
                    if(words_found>0)
                    {
                      fcl=return_from_json(tmp, "fcl");
                      fclName=return_from_json(tmp, "fclName");
                      fcode=return_from_json(tmp, "fcode");
                      fcodeName=return_from_json(tmp, "fcodeName");
                      countryCode=return_from_json(tmp, "countryCode");
                      geonameId=return_from_json(tmp, "geonameId");
                      countryName=return_from_json(tmp, "countryName");
                      adminCodes1=JSON.stringify(return_from_json(tmp, "adminCodes1"));
                      adminName1=return_from_json(tmp, "adminName1");
                      lat=return_from_json(tmp, "lat");
                      lng=return_from_json(tmp, "lng");
                      if(lat.toString().length>0 && lng.toString().length>0 )
                      {
                          name=name.replace("|","_")
                          acc_coord.push(id_data+"||"+name+"|"+lng.toString()+"_"+ lat.toString())
                      }
                      sheet_geonames.appendRow([id_data, subject_id, subject_place, subject_country,geonameId, name, fcl, fclName, fcode, fcodeName, countryCode, countryName,adminCodes1, adminName1, lat, lng]);

                    }
                    if(i>5)
                    {
                        break;

                    }
                }
              }
            }
        }
       i=i+1;
    
    });
  flush_write_coord_form_map(src, sheet, i, acc_coord);
   build_url_viewer();
  SpreadsheetApp.getActiveSpreadsheet().toast("Geonames done");
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName("geonames");
  sheetgeo.activate()
} 
 

function count_overlaps(array_1, array_2)
{
  returned=0;
  var array_1 = array_1.map(v => v.toLowerCase().trim());
  var array_2 = array_2.map(v => v.toLowerCase().trim());
  //Logger.log(array_1);
   // Logger.log(array_2);
  for(var i=0; i<array_1.length;i++)
  {
    //Logger.log("test");
    //Logger.log(array_1[i]);
    if(array_2.includes(array_1[i]))
    {
      returned++;
    }
  }
  return returned;

}

function go_osm()
{
    Logger.log("go_osm");
    var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
    var sheet = sheetActive.getSheetByName("source");
    var sheet_nominatim = sheetActive.getSheetByName("nominatim");
    var data = sheet.getDataRange().getValues();
    var i=0;
     var old_i=-1;
    var acc_coord=Array();
    var src="osm";
    data.forEach(function (row) {
      if(i>0)
      {
         if(i!=old_i && i>1)
          {
              
              flush_write_coord_form_map(src, sheet, i, acc_coord);
              old_i=i;
              acc_coord=[];
          }
        //Logger.log(row);
        id=row[0]
        place=row[1];
        country=row[2];
        //Logger.log(place)
        //Logger.log(country)
          if(place.length>0)
          {
          var tmp_url="https://nominatim.openstreetmap.org/search.php?format=json&limit=100&q="+encodeURIComponent(place+";"+country)+"&addressdetails=1";
          Logger.log(tmp_url);
          var response = UrlFetchApp.fetch(tmp_url);
          var code = response.getResponseCode();
          //Logger.log(code);
          var text = response.getContentText();
          //Logger.log(text);
          var data2=JSON.parse(text);
          for (let i2 = 0; i2 < data2.length; i2++) 
          {
            var id_data=src+'_'+i.toString()+'_'+(i2+1).toString();
            var tmp=data2[i2];
            var subject_id=row[0];
            var subject_place=row[1];
            var subject_country=row[2];
            var name=return_from_json(tmp, "name");
            var display_name=return_from_json(tmp, "display_name");
            var place_id=return_from_json(tmp, "place_id");
            var osm_id=return_from_json(tmp, "osm_id");
            var v_class=return_from_json(tmp, "class");
            var type=return_from_json(tmp, "type");
            var importance=return_from_json(tmp, "importance");
            var lon=return_from_json(tmp, "lon");
            var lat=return_from_json(tmp, "lat");
            var boundingbox=return_from_json(tmp, "boundingbox");
            var licence=return_from_json(tmp, "licence");
            var country="";
            if("address" in tmp )
            {
              if("country" in tmp["address"])
              {

                country=tmp["address"]["country"];
              }

            }
           if(lat.toString().length>0 && lon.toString().length>0 )
           {
              name=name.replace("|","_")
               acc_coord.push(id_data+"||"+name+"|"+lon.toString()+"_"+ lat.toString())
           }
            sheet_nominatim.appendRow([id_data, subject_id, subject_place, subject_country, name, country, display_name, place_id, osm_id, v_class, type, importance,lon, lat, boundingbox.toString(),licence.toString()]);
          
          }
          }
        
      }
      i=i+1;
    });
     flush_write_coord_form_map(src, sheet, i, acc_coord);
      build_url_viewer();
      SpreadsheetApp.getActiveSpreadsheet().toast("Nominatim done");
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName("nominatim");
  sheetgeo.activate()
      
}


function go_srtm()
{
  var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
  var sheet = sheetActive.getSheetByName("source_srtm");
  var sheet_output = sheetActive.getSheetByName(sheet_srtm_name);
  var data = sheet.getDataRange().getValues();
  var offset_coord=0.003;
    var i=0;
     var old_i=-1;
    var acc_coord=Array();
    var src="osm";
    var url=url_srtm;
    data.forEach(function (row) {
      if(i>0)
      {
          Logger.log(row);
          id_data=row[0];
          name=row[1];
          if(row[2].toString().length>0&&row[3].toString().length)
          {
            if(!isNaN(row[2])&&!isNaN(row[3]))
            {
              x=parseFloat(row[2]);
              y=parseFloat(row[3]);
              Logger.log(x);
              Logger.log(y);
              max_x=x+offset_coord
              max_y=y+offset_coord
              bbox=x.toString()+","+y.toString()+","+max_x.toString()+","+max_y.toString();
              Logger.log(bbox);
              var tmp_url=url+bbox;
              Logger.log(tmp_url);
              var response = UrlFetchApp.fetch(tmp_url);
              var code = response.getResponseCode();
              Logger.log(code);
              var text = response.getContentText();
              Logger.log(text);
              var data2=JSON.parse(text);
              if("features" in data2)
              {
                var init_alt=false;
                var alt=null;
                var bathymetry=null;
                for (let i2 = 0; i2 < data2["features"].length; i2++) 
                {
                    var tmp_data=data2["features"][i2];
                    Logger.log(tmp_data);
                    if("properties" in tmp_data)
                    {
                      if("GRAY_INDEX" in tmp_data["properties"])
                      {
                        var alt_tmp=tmp_data["properties"]["GRAY_INDEX"];
                        Logger.log(alt_tmp);
                        if(!init_alt)
                        {
                            bathymetry=alt_tmp;
                        }
                        else
                        {
                           alt =alt_tmp;
                        }
                        init_alt=true;
                      }  
                    }
                }
                Logger.log("elevation");
                Logger.log(alt);
                 Logger.log("bathymetry")
                Logger.log(bathymetry);
                sheet_output.appendRow([id_data, name, x, y, alt]);
              }
            }
          }
      }
      i++;
    });
}

function go_srtm_rdc()
{
  var sheetActive = SpreadsheetApp.openById(spreadsheet_id);
  var sheet = sheetActive.getSheetByName("source_srtm");
  var sheet_output = sheetActive.getSheetByName(sheet_srtm_drc_name);
  var data = sheet.getDataRange().getValues();
 
    var i=0;
     var old_i=-1;
    var acc_coord=Array();
    var src="srtm_rdc_rmca";
    var url=url_srtm_rdc;
    data.forEach(function (row) {
      if(i>0)
      {
          Logger.log(row);
          id_data=row[0];
          name=row[1];
          if(row[2].toString().length>0&&row[3].toString().length)
          {
            if(!isNaN(row[2])&&!isNaN(row[3]))
            {
              ori_x=row[2]
              ori_y=row[3]
              x=parseFloat(row[2]).toFixed(3);;
              y=parseFloat(row[3]).toFixed(3);
    
              Logger.log(x);
              Logger.log(y);
              max_x=parseFloat(x)+0.001;
              max_y=parseFloat(y)+0.001;
              Logger.log(max_x);
              Logger.log(max_x);
              max_x=parseFloat(max_x).toFixed(3);
              max_y=parseFloat(max_y).toFixed(3);
              bbox="&SUBSET=Long("+x.toString()+","+max_x.toString()+")&SUBSET=Lat("+y.toString()+","+max_y.toString()+")";
              Logger.log(bbox);
              var tmp_url=url+bbox;
              Logger.log(tmp_url);
              var response = UrlFetchApp.fetch(tmp_url);
              var code = response.getResponseCode();
              Logger.log(code);
              var text = response.getContentText();
              Logger.log(text);
              var data2=JSON.parse(text);
              alt="NOT_FOUND"
              //if("domain" in data2 )
              //{
                //data2=data2["domain"];
                if("ranges" in data2)
                {
                  if("GRAY_INDEX" in data2["ranges"])
                  {
                    if("values" in data2["ranges"]['GRAY_INDEX']);
                    {
                      var tmp=0;
                      i=0;
                      for (let i2 = 0; i2 < data2["ranges"]['GRAY_INDEX']["values"].length; i2++) 
                      {
                        tmp=tmp+data2["ranges"]['GRAY_INDEX']["values"][i2];
                        i=i+1;
                      }
                      var tmp_alt=parseFloat(tmp/i);
                      alt=tmp_alt.toString();
                    }
                
                  }
                }
              sheet_output.appendRow([id_data, name, ori_x, ori_y, alt]);
            //}
            }
          }
      }
      i++;
    });
  SpreadsheetApp.getActiveSpreadsheet().toast("SRTM DRC done");
   var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetgeo = ss.getSheetByName(sheet_srtm_drc_name);
  sheetgeo.activate()
}

function go_sparql_wikidata()
{
  const endpoint = "https://query.wikidata.org/sparql";

const query_str = `
SELECT DISTINCT ?item ?itemLabel ?typeLabel WHERE {
  
  ?item 
        rdfs:label ?label .

  FILTER(LANG(?label) IN ("fr", "en"))
  FILTER(
    CONTAINS(LCASE(STR(?label)), "kinkole") 
  )

  BIND(?label AS ?itemLabel)
 
}
ORDER BY STRLEN(STR(?label))
LIMIT 1
`;

const formData = {
  query: query_str,
};

const qHeaders = {
  Accept:"application/sparql-results+json"
};
const options = {
  method: 'post',
  headers: qHeaders,
  payload: formData,
  muteHttpExceptions: true
};
const response =UrlFetchApp.fetch(endpoint, options);
Logger.log(response.getContentText());
}