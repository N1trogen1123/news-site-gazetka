from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length


class NewsForm(FlaskForm):
    title = StringField('Заголовок', validators=[
        DataRequired(message='Заголовок обязателен'),
        Length(min=3, max=200, message='Заголовок должен быть от 3 до 200 символов')
    ])
    content = TextAreaField('Текст новости', validators=[
        DataRequired(message='Текст новости обязателен'),
        Length(min=10, message='Текст должен содержать минимум 10 символов')
    ])
    category_id = SelectField('Категория', coerce=int, validators=[
        DataRequired(message='Выберите категорию')
    ])
    image = FileField('Изображение', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Только изображения (jpg, png, gif, webp)')
    ])
    submit = SubmitField('Сохранить как черновик')
