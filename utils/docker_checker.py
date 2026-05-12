import docker
import json
import tempfile
import time
import os

def run_code_in_docker(code, tests_json_str, language='python', time_limit=2.0):
    try:
        tests = json.loads(tests_json_str)
    except:
        return 'CE', 'Ошибка в формате тестов'

    client = docker.from_env()
    temp_dir = tempfile.mkdtemp()

    if language == 'python':
        filename = 'solution.py'
        compile_cmd = None
        run_cmd = ['python', f'/code/{filename}']
        image = 'python:3.10-slim'
    elif language == 'cpp':
        filename = 'solution.cpp'
        compile_cmd = ['g++', '/code/solution.cpp', '-o', '/code/solution']
        run_cmd = ['/code/solution']
        image = 'gcc:12'
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

    if compile_cmd:
        try:
            exec_result = container.exec_run(compile_cmd, workdir='/code')
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

        try:
            start_time = time.time()
            exec_result = container.exec_run(
                ['sh', '-c', f'{run_cmd[0]} < /code/input_{i}.txt 2>&1'],
                workdir='/code',
                demux=False
            )
            elapsed = time.time() - start_time

            output = exec_result.output
            output_str = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else str(output)
            actual_output = output_str.strip()
            exit_code = exec_result.exit_code

            if exit_code != 0:
                overall_status = 'RE'
                results.append(f"Test {i+1}: Runtime error (exit {exit_code})\n{output_str}")
                continue

            if actual_output != expected_output:
                overall_status = 'WA'
                results.append(f"Test {i+1}: WA\nExpected:\n{expected_output}\nGot:\n{actual_output}")
            else:
                results.append(f"Test {i+1}: OK ({elapsed:.3f}s)")

            if elapsed > time_limit:
                overall_status = 'TL'
                results.append(f"Test {i+1}: Time limit exceeded ({elapsed:.3f}s > {time_limit}s)")
        except Exception as e:
            overall_status = 'CE'
            results.append(f"Test {i+1}: Exception\n{str(e)}")

    container.remove(force=True)
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)

    details = '\n'.join(results)
    return overall_status, details