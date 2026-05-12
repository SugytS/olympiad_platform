import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class Topic(SqlAlchemyBase):
    __tablename__ = 'topics'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    order = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    theory = sqlalchemy.Column(sqlalchemy.Text, nullable=True)

    tasks = orm.relationship("Task", back_populates="topic")