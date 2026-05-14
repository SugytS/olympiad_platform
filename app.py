import os
from collections import defaultdict
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_restful import Api
from werkzeug.utils import secure_filename
import json

from data import db_session
from data.users import User
from data.topics import Topic
from data.tasks import Task
from data.submissions import Submission
from data.groups import Group
from data.group_members import GroupMember
from data.group_tasks import GroupTask
from data.group_submissions import GroupSubmission
from data.initial_data import init_database
from data.init_admin import init_super_admin, ensure_columns
from forms.user import RegisterForm, LoginForm
from forms.task import SubmissionForm
from forms.admin import TopicForm, TaskForm, GroupForm, GroupTaskForm
from api.tasks_api import TaskResource, TaskListResource, SubmissionResource
from utils.auth import admin_required, super_admin_required

from datetime import datetime, timedelta
from forms.user import EditProfileForm
from utils.avatar_helper import save_avatar, delete_avatar

from flask import session as flask_session
from datetime import datetime, timedelta

from datetime import datetime, timedelta
from flask import session as flask_session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
app.config['PERMANENT_SESSION_LIFETIME'] = 365 * 24 * 3600
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========
db_session.global_init("db/olympiad.db")
ensure_columns()          # добавит отсутствующие колонки
init_database()           # начальные темы/задачи
init_super_admin()        # первый пользователь – супер-админ

# ========== НАСТРОЙКА FLASK-LOGIN ==========
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к этой странице'

@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    user = session.get(User, int(user_id))
    if user:
        # принудительно загружаем атрибуты, чтобы избежать DetachedInstanceError
        _ = user.is_admin
        _ = user.is_super_admin
    session.close()
    return user

# ========== REST API ==========
api = Api(app)
api.add_resource(TaskListResource, '/api/v2/tasks')
api.add_resource(TaskResource, '/api/v2/tasks/<int:task_id>')
api.add_resource(SubmissionResource, '/api/v2/submissions')

# ========== ОБРАБОТЧИКИ ОШИБОК ==========
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

# ========== КОНТЕКСТНЫЙ ПРОЦЕССОР ==========
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    with db_session.session_scope() as session:
        topics = session.query(Topic).all()
        return render_template('index.html', title='Главная', topics=topics)

@app.route('/topics')
def topics_list():
    with db_session.session_scope() as session:
        topics = session.query(Topic).order_by(Topic.order).all()
        return render_template('topics.html', title='Темы', topics=topics)

@app.route('/topic/<int:topic_id>')
def tasks_by_topic(topic_id):
    with db_session.session_scope() as session:
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
            for tid in task_ids:
                task_subs = [s for s in subs if s.task_id == tid]
                if any(s.status == 'OK' for s in task_subs):
                    task_status[tid] = 'solved'
                elif task_subs:
                    task_status[tid] = 'attempted'
                else:
                    task_status[tid] = 'none'
        return render_template('tasks.html', topic=topic, tasks=tasks, task_status=task_status)

@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    form = SubmissionForm()
    task = None
    with db_session.session_scope() as session:
        task = session.query(Task).get(task_id)
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('topics_list'))
        previous_submissions = session.query(Submission).filter(
            Submission.task_id == task_id,
            Submission.user_id == current_user.id
        ).order_by(Submission.created_at.desc()).all()
    temp_code = flask_session.pop('temp_code', None)
    if form.validate_on_submit():
        code = form.code.data
        language = form.language.data
        if form.file.data:
            file = form.file.data
            filename = secure_filename(file.filename)
            ext = filename.split('.')[-1].lower()
            if language == 'python' and ext != 'py':
                flash('Для Python нужно загрузить файл .py', 'danger')
                return render_template('task_detail.html', task=task, form=form, previous_submissions=previous_submissions)
            if language == 'cpp' and ext not in ['cpp', 'cc', 'cxx']:
                flash('Для C++ нужно загрузить файл .cpp', 'danger')
                return render_template('task_detail.html', task=task, form=form, previous_submissions=previous_submissions)
            code = file.read().decode('utf-8')
        with db_session.session_scope() as session:
            submission = Submission(
                user_id=current_user.id,
                task_id=task_id,
                code=code,
                language=language,
                status='pending'
            )
            session.add(submission)
            session.commit()
            sub_id = submission.id
        from utils.docker_checker import run_code_in_docker
        status, details = run_code_in_docker(code, task.tests_json, language=language, time_limit=task.time_limit)
        with db_session.session_scope() as session:
            sub = session.query(Submission).get(sub_id)
            sub.status = status
            sub.details = details
            session.commit()
        flash(f'Результат: {status}', 'info')
        if status != 'OK':
            flask_session['temp_code'] = code
        return render_template('submission_result.html', submission=sub)
    if temp_code:
        form.code.data = temp_code
    return render_template('task_detail.html', task=task, form=form, previous_submissions=previous_submissions)

# ========== АУТЕНТИФИКАЦИЯ ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html', form=form)
        with db_session.session_scope() as session:
            if session.query(User).filter(User.email == form.email.data).first():
                flash('Email уже зарегистрирован', 'danger')
                return render_template('register.html', form=form)
            user = User(name=form.name.data, email=form.email.data, about=form.about.data)
            user.set_password(form.password.data)
            session.add(user)
            session.commit()
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with db_session.session_scope() as session:
            user = session.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                flash(f'Добро пожаловать, {user.name}!', 'success')
                return redirect(request.args.get('next') or url_for('index'))
        flash('Неверный email или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    with db_session.session_scope() as session:
        solved_task_ids = {sub.task_id for sub in session.query(Submission).filter(
            Submission.user_id == current_user.id, Submission.status == 'OK').all()}
        total_solved = len(solved_task_ids)
        total_attempts = session.query(Submission).filter(Submission.user_id == current_user.id).count()
        topic_stats = defaultdict(int)
        for tid in solved_task_ids:
            task = session.query(Task).get(tid)
            if task and task.topic:
                topic_stats[task.topic.title] += 1
        # Рейтинг
        all_users = session.query(User).all()
        user_solved = {}
        for u in all_users:
            cnt = session.query(Submission).filter(Submission.user_id == u.id, Submission.status == 'OK').distinct(
                Submission.task_id).count()
            user_solved[u.id] = (u.name, cnt, u.avatar_filename)
        sorted_users = sorted(user_solved.items(), key=lambda x: x[1][1], reverse=True)
        rating = []
        cur_rank = None
        for idx, (uid, (name, cnt, avatar)) in enumerate(sorted_users, 1):
            rating.append({'rank': idx, 'name': name, 'solved': cnt, 'avatar': avatar})
            if uid == current_user.id:
                cur_rank = idx

        return render_template('profile.html',
                               total_solved=total_solved, total_attempts=total_attempts,
                               topics=list(topic_stats.keys()), solved_counts=list(topic_stats.values()),
                               rating=rating[:10], user_rank=cur_rank, user_name=current_user.name,
                               user_about=current_user.about, user_avatar=current_user.avatar_filename)

@app.route('/rating')
def rating():
    with db_session.session_scope() as session:
        all_users = session.query(User).all()
        user_solved = {}
        for u in all_users:
            cnt = session.query(Submission).filter(Submission.user_id == u.id, Submission.status == 'OK').distinct(Submission.task_id).count()
            user_solved[u.id] = (u.name, cnt, u.avatar_filename)
        sorted_users = sorted(user_solved.items(), key=lambda x: x[1][1], reverse=True)
        rating = [{'rank': idx, 'name': name, 'solved': cnt, 'avatar': avatar} for idx, (_, (name, cnt, avatar)) in enumerate(sorted_users, 1)]
        return render_template('rating.html', rating=rating)

# ========== АДМИН-ПАНЕЛЬ ==========
@app.route('/admin')
@admin_required
def admin_dashboard():
    if current_user.is_super_admin:
        with db_session.session_scope() as session:
            return render_template('admin/dashboard.html',
                topics_count=session.query(Topic).count(),
                tasks_count=session.query(Task).count(),
                users_count=session.query(User).count(),
                submissions_count=session.query(Submission).count())
    else:
        # Обычный админ перенаправляется на управление группами
        return redirect(url_for('admin_groups'))

# --- Управление пользователями (только супер-админ) ---
@app.route('/admin/users')
@super_admin_required
def admin_users():
    with db_session.session_scope() as session:
        users = session.query(User).all()
        return render_template('admin/users.html', users=users)

@app.route('/admin/users/toggle_admin/<int:user_id>')
@super_admin_required
def toggle_admin(user_id):
    with db_session.session_scope() as session:
        user = session.query(User).get(user_id)
        if user and user.id != current_user.id:
            user.is_admin = not user.is_admin
            session.commit()
            flash(f'Права админа для {user.name} {"назначены" if user.is_admin else "сняты"}', 'success')
        else:
            flash('Нельзя изменить свои права', 'danger')
    return redirect(url_for('admin_users'))

# --- Управление темами (только супер-админ) ---
@app.route('/admin/topics')
@super_admin_required
def admin_topics():
    with db_session.session_scope() as session:
        topics = session.query(Topic).order_by(Topic.order).all()
        return render_template('admin/topics.html', topics=topics)

@app.route('/admin/topics/add', methods=['GET', 'POST'])
@super_admin_required
def add_topic():
    form = TopicForm()
    if form.validate_on_submit():
        with db_session.session_scope() as session:
            topic = Topic(
                title=form.title.data,
                description=form.description.data,
                theory=form.theory.data,
                order=form.order.data or 0,
                created_by=current_user.id,
                is_system=current_user.is_super_admin
            )
            session.add(topic)
            session.commit()
            flash(f'Тема "{topic.title}" добавлена', 'success')
            return redirect(url_for('admin_topics'))
    return render_template('admin/topic_form.html', form=form, title='Добавить тему')

@app.route('/admin/topics/edit/<int:topic_id>', methods=['GET', 'POST'])
@super_admin_required
def edit_topic(topic_id):
    with db_session.session_scope() as session:
        topic = session.query(Topic).get(topic_id)
        if not topic:
            flash('Тема не найдена', 'danger')
            return redirect(url_for('admin_topics'))
        form = TopicForm(obj=topic)
        if form.validate_on_submit():
            topic.title = form.title.data
            topic.description = form.description.data
            topic.theory = form.theory.data
            topic.order = form.order.data or 0
            session.commit()
            flash('Тема обновлена', 'success')
            return redirect(url_for('admin_topics'))
    return render_template('admin/topic_form.html', form=form, title='Редактировать тему', topic=topic)

@app.route('/admin/topics/delete/<int:topic_id>')
@super_admin_required
def delete_topic(topic_id):
    with db_session.session_scope() as session:
        topic = session.query(Topic).get(topic_id)
        if topic:
            session.query(Task).filter(Task.topic_id == topic_id).delete()
            session.delete(topic)
            session.commit()
            flash('Тема и её задачи удалены', 'success')
    return redirect(url_for('admin_topics'))

# --- Управление задачами (только супер-админ) ---
@app.route('/admin/tasks')
@super_admin_required
def admin_tasks():
    with db_session.session_scope() as session:
        tasks = session.query(Task).all()
        return render_template('admin/tasks.html', tasks=tasks)

@app.route('/admin/tasks/add', methods=['GET', 'POST'])
@super_admin_required
def add_task():
    form = TaskForm()
    with db_session.session_scope() as session:
        form.topic_id.choices = [(t.id, t.title) for t in session.query(Topic).all()]
    if form.validate_on_submit():
        try:
            json.loads(form.tests_json.data)
        except:
            flash('Неверный JSON в тестах', 'danger')
            return render_template('admin/task_form.html', form=form, title='Добавить задачу')
        with db_session.session_scope() as session:
            task = Task(
                title=form.title.data,
                description=form.description.data,
                input_example=form.input_example.data,
                output_example=form.output_example.data,
                tests_json=form.tests_json.data,
                time_limit=form.time_limit.data,
                topic_id=form.topic_id.data,
                created_by=current_user.id,
                is_system=current_user.is_super_admin
            )
            session.add(task)
            session.commit()
            flash('Задача добавлена', 'success')
            return redirect(url_for('admin_tasks'))
    return render_template('admin/task_form.html', form=form, title='Добавить задачу')

@app.route('/admin/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@super_admin_required
def edit_task(task_id):
    with db_session.session_scope() as session:
        task = session.query(Task).get(task_id)
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('admin_tasks'))
        form = TaskForm(obj=task)
        form.topic_id.choices = [(t.id, t.title) for t in session.query(Topic).all()]
        if form.validate_on_submit():
            try:
                json.loads(form.tests_json.data)
            except:
                flash('Неверный JSON', 'danger')
                return render_template('admin/task_form.html', form=form, title='Редактировать задачу', task=task)
            task.title = form.title.data
            task.description = form.description.data
            task.input_example = form.input_example.data
            task.output_example = form.output_example.data
            task.tests_json = form.tests_json.data
            task.time_limit = form.time_limit.data
            task.topic_id = form.topic_id.data
            session.commit()
            flash('Задача обновлена', 'success')
            return redirect(url_for('admin_tasks'))
    return render_template('admin/task_form.html', form=form, title='Редактировать задачу', task=task)

@app.route('/admin/tasks/delete/<int:task_id>')
@super_admin_required
def delete_task(task_id):
    with db_session.session_scope() as session:
        task = session.query(Task).get(task_id)
        if task:
            session.delete(task)
            session.commit()
            flash('Задача удалена', 'success')
    return redirect(url_for('admin_tasks'))

# ========== ГРУППЫ (доступно для всех админов) ==========
@app.route('/admin/groups')
@admin_required
def admin_groups():
    with db_session.session_scope() as session:
        if current_user.is_super_admin:
            groups = session.query(Group).all()
        else:
            groups = session.query(Group).filter(Group.created_by == current_user.id).all()
        return render_template('admin/groups.html', groups=groups)

@app.route('/admin/groups/add', methods=['GET', 'POST'])
@admin_required
def add_group():
    form = GroupForm()
    if form.validate_on_submit():
        with db_session.session_scope() as session:
            group = Group(
                name=form.name.data,
                description=form.description.data,
                created_by=current_user.id
            )
            session.add(group)
            session.commit()
            flash(f'Группа "{group.name}" создана', 'success')
            return redirect(url_for('admin_groups'))
    return render_template('admin/group_form.html', form=form)

@app.route('/admin/groups/<int:group_id>')
@admin_required
def group_detail(group_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group:
            flash('Группа не найдена', 'danger')
            return redirect(url_for('admin_groups'))
        if not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        members = session.query(GroupMember).filter(GroupMember.group_id == group_id).all()
        tasks = session.query(GroupTask).filter(GroupTask.group_id == group_id).all()
        return render_template('admin/group_detail.html', group=group, members=members, tasks=tasks)

@app.route('/admin/groups/<int:group_id>/add_member', methods=['POST'])
@admin_required
def add_group_member(group_id):
    email = request.form.get('email')
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group or not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        user = session.query(User).filter(User.email == email).first()
        if not user:
            flash('Пользователь не найден', 'danger')
        else:
            existing = session.query(GroupMember).filter_by(group_id=group_id, user_id=user.id).first()
            if existing:
                flash('Пользователь уже в группе', 'warning')
            else:
                member = GroupMember(group_id=group_id, user_id=user.id)
                session.add(member)
                session.commit()
                flash(f'{user.name} добавлен в группу', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/admin/groups/<int:group_id>/remove_member/<int:user_id>')
@admin_required
def remove_group_member(group_id, user_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group or not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        member = session.query(GroupMember).filter_by(group_id=group_id, user_id=user_id).first()
        if member:
            session.delete(member)
            session.commit()
            flash('Участник удалён', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/admin/groups/<int:group_id>/add_task', methods=['GET', 'POST'])
@admin_required
def add_group_task(group_id):
    form = GroupTaskForm()
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group or not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        if form.validate_on_submit():
            try:
                json.loads(form.tests_json.data)
            except:
                flash('Неверный JSON', 'danger')
                return render_template('admin/group_task_form.html', form=form, group=group)
            task = GroupTask(
                group_id=group_id,
                title=form.title.data,
                description=form.description.data,
                input_example=form.input_example.data,
                output_example=form.output_example.data,
                tests_json=form.tests_json.data,
                time_limit=form.time_limit.data,
                created_by=current_user.id
            )
            session.add(task)
            session.commit()
            flash('Задача добавлена', 'success')
            return redirect(url_for('group_detail', group_id=group_id))
    return render_template('admin/group_task_form.html', form=form, group=group)

@app.route('/admin/groups/<int:group_id>/edit_task/<int:task_id>', methods=['GET', 'POST'])
@admin_required
def edit_group_task(group_id, task_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        task = session.query(GroupTask).get(task_id)
        if not group or not task or task.group_id != group_id:
            flash('Группа или задача не найдены', 'danger')
            return redirect(url_for('admin_groups'))
        if not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        form = GroupTaskForm()
        if form.validate_on_submit():
            try:
                json.loads(form.tests_json.data)
            except:
                flash('Неверный JSON', 'danger')
                return render_template('admin/group_task_form.html', form=form, group=group, task=task)
            task.title = form.title.data
            task.description = form.description.data
            task.input_example = form.input_example.data
            task.output_example = form.output_example.data
            task.tests_json = form.tests_json.data
            task.time_limit = form.time_limit.data
            session.commit()
            flash('Задача обновлена', 'success')
            return redirect(url_for('group_detail', group_id=group_id))
        if request.method == 'GET':
            form.title.data = task.title
            form.description.data = task.description
            form.input_example.data = task.input_example
            form.output_example.data = task.output_example
            form.tests_json.data = task.tests_json
            form.time_limit.data = task.time_limit
    return render_template('admin/group_task_form.html', form=form, group=group, task=task)

@app.route('/admin/groups/<int:group_id>/delete_task/<int:task_id>')
@admin_required
def delete_group_task(group_id, task_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        task = session.query(GroupTask).get(task_id)
        if not group or not task or task.group_id != group_id:
            flash('Группа или задача не найдены', 'danger')
            return redirect(url_for('admin_groups'))
        if not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        session.delete(task)
        session.commit()
        flash('Задача удалена', 'success')
    return redirect(url_for('group_detail', group_id=group_id))

@app.route('/admin/groups/<int:group_id>/task/<int:task_id>/submissions')
@admin_required
def group_task_submissions(group_id, task_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group:
            flash('Группа не найдена', 'danger')
            return redirect(url_for('admin_groups'))
        if not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        task = session.query(GroupTask).filter(GroupTask.id == task_id, GroupTask.group_id == group_id).first()
        if not task:
            flash('Задача не найдена в этой группе', 'danger')
            return redirect(url_for('group_detail', group_id=group_id))
        submissions = session.query(GroupSubmission).filter(GroupSubmission.task_id == task_id).order_by(GroupSubmission.created_at.desc()).all()
        return render_template('admin/group_submissions.html', group=group, task=task, submissions=submissions)

@app.route('/admin/groups/<int:group_id>/submission/<int:submission_id>/set_status', methods=['POST'])
@admin_required
def set_group_submission_status(group_id, submission_id):
    new_status = request.form.get('status')
    if new_status not in ['OK', 'WA', 'RE', 'CE', 'TL', 'pending']:
        flash('Неверный статус', 'danger')
        return redirect(request.referrer or url_for('admin_groups'))
    with db_session.session_scope() as session:
        submission = session.query(GroupSubmission).get(submission_id)
        if not submission:
            flash('Решение не найдено', 'danger')
            return redirect(url_for('admin_groups'))
        # Проверяем, что задача принадлежит группе, а группа - текущему админу
        task = session.query(GroupTask).get(submission.task_id)
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('admin_groups'))
        group = session.query(Group).get(task.group_id)
        if not (current_user.is_super_admin or group.created_by == current_user.id):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('admin_groups'))
        submission.status = new_status
        session.commit()
        flash(f'Статус решения изменён на {new_status}', 'success')
    return redirect(request.referrer or url_for('group_detail', group_id=group_id))

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ МАРШРУТЫ ДЛЯ ГРУПП ==========
@app.route('/my_groups')
@login_required
def my_groups():
    with db_session.session_scope() as session:
        member_of = session.query(GroupMember).filter(GroupMember.user_id == current_user.id).all()
        groups = [session.query(Group).get(m.group_id) for m in member_of]
        owned_groups = session.query(Group).filter(Group.created_by == current_user.id).all()
        return render_template('my_groups.html', groups=groups, owned_groups=owned_groups)

@app.route('/group/<int:group_id>')
@login_required
def group_tasks_list(group_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group:
            flash('Группа не найдена', 'danger')
            return redirect(url_for('my_groups'))
        is_member = session.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
        if not is_member and group.created_by != current_user.id:
            flash('Вы не состоите в этой группе', 'danger')
            return redirect(url_for('my_groups'))
        tasks = session.query(GroupTask).filter(GroupTask.group_id == group_id).all()
        task_status = {}
        for t in tasks:
            sub = session.query(GroupSubmission).filter_by(task_id=t.id, user_id=current_user.id).order_by(GroupSubmission.created_at.desc()).first()
            if sub and sub.status == 'OK':
                task_status[t.id] = 'solved'
            elif sub:
                task_status[t.id] = 'attempted'
            else:
                task_status[t.id] = 'none'
        return render_template('group_tasks.html', group=group, tasks=tasks, task_status=task_status)


@app.route('/group/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def group_task_detail(task_id):
    form = SubmissionForm()
    task = None
    group = None
    previous_submissions = []
    with db_session.session_scope() as session:
        task = session.query(GroupTask).get(task_id)
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('my_groups'))
        group = session.query(Group).get(task.group_id)
        is_member = session.query(GroupMember).filter_by(group_id=group.id, user_id=current_user.id).first()
        if not is_member and group.created_by != current_user.id:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('my_groups'))
        previous_submissions = session.query(GroupSubmission).filter(
            GroupSubmission.task_id == task_id,
            GroupSubmission.user_id == current_user.id
        ).order_by(GroupSubmission.created_at.desc()).all()

    temp_code = flask_session.pop('temp_code', None)
    if form.validate_on_submit():
        code = form.code.data
        language = form.language.data
        if form.file.data:
            file = form.file.data
            filename = secure_filename(file.filename)
            ext = filename.split('.')[-1].lower()
            if language == 'python' and ext != 'py':
                flash('Для Python нужен .py', 'danger')
                return render_template('group_task_detail.html', task=task, form=form, group=group,
                                       previous_submissions=previous_submissions)
            if language == 'cpp' and ext not in ['cpp', 'cc', 'cxx']:
                flash('Для C++ нужен .cpp', 'danger')
                return render_template('group_task_detail.html', task=task, form=form, group=group,
                                       previous_submissions=previous_submissions)
            code = file.read().decode('utf-8')
        with db_session.session_scope() as session:
            submission = GroupSubmission(
                task_id=task_id,
                user_id=current_user.id,
                code=code,
                language=language,
                status='pending'
            )
            session.add(submission)
            session.commit()
            sub_id = submission.id
        from utils.docker_checker import run_code_in_docker
        status, details = run_code_in_docker(code, task.tests_json, language=language, time_limit=task.time_limit)
        with db_session.session_scope() as session:
            sub = session.query(GroupSubmission).get(sub_id)
            sub.status = status
            sub.details = details
            session.commit()
        flash(f'Результат: {status}', 'info')
        if status != 'OK':
            flask_session['temp_code'] = code
        # Передаём ID задачи и группы в шаблон
        return render_template('group_submission_result.html',
                               submission_id=sub.id,
                               task_id=task.id,
                               group_id=group.id,
                               status=status,
                               language=language,
                               details=details)
    if temp_code:
        form.code.data = temp_code
    return render_template('group_task_detail.html', task=task, form=form, group=group,
                           previous_submissions=previous_submissions)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        with db_session.session_scope() as session:
            user = session.query(User).get(current_user.id)
            user.name = form.name.data
            user.about = form.about.data
            if form.avatar.data:
                # Удаляем старый аватар
                if user.avatar_filename:
                    delete_avatar(user.avatar_filename)
                # Сохраняем новый
                filename = save_avatar(form.avatar.data, user.id)
                user.avatar_filename = filename
            session.commit()
        flash('Профиль обновлён', 'success')
        return redirect(url_for('profile'))
    # Заполняем форму текущими данными
    form.name.data = current_user.name
    form.about.data = current_user.about
    return render_template('edit_profile.html', form=form)

@app.route('/group/<int:group_id>/rating')
@login_required
def group_rating(group_id):
    with db_session.session_scope() as session:
        group = session.query(Group).get(group_id)
        if not group:
            flash('Группа не найдена', 'danger')
            return redirect(url_for('my_groups'))
        is_member = session.query(GroupMember).filter_by(group_id=group_id, user_id=current_user.id).first()
        if not is_member and group.created_by != current_user.id:
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('my_groups'))
        members = session.query(GroupMember).filter(GroupMember.group_id == group_id).all()
        group_rating = []
        for member in members:
            user = member.user
            solved_count = session.query(GroupSubmission).filter(
                GroupSubmission.user_id == user.id,
                GroupSubmission.status == 'OK'
            ).join(GroupTask).filter(GroupTask.group_id == group_id).distinct(GroupSubmission.task_id).count()
            group_rating.append({
                'user': user,
                'solved': solved_count,
                'avatar': user.avatar_filename
            })
        group_rating.sort(key=lambda x: x['solved'], reverse=True)
        for idx, item in enumerate(group_rating, 1):
            item['rank'] = idx
        return render_template('group_rating.html', group=group, rating=group_rating)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)