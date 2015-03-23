import argparse
import re
import datetime
import time
import string
import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.dialects.postgresql
import psycopg2

DATE_HEADER_RE = re.compile("For\s+Date:\s+(?P<date>[0-9/]+)")
HEADER_RE = re.compile(r"(?P<recid>[0-9]{2}-[0-9]+)\s+(?P<time>[0-9]{4})" + 
                        "\s+(?P<source>[A-z0-9-\(\)]+)\s+-\s+(?P<category>((([A-Z0-9\(\)-/]+)\s)+|Fraud|Police Training Event))(?P<outcome>[\w /]+)")
LOCATION_RE = re.compile(r"(Location/Address|Location|Vicinity of):\s*(?P<addr>.*)")
LAT_LON_RE = re.compile(r"Lat:\s+(?P<lat>[0-9\.\+-]+)\s+Lon:\s+(?P<lon>[0-9\.\+-]+)")

LOCATION_CHANGE_RE = re.compile(r"Location\s+Change:\s*(?P<addr>.*)")
MODIFIED_RE = re.compile(r"\[Modified:\s+(?P<moddate>[0-9/]+)\]")

ARREST_NAME_RE = re.compile(r"Arrest:\s*(?P<last_name>[A-z' -]+),\s*(?P<first_name>[A-z]+)")
SUMMONS_NAME_RE = re.compile(r"Summons:\s*(?P<last_name>[A-z' -]+),\s*(?P<first_name>[A-z]+)")
PC_NAME_RE = re.compile(r"P/C:\s*(?P<last_name>[A-z' -]+),\s*(?P<first_name>[A-z]+)")
ADDRESS_RE = re.compile(r"Address:\s*(?P<address>.+)")
AGE_RE = re.compile(r"Age:\s*(?P<age>[0-9]+)")
CHARGES_RE = re.compile(r"Charges:\s+(?P<charges>.+)")

CALL_TAKER_RE = re.compile(r"Call\s+Taker:\s+(?P<number>[0-9]+)\s+-\s+(?P<last_name>[A-z']+),\s+(?P<first_name>[A-z]+)")
PRIMARY_ID_RE = re.compile(r"Primary\s+Id:\s+(?P<number>[0-9]+)\s+-\s+(?P<last_name>[A-z']+),\s+(?P<first_name>[A-z]+)")
OFFICER_ID_RE = re.compile(r"ID:\s+(?P<number>[0-9A-z]+)\s+-\s+(?P<last_name>[A-z']+),\s+(?P<first_name>[A-z]+)")
HANGING_OFFICER_ID_RE = re.compile(r"(?P<number>[0-9]+)\s+-\s+(?P<last_name>[A-z]+),\s+(?P<first_name>[A-z]+)")
JURISDICTION_RE = re.compile(r"Jurisdiction:\s*(?P<juris>.*)")
ARRIVAL_RE = re.compile("(Disp-(?P<disptime>[0-9]{2}:[0-9]{2}:[0-9]{2}))?" + 
                         '(\s*Enrt-[0-9:]{8})?' +
                        "(\s*Arvd-(?P<arvtime>[0-9]{2}:[0-9]{2}:[0-9]{2}))?\s*" + 
                        "(Clrd-(?P<clrdtime>([0-9]{2}:[0-9]{2}:[0-9]{2})|([0-9/]{10} @ [0-9:]{8})))?")
REFER_TO_AUX_RE = re.compile(r"Refer\s+To\s+(?P<aux_type>[\w \/]+):\s+(?P<aux_id>[0-9A-z-]+)")
K9_RE = re.compile(r"K9RIOT.+")
CALL_CLOSED_BY_RE = re.compile("Call\s+Closed\s+By.+")

class DuplicateError(Exception):
    pass

class ParsingError(Exception):
    """ An exception type to throw when the 
        file cannot be interpreted 
    """
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="The file to read report information from in text format.")
    args = parser.parse_args()

    engine = create_engine("postgresql+psycopg2:///keene_police").connect()

    with open(args.source, "r") as handle:
    
        # first, extract the date of the report
        for line in handle:
            if line.strip():
                break

        match = DATE_HEADER_RE.search(line.strip())
        if not match:
            raise ParsingError("Unable to interpret header line: {0}".format(line))
        date_val = datetime.datetime.strptime(match.groupdict()["date"], "%m/%d/%Y")

        print("Processing date {0}".format(date_val))

        # now, remove the next header of field names
        for line in handle:
            if line.strip():
                break

        # now, we're in the guts of the report. Start reading records
        lines = [l.strip() for l in handle if l.strip()]
        position = 0
        Session = sessionmaker(bind  = engine)
        session = Session()
        while True:
            try:
                (record, position) = read_record(lines, position, date_val, session)
            except DuplicateError  as e:
                print(e)
                break

            if position == -1:
                break
        session.commit()

def read_record(lines, position, report_date, db_session):
    """ Reads a record from the source file defined by `lines` starting at line number `position`.
        Return a 2-tuple representing:
            1) the record that was read and 
            2) the position at which the next record begins, or -1 if the end of the file has been reached
    """
    incident = models.Incident()

    print(lines[position])
    match = HEADER_RE.match(lines[position])
    header_info = match.groupdict()

    incident.report_id = header_info["recid"]

    rectime = datetime.datetime.strptime(header_info["time"], "%H%M").time()
    timestamp = datetime.datetime.combine(report_date.date(), rectime)

    incident.dispatch_time = timestamp
    incident.dispatch_source = header_info["source"]
    incident.category = header_info["category"]
    incident.outcome = header_info["outcome"]

    newpos = position + 1
    responding_officers = []

    last_entity_type = None
    last_entity_subtype = None

    for line in lines[newpos:]:

        # rarely, a file will contain duplicated content
        if line.startswith("For Date"):
            raise DuplicateError("Duplicated content!")

        # check if a new record starts on this line
        match = HEADER_RE.match(line)
        if match:
            break

        # use the beginning of this line to inform which RE to use
        if line.strip() == '' or not [x for x in line if x in string.printable]: # skip blanks
            pass
        elif line.startswith("Call Closed By") or line.startswith("Call Modified By") or \
                line.startswith("Cleared By") or line.startswith("Con:") or \
                line.startswith("Arrived By") or line.startswith("Dispatched By") \
                or line.startswith("DOB") or line.startswith("Juvenile Arrest") or \
                line.startswith("Enroute By") or line.startswith("Juvenile Protective Custody"):
            pass # ignore those
        elif line.startswith("Additional Activity:"):
            last_entity_type = "additional_activity"
        elif line.startswith("Call Taker:"):
            last_entity_type = "call_taker"
            match = CALL_TAKER_RE.match(line)
            first_name = match.groupdict()["first_name"].strip()
            last_name = match.groupdict()["last_name"].strip()
            number = int(match.groupdict()["number"].strip())

            dispatcher = db_session.query(models.Dispatcher).filter(models.Dispatcher.number == number).first()
            if not dispatcher:
                disp = models.Dispatcher(number = number, first_name = first_name, last_name = last_name)
                db_session.add(disp)
            incident.call_taker = dispatcher

        elif line.startswith("Location/Address:") or line.startswith("Location:") or line.startswith("Vicinity of:"):
            last_entity_type = "location_address"
            match = LOCATION_RE.match(line)
            location = match.groupdict()["addr"].strip()
            incident.location = location

        elif line.startswith("Lat:"):
            last_entity_type = "lat_lon"
            match = LAT_LON_RE.match(line)
            incident.latitude = float(match.groupdict()["lat"].strip())
            incident.longitude = float(match.groupdict()["lon"].strip())

        elif line.startswith("Location Change:"):
            last_entity_type = "location_change"
            match = LOCATION_CHANGE_RE.match(line)
            location_and_date = match.groupdict()["addr"].strip()
            mod_date_match = MODIFIED_RE.search(location_and_date)
            if mod_date_match: # sometimes the line wraps around
                mod_date = mod_date_match.groupdict()["moddate"].strip()
                change_date = datetime.datetime.strptime(mod_date, "%m/%d/%Y%H%M")
            else:
               change_date = None
            if "[Modified" in location_and_date:
                location = location_and_date[:location_and_date.index("[Modified")]
            else:
                location = location_and_date

            loc_change = models.LocationChange(incident = incident, location=location, change_date=change_date)
            db_session.add(loc_change)
        elif line.startswith("Primary Id:"):
            last_entity_type = "primary_id"
            match = PRIMARY_ID_RE.match(line)
            first_name = match.groupdict()["first_name"].strip()
            last_name = match.groupdict()["last_name"].strip()
            number = int(match.groupdict()["number"].strip())

            officer = db_session.query(models.Officer).filter(models.Officer.number == number).first()
            if not officer:
                officer = models.Officer(number = number, first_name = first_name, last_name = last_name)
                db_session.add(officer)

            incident.primary_officer = officer

        elif line.startswith("Jurisdiction:"):
            last_entity_type = "jurisdiction"
            match = JURISDICTION_RE.match(line)
            incident.jurisdiction = match.groupdict()["juris"].strip()

        elif line.startswith("ID:"):
            last_entity_type = "officer"
            match = OFFICER_ID_RE.match(line)
            first_name = match.groupdict()["first_name"].strip()
            last_name = match.groupdict()["last_name"].strip()
            number_str = match.groupdict()["number"].strip()
            if number_str.startswith("K9"):
                number_str = "9000"
            number = int(number_str)

            officer = db_session.query(models.Officer).filter(models.Officer.number == number).first()
            if not officer:
                officer = models.Officer(number = number, first_name = first_name, last_name = last_name)
                db_session.add(officer)

            resp_officer = models.RespondingOfficer(incident = incident, officer = officer)
            db_session.add(resp_officer)
            responding_officers.append(resp_officer)

        elif line.startswith("Refer"):
            match = REFER_TO_AUX_RE.match(line)
            aux_type = match.groupdict()["aux_type"].strip()
            aux_id = match.groupdict()["aux_id"].strip()
            last_entity_type = "refer_" + aux_type

            incident.aux_event_type = aux_type
            incident.aux_event_id = aux_id
            if aux_type == "P/C":
                custody = models.ProtectiveCustody(incident=incident)
                db_session.add(custody)
            elif aux_type == "Arrest":
                arrest = models.Arrest(incident=incident)
                db_session.add(arrest)
            elif aux_type == "Summons":
                summons = models.Summon(incident=incident)
                db_session.add(summons)

        elif last_entity_type == "officer" and HANGING_OFFICER_ID_RE.match(line):
            pass # not sure what this means when it's present

        # probably a continuation of a previous tag
        elif last_entity_type == "officer":
            response = responding_officers[-1]
            arv_match = ARRIVAL_RE.match(line)
            k9_match = K9_RE.match(line)

            if arv_match:
                cleared_time = arv_match.groupdict()["clrdtime"]
                arrival_time = arv_match.groupdict()["arvtime"]
                dispatch_time = arv_match.groupdict()["disptime"]
                
                if cleared_time and len(cleared_time) == 8:
                    response.cleared_time = datetime.datetime.combine(report_date.date(),
                            datetime.datetime.strptime(cleared_time, "%H:%M:%S").time())
                elif cleared_time:
                    response.cleared_time = datetime.datetime.strptime(cleared_time, "%m/%d/%Y @ %H:%M:%S")

                if arrival_time and len(arrival_time) == 8:
                    response.arrival_time = datetime.datetime.combine(report_date.date(),
                            datetime.datetime.strptime(arrival_time, "%H:%M:%S").time())
                elif arrival_time:
                    response.arrival_time = datetime.datetime.strptime(arrival_time, "%m/%d/%Y @ %H:%M:%S")

                if dispatch_time and len(dispatch_time) == 8:
                    response.dispatch_time = datetime.datetime.combine(report_date.date(),
                            datetime.datetime.strptime(dispatch_time, "%H:%M:%S").time())
                elif dispatch_time:
                    response.dispatch_time = datetime.datetime.strptime(dispatch_time, "%m/%d/%Y @ %H:%M:%S")

            elif k9_match:
                pass # can't use this right now
            else:
                raise ParsingError("Unrecognized Input {0}".format(line))
        elif last_entity_type == "refer_P/C":
            if line.startswith("P/C"):
                match = PC_NAME_RE.match(line)
                custody.last_name = match.groupdict()["last_name"]
                custody.first_name = match.groupdict()["first_name"]
            elif line.startswith("Address"):
                match = ADDRESS_RE.match(line)
                custody.address = match.groupdict()["address"].strip()
            elif line.startswith("Age"):
                match = AGE_RE.match(line)
                custody.age_at_custody = int(match.groupdict()["age"].strip())
            elif line.startswith("Charges"):
                last_entity_subtype = "charges"
                match = CHARGES_RE.match(line)
                custody.charges = match.groupdict()["charges"].strip()
            elif last_entity_subtype == "charges":
                custody.charges += "," + line.strip()
            else:
                raise ParsingError("Unrecognized Input {0}".format(line))
        elif last_entity_type == "refer_Arrest":
            if line.startswith("Arrest:"):
                match = ARREST_NAME_RE.match(line)
                arrest.last_name = match.groupdict()["last_name"]
                arrest.first_name = match.groupdict()["first_name"]
            elif line.startswith("Address"):
                match = ADDRESS_RE.match(line)
                arrest.address = match.groupdict()["address"].strip()
            elif line.startswith("Age"):
                match = AGE_RE.match(line)
                arrest.age = int(match.groupdict()["age"].strip())
            elif line.startswith("Charges"):
                last_entity_subtype = "charges"
                match = CHARGES_RE.match(line)
                arrest.charges = match.groupdict()["charges"].strip()
            elif last_entity_subtype == "charges":
                pass # ignore duplicated charges
            else:
                raise ParsingError("Unrecognized Input {0}".format(line))
        elif last_entity_type == "refer_Summons":
            if line.startswith("Summons:"):
                match = SUMMONS_NAME_RE.match(line)
                summons.last_name = match.groupdict()["last_name"]
                summons.first_name = match.groupdict()["first_name"]
            elif line.startswith("Address"):
                match = ADDRESS_RE.match(line)
                summons.address = match.groupdict()["address"].strip()
            elif line.startswith("Age"):
                match = AGE_RE.match(line)
                summons.age = int(match.groupdict()["age"].strip())
            elif line.startswith("Charges"):
                last_entity_subtype = "charges"
                match = CHARGES_RE.match(line)
                summons.charges = match.groupdict()["charges"].strip()
            elif last_entity_subtype == "charges":
                pass # ignore duplicated charges
            else:
                raise ParsingError("Unrecognized Input {0}".format(line))
        elif last_entity_type == "location_change":
            pass # sometimes the line wraps around
        elif last_entity_type == "location_address" and not ":" in line:
            incident.location += " " + line.strip()
        elif last_entity_type == "additional_activity":
            pass 
        else:
            raise ParsingError(u"Unrecognized Input '{0}'".format(line))

        newpos += 1

    db_session.add(incident)
    if newpos == len(lines):
        return (None, -1)
    else:
        return (None, newpos)


if __name__ == "__main__":
    main()

