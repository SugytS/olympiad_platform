import json
from data import db_session
from data.topics import Topic
from data.tasks import Task


def init_database():
    """Заполняет базу данных начальными темами и задачами, если они ещё не добавлены."""
    session = db_session.create_session()

    # Проверяем, есть ли уже темы
    if session.query(Topic).first():
        print("База данных уже содержит темы. Инициализация пропущена.")
        return

    # Создаём темы
    topics_data = [
        {
            "title": "Введение в алгоритмы",
            "description": "Базовые понятия алгоритмизации, линейные алгоритмы, условные операторы, циклы.",
            "order": 1,
            "theory": """NIGERSSSSSSSSSSSSSSSS"""
        },
        {
            "title": "Массивы и строки",
            "description": "Работа с одномерными и двумерными массивами, строковые алгоритмы.",
            "order": 2
        },
        {
            "title": "Сортировка и поиск",
            "description": "Алгоритмы сортировки (пузырьком, быстрая, слиянием), бинарный поиск.",
            "order": 3
        },
        {
            "title": "Рекурсия и динамическое программирование",
            "description": "Рекурсивные алгоритмы, основы ДП: задача о кузнечике, рюкзак, НВП.",
            "order": 4
        },
        {
            "title": "Структуры данных",
            "description": "Стек, очередь, дек, связные списки, деревья, хеш-таблицы.",
            "order": 5
        }
    ]

    topics = []
    for t_data in topics_data:
        topic = Topic(
            title=t_data["title"],
            description=t_data["description"],
            order=t_data["order"]
        )
        session.add(topic)
        topics.append(topic)
    session.commit()

    # Задачи для каждой темы
    tasks_data = {
        topics[0].id: [  # Введение в алгоритмы
            {
                "title": "Сумма двух чисел",
                "description": "На вход программе подаются два целых числа, каждое на отдельной строке. Выведите их сумму.",
                "input_example": "2\n3",
                "output_example": "5",
                "tests_json": json.dumps([
                    {"input": "1\n1", "output": "2"},
                    {"input": "0\n0", "output": "0"},
                    {"input": "-5\n10", "output": "5"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Четное или нечетное?",
                "description": "Дано целое число. Определите, является ли оно четным. Выведите 'YES' или 'NO'.",
                "input_example": "4",
                "output_example": "YES",
                "tests_json": json.dumps([
                    {"input": "4", "output": "YES"},
                    {"input": "7", "output": "NO"},
                    {"input": "0", "output": "YES"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Таблица умножения",
                "description": "Дано число n (1 ≤ n ≤ 10). Выведите таблицу умножения для числа n в формате: n * i = res, где i от 1 до 10.",
                "input_example": "5",
                "output_example": "5 * 1 = 5\n5 * 2 = 10\n5 * 3 = 15\n5 * 4 = 20\n5 * 5 = 25\n5 * 6 = 30\n5 * 7 = 35\n5 * 8 = 40\n5 * 9 = 45\n5 * 10 = 50",
                "tests_json": json.dumps([
                    {"input": "2",
                     "output": "2 * 1 = 2\n2 * 2 = 4\n2 * 3 = 6\n2 * 4 = 8\n2 * 5 = 10\n2 * 6 = 12\n2 * 7 = 14\n2 * 8 = 16\n2 * 9 = 18\n2 * 10 = 20"},
                    {"input": "3",
                     "output": "3 * 1 = 3\n3 * 2 = 6\n3 * 3 = 9\n3 * 4 = 12\n3 * 5 = 15\n3 * 6 = 18\n3 * 7 = 21\n3 * 8 = 24\n3 * 9 = 27\n3 * 10 = 30"}
                ]),
                "time_limit": 1.0
            }
        ],
        topics[1].id: [  # Массивы и строки
            {
                "title": "Максимум в массиве",
                "description": "Дано натуральное число N, затем N целых чисел. Найдите максимальное число среди них.",
                "input_example": "5\n1 2 3 4 5",
                "output_example": "5",
                "tests_json": json.dumps([
                    {"input": "3\n10 20 30", "output": "30"},
                    {"input": "1\n-100", "output": "-100"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Обратный порядок",
                "description": "Дан массив целых чисел. Выведите его элементы в обратном порядке.",
                "input_example": "4\n1 2 3 4",
                "output_example": "4 3 2 1",
                "tests_json": json.dumps([
                    {"input": "3\n5 6 7", "output": "7 6 5"},
                    {"input": "1\n42", "output": "42"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Палиндром",
                "description": "Дана строка. Определите, является ли она палиндромом. Выведите 'YES' или 'NO'.",
                "input_example": "abba",
                "output_example": "YES",
                "tests_json": json.dumps([
                    {"input": "abba", "output": "YES"},
                    {"input": "abc", "output": "NO"},
                    {"input": "a", "output": "YES"}
                ]),
                "time_limit": 1.0
            }
        ],
        topics[2].id: [  # Сортировка и поиск
            {
                "title": "Сортировка пузырьком",
                "description": "Дан массив целых чисел. Отсортируйте его по возрастанию и выведите.",
                "input_example": "5\n3 1 4 1 5",
                "output_example": "1 1 3 4 5",
                "tests_json": json.dumps([
                    {"input": "4\n4 3 2 1", "output": "1 2 3 4"},
                    {"input": "3\n1 2 3", "output": "1 2 3"}
                ]),
                "time_limit": 2.0
            },
            {
                "title": "Бинарный поиск",
                "description": "Дан отсортированный массив и число x. Найдите индекс первого вхождения x (нумерация с 1). Если x не найден, выведите 0.",
                "input_example": "6\n1 3 5 7 9 11\n5",
                "output_example": "3",
                "tests_json": json.dumps([
                    {"input": "5\n10 20 30 40 50\n30", "output": "3"},
                    {"input": "4\n1 2 3 4\n5", "output": "0"}
                ]),
                "time_limit": 1.0
            }
        ],
        topics[3].id: [  # Рекурсия и ДП
            {
                "title": "Числа Фибоначчи",
                "description": "Дано число n (n ≥ 1). Выведите n-е число Фибоначчи (F1=1, F2=1).",
                "input_example": "6",
                "output_example": "8",
                "tests_json": json.dumps([
                    {"input": "1", "output": "1"},
                    {"input": "2", "output": "1"},
                    {"input": "7", "output": "13"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Кузнечик",
                "description": "Кузнечик стоит на позиции 1 и хочет попасть в позицию N. Прыжки +1 или +2. Сколькими способами?",
                "input_example": "5",
                "output_example": "5",
                "tests_json": json.dumps([
                    {"input": "3", "output": "2"},
                    {"input": "4", "output": "3"},
                    {"input": "6", "output": "8"}
                ]),
                "time_limit": 1.0
            }
        ],
        topics[4].id: [  # Структуры данных
            {
                "title": "Стек",
                "description": "Реализуйте стек. Команды: 'push n', 'pop'. При pop из пустого стека выводить 'error'.",
                "input_example": "5\npush 1\npush 2\npop\npop\npop",
                "output_example": "2\n1\nerror",
                "tests_json": json.dumps([
                    {"input": "3\npush 10\npop\npop", "output": "10\nerror"},
                    {"input": "4\npush 5\npush 7\npop\npop", "output": "7\n5"}
                ]),
                "time_limit": 1.0
            },
            {
                "title": "Очередь",
                "description": "Реализуйте очередь. Команды: 'push n', 'pop'.",
                "input_example": "4\npush 1\npush 2\npop\npop",
                "output_example": "1\n2",
                "tests_json": json.dumps([
                    {"input": "3\npush 100\npop\npop", "output": "100\nerror"}
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
                time_limit=t.get("time_limit", 2.0),
                topic_id=topic_id
            )
            session.add(task)
    session.commit()
    print("База данных успешно инициализирована темами и задачами!")