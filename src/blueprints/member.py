from flask import Blueprint, flash, redirect, render_template, request, url_for

from content_db import MediaAppearance, Member, MemberService, Role, db

from .forms import QuickMemberForm


member_bp = Blueprint(
    "member", __name__, url_prefix="/member", template_folder="../templates/member"
)


@member_bp.route("/")
def list():
    """List all members (GDPR-approved only by default)"""
    # Get filter parameters
    show_all = request.args.get("show_all", "false").lower() == "true"
    search = request.args.get("q", "").strip()

    # Build query
    query = Member.query

    # Apply GDPR filter unless show_all is requested
    if not show_all:
        query = query.filter(Member.gdpr_permission == 1)

    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Member.current_first_name.ilike(f"%{search}%"),
                Member.current_last_name.ilike(f"%{search}%"),
                Member.id_member.ilike(f"%{search}%"),
            )
        )

    # Order and execute
    members = query.order_by(Member.current_last_name, Member.current_first_name).all()

    return render_template("member_list.html", members=members, search=search)


@member_bp.route("/<id_member>")
def detail(id_member):
    """Show member profile with roles and media appearances"""
    member = Member.query.filter_by(id_member=id_member).first()

    if not member:
        flash("Lid niet gevonden", "danger")
        return redirect(url_for("member_list"))

    # Check GDPR permission
    if member.gdpr_permission != 1:
        flash("Dit lid is niet zichtbaar in het openbare archief", "warning")
        return redirect(url_for("member_list"))

    # Get member's roles
    roles = (
        Role.query.filter_by(id_member=id_member)
        .order_by(Role.id_activity.desc())
        .all()
    )

    # Get media appearances
    appearances = (
        MediaAppearance.query.filter_by(id_member=id_member)
        .order_by(MediaAppearance.id_media.desc())
        .all()
    )

    return render_template(
        "member_detail.html", member=member, roles=roles, appearances=appearances
    )


@member_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new member"""
    form = QuickMemberForm()

    if form.validate_on_submit():
        member = MemberService.quick_create_member(
            db.session,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            id_lid=form.id_lid.data or None,
        )
        db.session.commit()

        flash(
            f"Lid {member.current_first_name} {member.current_last_name} aangemaakt",
            "success",
        )
        return redirect(url_for("member_detail", id_member=member.id_member))

    return render_template("member_form.html", form=form, title="Nieuw lid")


@member_bp.route("/quick-create", methods=["POST"])
def member_quick_create():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    id_lid = request.form.get("id_lid", "").strip()

    if not first_name or not last_name:
        flash("Voornaam en achternaam zijn verplicht", "danger")
        return render_template("partials/member_quick_form.html")

    with db.session.begin():
        member = MemberService.quick_create_member(
            db.session,
            first_name=first_name,
            last_name=last_name,
            id_lid=id_lid or None,
        )

    # Return updated <select> with new member selected
    members = Member.query.order_by(Member.current_last_name).all()
    return render_template(
        "partials/member_select.html", members=members, selected=member.id_member
    )


@member_bp.route("/<id_member>/edit", methods=["GET", "POST"])
def edit(id_member):
    """Edit an existing member"""
    member = Member.query.filter_by(id_member=id_member).first()

    if not member:
        flash("Lid niet gevonden", "danger")
        return redirect(url_for("member_list"))

    form = QuickMemberForm()

    if form.validate_on_submit():
        member.current_first_name = form.first_name.data
        member.current_last_name = form.last_name.data
        db.session.commit()

        flash("Lid bijgewerkt", "success")
        return redirect(url_for("member_detail", id_member=member.id_member))

    # Pre-populate form
    if request.method == "GET":
        form.first_name.data = member.current_first_name
        form.last_name.data = member.current_last_name
        form.id_lid.data = member.id_member

    return render_template(
        "member_form.html", form=form, title="Lid bewerken", member=member
    )
