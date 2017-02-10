import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.dialects.postgresql
import psycopg2
import models
import os
import re
import csv
import StringIO
import time

class GeocodeError(Exception):
    pass

class AuthenticationError(Exception):
    pass


TAGGED_LOCATION_RE = re.compile("\s*\[.+\]\s*")
ADDRESS_WITH_NUMBER = re.compile("[1-9][0-9]*\s+")
ADDRESS_WITH_ZERO_NUMBER = re.compile("^\s*0\s+(.+)")

def main():
    engine = create_engine("postgresql+psycopg2:///keene_police_logs").connect()
    Session = sessionmaker(bind = engine)
    session = Session()

    incidents_with_locations = session.query(models.Incident) \
        .filter(models.Incident.latitude != None) \
        .distinct(models.Incident.location, models.Incident.latitude, models.Incident.longitude).all()

    location_dict = dict([(i.location, [i.latitude, i.longitude]) for i in incidents_with_locations])
    recs_since_commit = 0

    recs_to_geocode = []
    for incident in session.query(models.Incident).filter(models.Incident.latitude == None):
        cleaned_q = clean_query(incident.location)
        print("----------------")
        print("{0} -> {1}".format(incident.location, cleaned_q))

        if incident.location in location_dict:
            print("Found {0} in the location dictionary".format(incident.location))
            loc = location_dict[incident.location]
            print(loc)
            incident.latitude = loc[0]
            incident.longitude = loc[1]
            continue

        if cleaned_q in location_dict:
            print("Found {0} in the location dictionary".format(cleaned_q))
            loc = location_dict[cleaned_q]
            print(loc)
            incident.latitude = loc[0]
            incident.longitude = loc[1]
            continue

        recs_to_geocode.append(cleaned_q)

        if len(recs_to_geocode) >= 5:
            session.commit()
            batch_geocode(recs_to_geocode)
            session.commit()
            break
        

def batch_geocode(records):
    content = StringIO.StringIO()
    content.write("Bing Spatial Data Services|2.0\n")
    writer = csv.DictWriter(content, fieldnames=["Id", "GeocodeRequest/Culture", "GeocodeRequest/Address/AddressLine", "GeocodeRequest/Address/AdminDistrict", "GeocodeRequest/Address/CountryRegion", "GeocodeRequest/Address/PostalCode", "GeocodeRequest/Address/PostalTown"], delimiter="|")
    writer.writeheader()

    for i, address in enumerate(records):
        record = {
            "Id" : str(i),
            "GeocodeRequest/Culture" : "en-US",
            "GeocodeRequest/Address/AddressLine" : address,
            "GeocodeRequest/Address/AdminDistrict" : "NH",
            "GeocodeRequest/Address/CountryRegion" : "US",
            "GeocodeRequest/Address/PostalCode" : "03431",
            "GeocodeRequest/Address/PostalTown" : "Keene"
        }
        writer.writerow(record)
    post_content = content.getvalue()
    print(post_content)
    r = requests.post("http://spatial.virtualearth.net/REST/v1/Dataflows/Geocode", 
            params={"input" : "pipe",
                    "output" : "json",
                    "key" : os.environ["BING_API_KEY"]
            }, data=post_content)
    result = r.json()
    if result.status != 201:
        raise ValueError("Bad status code from {0}".format(r.url))

    result_url = [r["url"] for r in result["resourceSets"][0]["resources"]["links"] if r["role"] == "self"][0]
    #time.sleep()

    #r = requests.post("http://dev.virtualearth.net/REST/v1/Locations/US/NH/03431/Keene/{0}".format(query_text),

def old():
        try:
            address, point = run_structured_query(cleaned_q)
        except GeocodeError:
            try:
                address, point = run_unstructured_query(cleaned_q)
            except GeocodeError:
                print("{0} Failed!".format(cleaned_q))
        recs_since_commit += 1

        print(address)
        print(point)
        incident.formatted_location = address
        incident.latitude = point[0]
        incident.longitude = point[1]
        location_dict[cleaned_q] = point
        if recs_since_commit == 50:
            session.commit()

def clean_query(query_text):
    q = TAGGED_LOCATION_RE.sub("", query_text)
    elems = q.split(" - ")
    q = elems[-1]
    if "@" in q:
        elems = q.split("@")
        if ADDRESS_WITH_NUMBER.match(elems[0]):
            return elems[0].strip()
        elif ADDRESS_WITH_NUMBER.match(elems[1]):
            return elems[1].strip()
        else:
            for i in range(len(elems)):
                elems[i] = ADDRESS_WITH_ZERO_NUMBER.sub(r"\1", elems[i]).strip()
            q = " & ".join(elems)
    return q

def handle_result(query_text, r):
    if r.status_code != 200:
        raise GeocodeError("Failed to geocode in a with query {0}".format(query_text))

    try:
        resources = r.json()["resourceSets"][0]["resources"]
        if resources:
            resource = resources[0]
        else:
            raise GeocodeError("No matches found for {0}".format(query_text))
    except Exception as e:
        print(r.json())
        raise e

    if set(["Good"]) != set(resource["matchCodes"]):
        raise GeocodeError("Bad match quality for {0}".format(query_text))

    return (resource["address"]["formattedAddress"], resource["point"]["coordinates"])
    

def run_structured_query(query_text):
    r = requests.get("http://dev.virtualearth.net/REST/v1/Locations/US/NH/03431/Keene/{0}".format(query_text),
            params = {
                "includeNeighborhood" : 1,
                "key" : os.environ["BING_API_KEY"]
            })
    return handle_result(query_text, r)

def run_unstructured_query(query_text):
    r = requests.get("http://dev.virtualearth.net/REST/v1/Locations/",
            params = {
                "query" : query_text + " Keene, NH",
                "includeNeighborhood" : 1,
                "key" : os.environ["BING_API_KEY"]
            })
    return handle_result(query_text, r)


if __name__ == "__main__":
    main()


