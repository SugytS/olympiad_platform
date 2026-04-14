import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_restful import Api
from werkzeug.utils import secure_filename
from collections import defaultdict
from data import db_session
from data.users import User
from data.topics import Topic
from data.tasks import Task
from data.submissions import Submission
from forms.user import RegisterForm, LoginForm
from forms.task import SubmissionForm
from api.tasks_api import TaskResource, TaskListResource, SubmissionResource
from data.initial_data import init_database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
app.config['PERMANENT_SESSION_LIFETIME'] = 365 * 24 * 3600
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Инициализация базы данных
db_session.global_init("db/olympiad.db")
init_database()

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к этой странице'


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.get(User, user_id)


# Настройка REST API
api = Api(app)
api.add_resource(TaskListResource, '/api/v2/tasks')
api.add_resource(TaskResource, '/api/v2/tasks/<int:task_id>')
api.add_resource(SubmissionResource, '/api/v2/submissions')


# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


# Контекстный процессор для шаблонов
@app.context_processor
def inject_user():
    return dict(current_user=current_user)


# Главная страница
@app.route('/')
def index():
    session = db_session.create_session()
    topics = session.query(Topic).all()
    return render_template('index.html', title='Главная', topics=topics)


# Список всех тем
@app.route('/topics')
def topics_list():
    session = db_session.create_session()
    topics = session.query(Topic).order_by(Topic.order).all()
    return render_template('topics.html', title='Темы', topics=topics)


# Задачи по теме (с цветовой индикацией)
@app.route('/topic/<int:topic_id>')
def tasks_by_topic(topic_id):
    session = db_session.create_session()
    topic = session.query(Topic).get(topic_id)
    if not topic:
        flash('Тема не найдена', 'danger')
        return redirect(url_for('topics_list'))
    tasks = session.query(Task).filter(Task.topic_id == topic_id).all()

    task_status = {}
    if current_user.is_authenticated:
        task_ids = [t.id for t in tasks]
        subs = session.query(Submission).filter(
            Submission.user_id == current_user.id,
            Submission.task_id.in_(task_ids)
        ).all()
        for task_id in task_ids:
            task_subs = [s for s in subs if s.task_id == task_id]
            if any(s.status == 'OK' for s in task_subs):
                task_status[task_id] = 'solved'
            elif task_subs:
                task_status[task_id] = 'attempted'
            else:
                task_status[task_id] = 'none'
    else:
        task_status = {}

    return render_template('tasks.html',
                           title=topic.title,
                           topic=topic,
                           tasks=tasks,
                           task_status=task_status)


# Детали задачи и отправка решения
@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    form = SubmissionForm()
    session = db_session.create_session()
    task = session.query(Task).get(task_id)
    if not task:
        flash('Задача не найдена', 'danger')
        return redirect(url_for('topics_list'))

    if form.validate_on_submit():
        code = form.code.data
        language = form.language.data

        if form.file.data:
            file = form.file.data
            filename = secure_filename(file.filename)
            ext = filename.split('.')[-1].lower()
            if language == 'python' and ext != 'py':
                flash('Для Python нужно загрузить файл с расширением .py', 'danger')
                return render_template('task_detail.html', title=task.title, task=task, form=form)
            if language == 'cpp' and ext not in ['cpp', 'cc', 'cxx']:
                flash('Для C++ нужно загрузить файл с расширением .cpp', 'danger')
                return render_template('task_detail.html', title=task.title, task=task, form=form)
            code = file.read().decode('utf-8')

        submission = Submission(
            user_id=current_user.id,
            task_id=task_id,
            code=code,
            language=language,
            status='pending'
        )
        session.add(submission)
        session.commit()

        from utils.docker_checker import run_code_in_docker
        status, details = run_code_in_docker(
            code, task.tests_json,
            language=language,
            time_limit=task.time_limit
        )

        submission.status = status
        submission.details = details
        session.commit()

        flash(f'Решение проверено. Результат: {status}', 'info')
        return render_template('submission_result.html', submission=submission)

    return render_template('task_detail.html', title=task.title, task=task, form=form)


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html', title='Регистрация', form=form)
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html', title='Регистрация', form=form)
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)


# Логин
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Добро пожаловать, {user.name}!', 'success')
            return redirect(next_page or url_for('index'))
        flash('Неверный email или пароль', 'danger')
    return render_template('login.html', title='Авторизация', form=form)


# Логаут
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Профиль пользователя
@app.route('/profile')
@login_required
def profile():
    session = db_session.create_session()
    successful_submissions = session.query(Submission).filter(
        Submission.user_id == current_user.id,
        Submission.status == 'OK'
    ).all()

    solved_task_ids = set()
    for sub in successful_submissions:
        solved_task_ids.add(sub.task_id)

    total_solved = len(solved_task_ids)
    total_attempts = session.query(Submission).filter(
        Submission.user_id == current_user.id
    ).count()

    topic_stats = defaultdict(int)
    for task_id in solved_task_ids:
        task = session.query(Task).get(task_id)
        if task and task.topic:
            topic_stats[task.topic.title] += 1

    topics_list = list(topic_stats.keys())
    solved_counts = list(topic_stats.values())

    user_solved_counts = {}
    all_users = session.query(User).all()
    for user in all_users:
        count = session.query(Submission).filter(
            Submission.user_id == user.id,
            Submission.status == 'OK'
        ).distinct(Submission.task_id).count()
        user_solved_counts[user.id] = (user.name, count)

    sorted_users = sorted(user_solved_counts.items(), key=lambda x: x[1][1], reverse=True)
    rating = []
    current_user_rank = None
    for idx, (uid, (name, cnt)) in enumerate(sorted_users, 1):
        rating.append({'rank': idx, 'name': name, 'solved': cnt})
        if uid == current_user.id:
            current_user_rank = idx

    top_rating = rating[:10]

    return render_template('profile.html',
                           title='Мой профиль',
                           total_solved=total_solved,
                           total_attempts=total_attempts,
                           topics=topics_list,
                           solved_counts=solved_counts,
                           rating=top_rating,
                           user_rank=current_user_rank,
                           user_name=current_user.name)


# Рейтинг
@app.route('/rating')
def rating():
    session = db_session.create_session()
    user_solved_counts = {}
    all_users = session.query(User).all()
    for user in all_users:
        count = session.query(Submission).filter(
            Submission.user_id == user.id,
            Submission.status == 'OK'
        ).distinct(Submission.task_id).count()
        user_solved_counts[user.id] = (user.name, count)

    sorted_users = sorted(user_solved_counts.items(), key=lambda x: x[1][1], reverse=True)
    rating = []
    for idx, (uid, (name, cnt)) in enumerate(sorted_users, 1):
        rating.append({'rank': idx, 'name': name, 'solved': cnt})

    return render_template('rating.html', title='Рейтинг пользователей', rating=rating)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)