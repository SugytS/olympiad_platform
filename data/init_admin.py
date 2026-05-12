from data import db_session
from data.users import User
from sqlalchemy import inspect, text

def ensure_columns():
    """Добавляет недостающие колонки в таблицу users (если нужно)"""
    with db_session.session_scope() as session:
        inspector = inspect(session.bind)
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'is_admin' not in columns:
            session.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
            print("Добавлена колонка is_admin")
        if 'is_super_admin' not in columns:
            session.execute(text('ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT 0'))
            print("Добавлена колонка is_super_admin")
        session.commit()

def init_super_admin():
    ensure_columns()  # сначала убеждаемся, что колонки есть
    with db_session.session_scope() as session:
        users = session.query(User).all()
        if users and not session.query(User).filter(User.is_super_admin == True).first():
            first_user = users[0]
            first_user.is_super_admin = True
            first_user.is_admin = True
            session.commit()
            print(f"Пользователь {first_user.name} назначен супер-администратором")