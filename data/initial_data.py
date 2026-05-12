import json
from data import db_session
from data.topics import Topic
from data.tasks import Task

def init_database():
    session = db_session.create_session()
    if session.query(Topic).first():
        print("База данных уже содержит темы. Инициализация пропущена.")
        session.close()
        return

    topics_data = [
        {
            "title": "Введение в алгоритмы",
            "description": "Базовые понятия алгоритмизации.",
            "order": 1,
            "theory": "<h3>Что такое алгоритм?</h3><p>Алгоритм — это конечная последовательность шагов.</p>"
        },
        {"title": "Массивы и строки", "description": "Работа с массивами и строками.", "order": 2, "theory": ""},
        {"title": "Сортировка и поиск", "description": "Алгоритмы сортировки и поиска.", "order": 3, "theory": ""},
        {"title": "Рекурсия и ДП", "description": "Рекурсивные алгоритмы, ДП.", "order": 4, "theory": ""},
        {"title": "Структуры данных", "description": "Стек, очередь, деревья.", "order": 5, "theory": ""}
    ]

    topics = []
    for td in topics_data:
        topic = Topic(title=td["title"], description=td["description"],
                      order=td["order"], theory=td["theory"])
        session.add(topic)
        topics.append(topic)
    session.commit()

    tasks_data = {
        topics[0].id: [
            {
                "title": "Сумма двух чисел",
                "description": "Вычислите сумму двух целых чисел.",
                "input_example": "2\n3",
                "output_example": "5",
                "tests_json": json.dumps([
                    {"input": "1\n1", "output": "2"},
                    {"input": "0\n0", "output": "0"},
                    {"input": "-5\n10", "output": "5"}
                ]),
                "time_limit": 1.0
            }
        ]
    }

    for topic_id, tasks in tasks_data.items():
        for t in tasks:
            task = Task(
                title=t["title"],
                description=t["description"],
                input_example=t.get("input_example", ""),
                output_example=t.get("output_example", ""),
                tests_json=t["tests_json"],
                time_limit=t["time_limit"],
                topic_id=topic_id
            )
            session.add(task)
    session.commit()
    session.close()
    print("База данных инициализирована темами и задачами.")