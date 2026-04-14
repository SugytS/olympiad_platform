import docker
import json
import tempfile
import time
import os

def run_code_in_docker(code, tests_json_str, language='python', time_limit=2.0):
    try:
        tests = json.loads(tests_json_str)
    except Exception as e:
        return 'CE', f'Ошибка в формате тестов: {e}'

    client = docker.from_env()
    temp_dir = tempfile.mkdtemp()

    # Выбираем образ и команды в зависимости от языка
    if language == 'python':
        filename = 'solution.py'
        compile_cmd = None
        run_cmd = ['python', f'/code/{filename}']
        image = 'python:3.10-slim'
    elif language == 'cpp':
        filename = 'solution.cpp'
        compile_cmd = ['g++', '-O2', '-std=c++17', '/code/solution.cpp', '-o', '/code/solution']
        run_cmd = ['/code/solution']
        image = 'gcc:12'
    else:
        return 'CE', f'Неподдерживаемый язык: {language}'

    # Сохраняем код в файл
    code_path = os.path.join(temp_dir, filename)
    with open(code_path, 'w', encoding='utf-8') as f:
        f.write(code)

    # Создаём контейнер с ОТКЛЮЧЁННЫМ seccomp
    try:
        container = client.containers.run(
            image,
            command=['sleep', 'infinity'],
            detach=True,
            mem_limit='256m',
            network_disabled=True,
            security_opt=['seccomp=unconfined'],  # <-- ГЛАВНОЕ ИСПРАВЛЕНИЕ
            volumes={temp_dir: {'bind': '/code', 'mode': 'rw'}},
            remove=False
        )
    except Exception as e:
        return 'CE', f'Не удалось создать контейнер: {e}'

    # Компиляция для C++
    if compile_cmd:
        try:
            exec_result = container.exec_run(compile_cmd, workdir='/code')
            if exec_result.exit_code != 0:
                container.remove(force=True)
                err_msg = exec_result.output.decode('utf-8', errors='replace')
                return 'CE', f'Ошибка компиляции:\n{err_msg}'
        except Exception as e:
            container.remove(force=True)
            return 'CE', f'Ошибка компиляции: {e}'

    results = []
    overall_status = 'OK'

    for i, test in enumerate(tests):
        input_data = test.get('input', '')
        expected_output = test.get('output', '').strip()

        # Записываем входные данные в файл (можно и через stdin, но так проще)
        input_file_name = f'input_{i}.txt'
        input_file_path = os.path.join(temp_dir, input_file_name)
        with open(input_file_path, 'w', encoding='utf-8') as f:
            f.write(input_data)

        try:
            start_time = time.time()
            exec_result = container.exec_run(
                ['sh', '-c', f'timeout {time_limit} {" ".join(run_cmd)} < /code/{input_file_name} 2>&1'],
                workdir='/code',
                demux=False
            )
            elapsed = time.time() - start_time

            output = exec_result.output
            if isinstance(output, bytes):
                output_str = output.decode('utf-8', errors='replace')
            else:
                output_str = str(output)

            actual_output = output_str.strip()
            exit_code = exec_result.exit_code

            # timeout возвращает 124 при превышении лимита
            if exit_code == 124:
                overall_status = 'TL'
                results.append(f"Test {i+1}: Time limit exceeded ({elapsed:.3f}s > {time_limit}s)")
                break
            elif exit_code != 0:
                overall_status = 'RE'
                results.append(f"Test {i+1}: Runtime error (exit {exit_code})\n{output_str}")
                break

            if actual_output != expected_output:
                overall_status = 'WA'
                results.append(f"Test {i+1}: WA\nExpected:\n{expected_output}\nGot:\n{actual_output}")
                break
            else:
                results.append(f"Test {i+1}: OK ({elapsed:.3f}s)")

        except Exception as e:
            overall_status = 'CE'
            results.append(f"Test {i+1}: Exception\n{str(e)}")
            break

    # Очистка
    try:
        container.remove(force=True)
    except:
        pass
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)

    details = '\n'.join(results)
    return overall_status, details