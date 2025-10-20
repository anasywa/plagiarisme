import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()

def create_container():
    database_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost/plagiarisme")
    return {
        "DATABASE_URL": database_url,
        "db": db,
    }
