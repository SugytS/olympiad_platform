import datetime
import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase

class GroupMember(SqlAlchemyBase):
    __tablename__ = 'group_members'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    group_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("groups.id"), nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    joined_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    group = orm.relationship("Group", back_populates="members")
    user = orm.relationship("User")