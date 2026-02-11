# content_db/database.py
from flask_sqlalchemy import SQLAlchemy

# Create Flask-SQLAlchemy instance
# This automatically creates a Base class with .query support
db = SQLAlchemy()

# Export the Base class for models to use
# This is the declarative base that has .query attribute
Base = db.Model

# For backwards compatibility
def get_session():
    """Get database session - for Flask-SQLAlchemy, use db.session instead"""
    return db.session
