import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class GroupTask(SqlAlchemyBase):
    __tablename__ = 'group_tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    group_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("groups.id"), nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    input_example = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    output_example = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    tests_json = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    time_limit = sqlalchemy.Column(sqlalchemy.Float, default=2.0)
    created_by = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    max_score = sqlalchemy.Column(sqlalchemy.Integer, default=100)
    scoring_enabled = sqlalchemy.Column(sqlalchemy.Boolean, default=False)  # новый флаг

    group = orm.relationship("Group", back_populates="tasks")
    submissions = orm.relationship("GroupSubmission", back_populates="task", cascade="all, delete-orphan")