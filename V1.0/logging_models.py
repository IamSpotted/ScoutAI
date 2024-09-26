from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# Ensure the directory exists
db_dir = os.path.expanduser('~/chatbot/logging')
os.makedirs(db_dir, exist_ok=True)

# Define the PdfDownloadLog model
class PdfDownloadLog(Base):
    __tablename__ = 'pdf_download_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Define the CompletedPagesLog model
class CompletedPagesLog(Base):
    __tablename__ = 'completed_pages_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# SQLite database setup
DATABASE_URL = f'sqlite:///{os.path.join(db_dir, "logging_db.sqlite")}'
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)
