from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange

class TopicForm(FlaskForm):
    title = StringField('Название темы', validators=[DataRequired()])
    description = TextAreaField('Описание')
    theory = TextAreaField('Теория (HTML/Markdown)')
    order = IntegerField('Порядок', default=0)
    submit = SubmitField('Сохранить')

class TaskForm(FlaskForm):
    title = StringField('Название задачи', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    input_example = TextAreaField('Пример ввода')
    output_example = TextAreaField('Пример вывода')
    tests_json = TextAreaField('Тесты (JSON)', validators=[DataRequired()])
    time_limit = FloatField('Ограничение времени (сек)', default=2.0, validators=[NumberRange(min=0.1)])
    topic_id = SelectField('Тема', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Сохранить')