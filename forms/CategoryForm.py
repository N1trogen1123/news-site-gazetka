from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class CategoryForm(FlaskForm):
    name = StringField('Название категории', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Добавить')
