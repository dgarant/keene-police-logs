from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.dialects.postgresql
import psycopg2

engine = create_engine("postgresql+psycopg2:///keene_police").connect()
engine.execute("delete from arrest")
engine.execute("delete from summons")
engine.execute("delete from protective_custody")
engine.execute("delete from responding_officer")
engine.execute("delete from location_change")
engine.execute("delete from incident")
engine.execute("delete from dispatcher")
engine.execute("delete from officer")
