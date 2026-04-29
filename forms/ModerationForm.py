from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import Length

class ModerationForm(FlaskForm):
    comment = TextAreaField('Комментарий', validators=[Length(max=500)])
    submit_approve = SubmitField('Одобрить')
    submit_reject = SubmitField('Отклонить')
