import docker
import json
import tempfile
import time
import os
import requests.exceptions

def run_code_in_docker(code, tests_json_str, language='python', time_limit=2.0):
    try:
        tests = json.loads(tests_json_str)
    except Exception as e:
        return 'CE', f'Ошибка в формате тестов: {e}'

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
        return 'CE', 'Неподдерживаемый язык'

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
        return 'CE', f'Не удалось создать контейнер: {e}'

    # Компиляция для C++ с таймаутом 10 секунд
    if compile_cmd:
        try:
            # Используем timeout и для компиляции
            compile_cmd_with_timeout = ['sh', '-c', f'timeout 10s {" ".join(compile_cmd)}']
            exec_result = container.exec_run(compile_cmd_with_timeout, workdir='/code')
            if exec_result.exit_code != 0:
                container.remove()
                output = exec_result.output
                err_msg = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
                return 'CE', f'Ошибка компиляции:\n{err_msg}'
        except Exception as e:
            container.remove()
            return 'CE', f'Ошибка компиляции: {e}'

    results = []
    overall_status = 'OK'

    for i, test in enumerate(tests):
        input_data = test.get('input', '')
        expected_output = test.get('output', '').strip()
        input_file = os.path.join(temp_dir, f'input_{i}.txt')
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(input_data)

        # Команда с перенаправлением ввода и timeout
        cmd = f'{run_cmd_template} < /code/input_{i}.txt 2>&1'
        try:
            start_time = time.time()
            exec_result = container.exec_run(
                ['sh', '-c', cmd],
                workdir='/code',
                demux=False
            )
            elapsed = time.time() - start_time

            output = exec_result.output
            output_str = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
            actual_output = output_str.strip()
            exit_code = exec_result.exit_code

            # Если утилита timeout убила процесс, exit_code == 124
            if exit_code == 124:
                overall_status = 'TL'
                results.append(f"Test {i+1}: Time limit exceeded (>{time_limit}s)")
                continue

            if exit_code != 0:
                overall_status = 'RE'
                results.append(f"Test {i+1}: Runtime error (exit {exit_code})\n{output_str}")
                continue

            if actual_output != expected_output:
                overall_status = 'WA'
                results.append(f"Test {i+1}: WA\nExpected:\n{expected_output}\nGot:\n{actual_output}")
            else:
                results.append(f"Test {i+1}: OK ({elapsed:.3f}s)")

        except Exception as e:
            overall_status = 'CE'
            results.append(f"Test {i+1}: Exception\n{str(e)}")

    container.remove(force=True)
    # Удаляем временную папку
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
    return overall_status, details