import docker
import json
import tempfile
import time
import os

def run_code_in_docker(code, tests_json_str, language='python', time_limit=2.0):
    try:
        groups = json.loads(tests_json_str)
    except Exception as e:
        return 'CE', f'Ошибка в формате тестов: {e}', 0

    client = docker.from_env()
    temp_dir = tempfile.mkdtemp()

    if language == 'python':
        filename = 'solution.py'
        compile_cmd = None
        image = 'python:3.10-slim'
        run_cmd_template = f'timeout {time_limit}s python /code/{filename}'
    elif language == 'cpp':
        filename = 'solution.cpp'
        compile_cmd = ['g++', '/code/solution.cpp', '-o', '/code/solution']
        image = 'gcc:12'
        run_cmd_template = f'timeout {time_limit}s /code/solution'
    else:
        return 'CE', 'Неподдерживаемый язык', 0

    code_path = os.path.join(temp_dir, filename)
    with open(code_path, 'w', encoding='utf-8') as f:
        f.write(code)

    try:
        container = client.containers.run(
            image,
            command=['sleep', 'infinity'],
            detach=True,
            mem_limit='256m',
            network_disabled=True,
            volumes={temp_dir: {'bind': '/code', 'mode': 'rw'}},
            remove=False
        )
    except Exception as e:
        return 'CE', f'Не удалось создать контейнер: {e}', 0

    if compile_cmd:
        try:
            compile_cmd_with_timeout = ['sh', '-c', f'timeout 10s {" ".join(compile_cmd)}']
            exec_result = container.exec_run(compile_cmd_with_timeout, workdir='/code')
            if exec_result.exit_code != 0:
                container.remove()
                output = exec_result.output
                err_msg = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
                return 'CE', f'Ошибка компиляции:\n{err_msg}', 0
        except Exception as e:
            container.remove()
            return 'CE', f'Ошибка компиляции: {e}', 0

    # Убеждаемся, что данные в формате подгрупп
    if not groups or not isinstance(groups, list):
        groups = []
    # Если структура плоская (нет 'tests' в первом элементе) – конвертируем
    if len(groups) > 0 and isinstance(groups[0], dict) and 'tests' not in groups[0]:
        # Плоский список тестов → одна подгруппа с score=0 (если баллы отключены)
        groups = [{"name": "Тесты", "score": 0, "tests": groups}]

    results = []
    overall_status = 'OK'
    total_score = 0
    max_possible_score = 0
    groups_results = []

    for group_idx, group in enumerate(groups):
        group_name = group.get('name', f'Подгруппа {group_idx+1}')
        group_score = group.get('score', 0)
        max_possible_score += group_score
        group_tests = group.get('tests', [])
        group_ok = True
        group_test_results = []

        for test_idx, test in enumerate(group_tests):
            input_data = test.get('input', '')
            if 'outputs' in test:
                expected_outputs = test['outputs']
                if isinstance(expected_outputs, str):
                    expected_outputs = [expected_outputs]
            elif 'output' in test:
                expected_outputs = [test['output']]
            else:
                expected_outputs = ['']
            expected_outputs = [s.strip() for s in expected_outputs]

            input_file = os.path.join(temp_dir, f'input_{group_idx}_{test_idx}.txt')
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(input_data)

            cmd = f'{run_cmd_template} < /code/input_{group_idx}_{test_idx}.txt 2>&1'
            try:
                start_time = time.time()
                exec_result = container.exec_run(['sh', '-c', cmd], workdir='/code', demux=False)
                elapsed = time.time() - start_time
                output = exec_result.output
                output_str = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
                actual_output = output_str.strip()
                exit_code = exec_result.exit_code

                if exit_code == 124:
                    overall_status = 'TL'
                    group_ok = False
                    group_test_results.append(f"Тест {test_idx+1}: TL (>{time_limit}s)")
                    continue
                if exit_code != 0:
                    overall_status = 'RE'
                    group_ok = False
                    group_test_results.append(f"Тест {test_idx+1}: RE (exit {exit_code})\n{output_str}")
                    continue
                if actual_output in expected_outputs:
                    group_test_results.append(f"Тест {test_idx+1}: OK ({elapsed:.3f}s)")
                else:
                    overall_status = 'WA'
                    group_ok = False
                    expected_str = '\n'.join(expected_outputs)
                    group_test_results.append(f"Тест {test_idx+1}: WA\nОжидалось одно из:\n{expected_str}\nПолучено:\n{actual_output}")
            except Exception as e:
                overall_status = 'CE'
                group_ok = False
                group_test_results.append(f"Тест {test_idx+1}: Exception\n{str(e)}")

        if group_ok:
            total_score += group_score
            results.append(f"✓ Подгруппа '{group_name}' полностью пройдена → +{group_score} баллов")
            for line in group_test_results:
                results.append(f"  {line}")
        else:
            results.append(f"✗ Подгруппа '{group_name}' не пройдена → 0 баллов (максимум {group_score})")
            for line in group_test_results:
                results.append(f"  {line}")

    container.remove(force=True)
    for f in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, f))
        except Exception:
            pass
    try:
        os.rmdir(temp_dir)
    except Exception:
        pass

    details = '\n'.join(results)
    if total_score == max_possible_score and overall_status in ('OK', 'WA', 'RE', 'TL', 'CE'):
        overall_status = 'OK'
    return overall_status, details, total_score