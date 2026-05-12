from flask import jsonify, request, make_response
from flask_restful import Resource, reqparse
from flask_login import current_user, login_required
from data import db_session
from data.tasks import Task
from data.submissions import Submission
from utils.docker_checker import run_code_in_docker

parser = reqparse.RequestParser()
parser.add_argument('code', required=True, help='Код обязателен')
parser.add_argument('language', default='python')

class TaskListResource(Resource):
    def get(self):
        with db_session.session_scope() as session:
            tasks = session.query(Task).all()
            return jsonify({'tasks': [{'id': t.id, 'title': t.title, 'topic_id': t.topic_id} for t in tasks]})

class TaskResource(Resource):
    def get(self, task_id):
        with db_session.session_scope() as session:
            task = session.get(Task, task_id)
            if not task:
                return make_response(jsonify({'error': 'Task not found'}), 404)
            return jsonify({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'input_example': task.input_example,
                'output_example': task.output_example,
                'time_limit': task.time_limit
            })

class SubmissionResource(Resource):
    @login_required
    def post(self):
        args = parser.parse_args()
        code = args['code']
        language = args['language']
        task_id = request.json.get('task_id')
        if not task_id:
            return make_response(jsonify({'error': 'task_id required'}), 400)

        with db_session.session_scope() as session:
            task = session.get(Task, task_id)
            if not task:
                return make_response(jsonify({'error': 'Task not found'}), 404)

            submission = Submission(user_id=current_user.id, task_id=task_id,
                                    code=code, language=language, status='pending')
            session.add(submission)
            session.commit()
            submission_id = submission.id

        status, details = run_code_in_docker(code, task.tests_json, language=language, time_limit=task.time_limit)

        with db_session.session_scope() as session:
            submission = session.get(Submission, submission_id)
            submission.status = status
            submission.details = details
            session.commit()

        return jsonify({'submission_id': submission_id, 'status': status, 'details': details})