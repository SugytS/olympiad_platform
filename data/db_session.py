import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import os
from contextlib import contextmanager

SqlAlchemyBase = orm.declarative_base()
__factory = None


def global_init(db_file):
    global __factory
    if __factory:
        return
    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    db_dir = os.path.dirname(db_file)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Создана папка для базы данных: {db_dir}")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    print(f"Подключение к базе данных по адресу {conn_str}")
    engine = sa.create_engine(conn_str, echo=False, pool_size=10, max_overflow=20, pool_timeout=30)
    # КЛЮЧЕВОЙ ПАРАМЕТР: не устаревать атрибуты после commit/close
    __factory = orm.sessionmaker(bind=engine, expire_on_commit=False)
    from . import __all_models
    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()


@contextmanager
def session_scope():
    """Контекстный менеджер для автоматического закрытия сессии"""
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()