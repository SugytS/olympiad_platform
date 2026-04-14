from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, FileField, SelectField
from wtforms.validators import DataRequired

class SubmissionForm(FlaskForm):
    code = TextAreaField('Ваш код', validators=[DataRequired()])
    file = FileField('Или загрузите файл')
    language = SelectField('Язык', choices=[('python', 'Python'), ('cpp', 'C++')], default='python')
    submit = SubmitField('Отправить на проверку')