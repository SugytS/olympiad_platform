import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class Submission(SqlAlchemyBase):
    __tablename__ = 'submissions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    code = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    language = sqlalchemy.Column(sqlalchemy.String, default='python')
    status = sqlalchemy.Column(sqlalchemy.String, default='pending')
    details = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    execution_time = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    used_memory = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    task_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("tasks.id"))

    user = orm.relationship("User", back_populates="submissions")
    task = orm.relationship("Task", back_populates="submissions")