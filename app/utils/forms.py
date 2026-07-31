"""WTForms form definitions (CSRF-protected via Flask-WTF)."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """Login form rendered on the web sign-in page."""

    username = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=4)])
    remember_me = BooleanField("Se souvenir de moi")
    submit = SubmitField("Se connecter")
