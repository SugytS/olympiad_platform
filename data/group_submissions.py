import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class GroupSubmission(SqlAlchemyBase):
    __tablename__ = 'group_submissions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    task_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("group_tasks.id"), nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    code = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    language = sqlalchemy.Column(sqlalchemy.String, default='python')
    status = sqlalchemy.Column(sqlalchemy.String, default='pending')
    details = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    task = orm.relationship("GroupTask", back_populates="submissions")
    user = orm.relationship("User")