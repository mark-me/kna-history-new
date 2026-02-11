from flask import Blueprint, render_template, request

from content_db import ActivityService, Activity, db

core_bp = Blueprint(
    'core',
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

@core_bp.route("/")
def index():
    activities = ActivityService.list_activities(db.session, limit=20)
    return render_template("index.html", activities=activities)


@core_bp.route("/activities")
def activity_list():
    year = request.args.get("year")
    type_ = request.args.get("type")
    q = request.args.get("q", "")

    query = Activity.query
    if year:
        query = query.filter(Activity.year == int(year))
    if type_:
        query = query.filter(Activity.type == type_)
    if q:
        query = query.filter(
            db.or_(
                Activity.title.ilike(f"%{q}%"),
                Activity.description.ilike(f"%{q}%")
            )
        )

    activities = query.order_by(Activity.year.desc()).limit(50).all()
    return render_template("activity_list.html", activities=activities)