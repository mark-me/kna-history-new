from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    MultipleFileField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional


class QuickActivityForm(FlaskForm):
    title = StringField("Titel", validators=[DataRequired()])
    year = StringField("Jaar", validators=[DataRequired()])
    type = SelectField(
        "Type",
        choices=[
            ("Uitvoering", "Uitvoering"),
            ("Event", "Evenement"),
            ("Rehearsal", "Repetitie"),
            ("Meeting", "Vergadering"),
        ],
        validators=[DataRequired()],
    )
    start_date = DateField("Startdatum", validators=[Optional()])
    end_date = DateField("Einddatum", validators=[Optional()])
    folder = StringField("Mapnaam (optioneel)")
    description = TextAreaField("Beschrijving")
    submit = SubmitField("Activiteit aanmaken")


class QuickMemberForm(FlaskForm):
    first_name = StringField("Voornaam", validators=[DataRequired()])
    last_name = StringField("Achternaam", validators=[DataRequired()])
    id_lid = StringField("ID (optioneel – auto indien leeg)")
    submit = SubmitField("Lid toevoegen")


class UploadAndAssignForm(FlaskForm):
    files = MultipleFileField("Scans / foto's", validators=[DataRequired()])
    activity_id = SelectField(
        "Toewijzen aan activiteit", coerce=str, validators=[DataRequired()]
    )
    submit = SubmitField("Uploaden en toewijzen")