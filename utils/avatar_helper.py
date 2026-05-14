import os
from PIL import Image
from flask import current_app
import uuid


def save_avatar(avatar_file, user_id):
    """Сохраняет аватар пользователя и возвращает имя файла"""
    if not avatar_file:
        return None

    # Создаём папку, если её нет
    avatars_dir = os.path.join(current_app.root_path, 'static', 'avatars')
    os.makedirs(avatars_dir, exist_ok=True)

    # Генерируем уникальное имя файла
    ext = os.path.splitext(avatar_file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
        ext = '.png'  # fallback

    filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(avatars_dir, filename)

    try:
        # Оптимизируем изображение
        img = Image.open(avatar_file)
        img.thumbnail((200, 200))  # Изменяем размер до 200x200 (сохраняя пропорции)

        # Сохраняем с оптимизацией
        if ext.lower() == '.jpg' or ext.lower() == '.jpeg':
            img.save(filepath, optimize=True, quality=85)
        else:
            img.save(filepath, optimize=True)

        return filename
    except Exception as e:
        print(f"Ошибка при сохранении аватара: {e}")
        return None


def delete_avatar(filename):
    """Удаляет файл аватара"""
    if not filename:
        return

    filepath = os.path.join(current_app.root_path, 'static', 'avatars', filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Ошибка при удалении аватара: {e}")