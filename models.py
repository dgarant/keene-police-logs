# coding: utf-8
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

class Arrest(Base):
    __tablename__ = u'arrest'

    id = Column(Integer, primary_key=True, server_default=text("nextval('arrest_id_seq'::regclass)"))
    incident_id = Column(ForeignKey(u'incident.id'), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    age_at_arrest = Column(Integer)
    charges = Column(String(100))
    address = Column(String(100))

    incident = relationship(u'Incident')


class Dispatcher(Base):
    __tablename__ = u'dispatcher'

    id = Column(Integer, primary_key=True, server_default=text("nextval('dispatcher_id_seq'::regclass)"))
    number = Column(Integer)
    first_name = Column(String(50))
    last_name = Column(String(50))


class Incident(Base):
    __tablename__ = u'incident'

    id = Column(Integer, primary_key=True, server_default=text("nextval('incident_id_seq'::regclass)"))
    report_id = Column(String(10))
    dispatch_time = Column(DateTime)
    dispatch_source = Column(String(50))
    category = Column(String(50))
    outcome = Column(String(50))
    call_taker_id = Column(ForeignKey(u'dispatcher.id'))
    primary_officer_id = Column(ForeignKey(u'officer.id'))
    location = Column(String(300))
    latitude = Column(Numeric(8, 6))
    longitude = Column(Numeric(8, 6))
    jurisdiction = Column(String(100))
    aux_event_type = Column(String(100))
    aux_event_key = Column(String(100))

    call_taker = relationship(u'Dispatcher')
    primary_officer = relationship(u'Officer')


class LocationChange(Base):
    __tablename__ = u'location_change'

    id = Column(Integer, primary_key=True, server_default=text("nextval('location_change_id_seq'::regclass)"))
    incident_id = Column(ForeignKey(u'incident.id'), nullable=False)
    location = Column(String(300))
    change_date = Column(Date)

    incident = relationship(u'Incident')


class Officer(Base):
    __tablename__ = u'officer'

    id = Column(Integer, primary_key=True, server_default=text("nextval('officer_id_seq'::regclass)"))
    number = Column(Integer)
    last_name = Column(String(50))
    first_name = Column(String(50))


class ProtectiveCustody(Base):
    __tablename__ = u'protective_custody'

    id = Column(Integer, primary_key=True, server_default=text("nextval('protective_custody_id_seq'::regclass)"))
    incident_id = Column(ForeignKey(u'incident.id'), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    address = Column(String(300))
    age_at_custody = Column(Integer)
    charges = Column(String(100))

    incident = relationship(u'Incident')


class RespondingOfficer(Base):
    __tablename__ = u'responding_officer'

    id = Column(Integer, primary_key=True, server_default=text("nextval('responding_officer_id_seq'::regclass)"))
    incident_id = Column(ForeignKey(u'incident.id'), nullable=False)
    officer_id = Column(ForeignKey(u'officer.id'), nullable=False)
    dispatch_time = Column(DateTime)
    arrival_time = Column(DateTime)
    cleared_time = Column(DateTime)

    incident = relationship(u'Incident')
    officer = relationship(u'Officer')

class Summon(Base):
    __tablename__ = u'summons'

    id = Column(Integer, primary_key=True, server_default=text("nextval('summons_id_seq'::regclass)"))
    incident_id = Column(ForeignKey(u'incident.id'), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    age_at_summons = Column(Integer)
    charges = Column(String(100))
    address = Column(String(100))

    incident = relationship(u'Incident')
