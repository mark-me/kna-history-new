from flask import Flask, render_template
from config import Config
from content_db import db, ActivityService

# Import blueprints
from blueprints.core import core_bp
from blueprints.activity import activity_bp
from blueprints.member import member_bp
from blueprints.media import media_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
Config.init_app(app)

# Register blueprints
app.register_blueprint(core_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(member_bp)
app.register_blueprint(media_bp)



# ─── Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    activities = ActivityService.list_activities(db.session, limit=20)
    return render_template("index.html", activities=activities)


# ─── Application Startup ─────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✓ Database tables created/verified")

    print(f"✓ Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"✓ Resources directory: {app.config['RESOURCES_FOLDER']}")
    print(f"✓ Uploads directory: {app.config['UPLOAD_FOLDER']}")

    app.run(debug=app.config['DEBUG'])
