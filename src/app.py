import locale
from datetime import date, datetime

from flask import Flask

from blueprints.activity import activity_bp

# Import blueprints
from blueprints.core import core_bp
from blueprints.media import media_bp
from blueprints.member import member_bp
from config import Config
from content_db import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
Config.init_app(app)

# Register blueprints
app.register_blueprint(core_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(member_bp)
app.register_blueprint(media_bp)

locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')

def _format_date(value, fmt: str = "%d-%m-%Y") -> str:
    """Safe date formatting filter"""
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime(fmt)
    return str(value)  # fallback for unexpected types

# Register filters
app.jinja_env.filters["date"]       = lambda v: _format_date(v, "%d-%m-%Y")
app.jinja_env.filters["date_long"]  = lambda v: _format_date(v, "%d %B %Y")
app.jinja_env.filters["date_short"] = lambda v: _format_date(v, "%d %b %Y")
app.jinja_env.filters["date_time"]  = lambda v: _format_date(v, "%d-%m-%Y %H:%M")

# ─── Application Startup ─────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✓ Database tables created/verified")

    print(f"✓ Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"✓ Resources directory: {app.config['RESOURCES_FOLDER']}")
    print(f"✓ Uploads directory: {app.config['UPLOAD_FOLDER']}")

    app.run(debug=app.config["DEBUG"])
