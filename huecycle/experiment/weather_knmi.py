import requests
import pprint
import time
from datetime import datetime, timedelta


public_key = "eyJvcmciOiI1ZTU1NGUxOTI3NGE5NjAwMDEyYTNlYjEiLCJpZCI6IjI4ZWZlOTZkNDk2ZjQ3ZmE5YjMzNWY5NDU3NWQyMzViIiwiaCI6Im11cm11cjEyOCJ9"

my_key = "eyJvcmciOiI1ZTU1NGUxOTI3NGE5NjAwMDEyYTNlYjEiLCJpZCI6IjdhZTQ1MDZmNTkzNzRhYjE4MWQ3YzVhMmRlZmQ5MDY5IiwiaCI6Im11cm11cjEyOCJ9"

quarter = timedelta(minutes=20)


""" potentiele meetwaarden die representatief zijn voor de CCT in de lucht:
mor_10:
    Visibility, meteorological day vision, 10'
    https://vocab.nerc.ac.uk/standard_name/visibility_in_air/ (meter)
h_ceilom_10:
    Clouds, the height of the base of the first layer, 10' (foot)
    https://vocab.nerc.ac.uk/standard_name/cloud_base_altitude/
h1_ceilom_10:
    Clouds, the height of the base of the first layer (ceilometer), 10' (foot)
    https://vocab.nerc.ac.uk/standard_name/cloud_base_altitude/
h2_ceilom_10:
    Clouds, the height of the base of the second layer (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_base_altitude/
h3_ceilom_10:
    Clouds, the height of the base of the third layer (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_base_altitude/
n_ceilom_10:
    Clouds, total degree of coverage (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_area_fraction/
    the unit of cloud amount – okta – is an eighth of the sky dome covered by cloud
n1_ceilom_10:
    Clouds, degree of coverage first layer (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_area_fraction/
    the unit of cloud amount – okta – is an eighth of the sky dome covered by cloud
n2_ceilom_10:
    Clouds, degree of coverage second layer (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_area_fraction/
    the unit of cloud amount – okta – is an eighth of the sky dome covered by cloud
n3_ceilom_10:
    Clouds, degree of coverage third layer (ceilometer), 10'
    https://vocab.nerc.ac.uk/standard_name/cloud_area_fraction/
    the unit of cloud amount – okta – is an eighth of the sky dome covered by cloud
q_glob_10:
    Radiation, global, average, 10' (W/m²)
    https://vocab.nerc.ac.uk/standard_name/downwelling_shortwave_flux_in_air/
sq_10:
    Sunshine duration, duration derived from radiation, 10' (minute)
    https://vocab.nerc.ac.uk/standard_name/duration_of_sunshine/
ww_cor_10:
    Weather, validated code, present weather sensor, 10'
    KNMI: Handboek waarnemingen: https://cdn.knmi.nl/system/data_center_publications/files/000/070/797/original/handboekwaarnemingen_KNMI_2000.pdf
ww_curr_10:
    Weather, code, present weather sensor, 10'
    WMO table 4680: https://met.nps.edu/~bcreasey/mr3222/files/helpful/DecodeLandSynopticCode.pdf
"""

def get_edr():
    api = "https://api.dataplatform.knmi.nl/edr"
    timestamp = (datetime.utcnow() - quarter).strftime("%Y-%m-%dT%H:%M:00Z/..")
    r = requests.get(api+'/collections/observations/locations/06275', params={
            'datetime': timestamp,
            'parameter-name': 'q_glob_10,t_dryb_10,ww_cor_10,ww_curr_10',
        },
        headers={'Authorization': f"{my_key}"})
    response = r.json()
    #pprint.pprint(response)
    ranges = response['ranges']
    return {k: ranges[k]['values'][0] for k in ranges}


""" van W/m² naar color temperatuur of witbalans:
    1. Zon: ~4.000 K (depends on source)
    2. Zwaar bewolkt: 10.000 K
    
"""

while True:
    try:
        print(get_edr())
    except Exception as e:
        print("ERROR:", type(e), str(e))
    time.sleep(300)
