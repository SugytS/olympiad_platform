import sys
from data import db_session
from data.users import User

def add_super_admin_by_email(email):
    db_session.global_init("db/olympiad.db")
    session = db_session.create_session()
    user = session.query(User).filter(User.email == email).first()
    if not user:
        print(f"Пользователь с email {email} не найден.")
        return False
    if user.is_super_admin:
        print(f"Пользователь {user.name} ({email}) уже является супер-админом.")
        return True
    user.is_super_admin = True
    user.is_admin = True
    session.commit()
    print(f"Пользователь {user.name} ({email}) назначен супер-админом.")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python add_super_admin.py email@example.com")
        sys.exit(1)
    email = sys.argv[1]
    add_super_admin_by_email(email)