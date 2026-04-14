import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class Task(SqlAlchemyBase):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    input_example = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    output_example = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    tests_json = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    time_limit = sqlalchemy.Column(sqlalchemy.Float, default=2.0)
    memory_limit = sqlalchemy.Column(sqlalchemy.Integer, default=128)

    topic_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("topics.id"))
    topic = orm.relationship("Topic", back_populates="tasks")
    submissions = orm.relationship("Submission", back_populates="task")