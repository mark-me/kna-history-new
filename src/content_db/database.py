# content_db/database.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Define Base class for models
class Base(DeclarativeBase):
    pass

# Create Flask-SQLAlchemy instance using our Base class
db = SQLAlchemy(model_class=Base)

# For backwards compatibility
def get_session():
    """Get database session - for Flask-SQLAlchemy, use db.session instead"""
    return db.session
