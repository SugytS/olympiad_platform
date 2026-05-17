# migrate_to_group_score.py
import json
from data import db_session
from data.group_tasks import GroupTask

def migrate():
    db_session.global_init("db/olympiad.db")
    with db_session.session_scope() as session:
        tasks = session.query(GroupTask).filter(GroupTask.scoring_enabled == True).all()
        for task in tasks:
            try:
                data = json.loads(task.tests_json)
                # Если уже формат подгрупп (с ключом 'tests') – пропускаем
                if data and isinstance(data, list) and len(data) > 0 and 'tests' in data[0]:
                    # Но возможно, там есть weight, которые нужно убрать
                    need_save = False
                    for group in data:
                        if 'score' not in group:
                            # Вычисляем score как сумму весов тестов
                            total = sum(t.get('weight', 1) for t in group.get('tests', []))
                            group['score'] = total
                            need_save = True
                        for test in group.get('tests', []):
                            if 'weight' in test:
                                del test['weight']
                                need_save = True
                    if need_save:
                        task.tests_json = json.dumps(data, ensure_ascii=False)
                        print(f"Задача '{task.title}': удалены веса тестов, установлен score для подгрупп")
                    continue

                # Старый формат: плоский список тестов с весами
                total_weight = 0
                for t in data:
                    total_weight += t.get('weight', 1)
                    if 'weight' in t:
                        del t['weight']
                new_data = [{
                    "name": "Основные тесты",
                    "score": total_weight,
                    "tests": data
                }]
                task.tests_json = json.dumps(new_data, ensure_ascii=False)
                task.max_score = total_weight
                print(f"Задача '{task.title}': сконвертирована в одну подгруппу с баллом {total_weight}")
            except Exception as e:
                print(f"Ошибка в задаче {task.id}: {e}")
        session.commit()
        print("Миграция завершена")

if __name__ == '__main__':
    migrate()