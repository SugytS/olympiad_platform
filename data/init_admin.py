from data import db_session
from data.users import User
from sqlalchemy import inspect, text


def ensure_columns():
    """Добавляет недостающие колонки в таблицы (для обновления БД)"""
    with db_session.session_scope() as session:
        inspector = inspect(session.bind)

        # users
        cols = [c['name'] for c in inspector.get_columns('users')]
        if 'is_admin' not in cols:
            session.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
            print("Добавлена колонка is_admin в таблицу users")
        if 'is_super_admin' not in cols:
            session.execute(text('ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT 0'))
            print("Добавлена колонка is_super_admin в таблицу users")
        if 'avatar_filename' not in cols:
            session.execute(text('ALTER TABLE users ADD COLUMN avatar_filename VARCHAR(255) DEFAULT NULL'))
            print("Добавлена колонка avatar_filename в таблицу users")

        # topics
        cols_topics = [c['name'] for c in inspector.get_columns('topics')]
        if 'created_by' not in cols_topics:
            session.execute(text('ALTER TABLE topics ADD COLUMN created_by INTEGER REFERENCES users(id)'))
            session.execute(text('ALTER TABLE topics ADD COLUMN is_system BOOLEAN DEFAULT 0'))
            session.execute(text('ALTER TABLE topics ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP'))
            print("Добавлены колонки created_by, is_system, created_at в таблицу topics")

        # tasks
        cols_tasks = [c['name'] for c in inspector.get_columns('tasks')]
        if 'created_by' not in cols_tasks:
            session.execute(text('ALTER TABLE tasks ADD COLUMN created_by INTEGER REFERENCES users(id)'))
            session.execute(text('ALTER TABLE tasks ADD COLUMN is_system BOOLEAN DEFAULT 0'))
            print("Добавлены колонки created_by, is_system в таблицу tasks")

        # group_submissions
        cols_gs = [c['name'] for c in inspector.get_columns('group_submissions')]
        if 'review_comment' not in cols_gs:
            session.execute(text('ALTER TABLE group_submissions ADD COLUMN review_comment TEXT'))
            print("Добавлена колонка review_comment в таблицу group_submissions")
        if 'score' not in cols_gs:
            session.execute(text('ALTER TABLE group_submissions ADD COLUMN score INTEGER DEFAULT NULL'))
            print("Добавлена колонка score в таблицу group_submissions")

        # group_tasks
        cols_gt = [c['name'] for c in inspector.get_columns('group_tasks')]
        if 'max_score' not in cols_gt:
            session.execute(text('ALTER TABLE group_tasks ADD COLUMN max_score INTEGER DEFAULT 100'))
            print("Добавлена колонка max_score в таблицу group_tasks")
        if 'scoring_enabled' not in cols_gt:
            session.execute(text('ALTER TABLE group_tasks ADD COLUMN scoring_enabled BOOLEAN DEFAULT 0'))
            print("Добавлена колонка scoring_enabled в таблицу group_tasks")

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