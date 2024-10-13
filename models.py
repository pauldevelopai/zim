from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime

# Base class for SQLAlchemy models
Base = declarative_base()

# Define the transcription model
class Transcription(Base):
    __tablename__ = 'transcriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    transcription = Column(Text, nullable=False)
    word_file_path = Column(String, nullable=True)  # New column to store Word file path
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Create an SQLite engine
engine = create_engine('sqlite:///transcriptions.db', echo=True)

# Create tables in the database
Base.metadata.create_all(engine)

# Create a session maker
Session = sessionmaker(bind=engine)
session = Session()