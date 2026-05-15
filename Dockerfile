FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Устанавливаем Docker CLI (только клиент, не демон)
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

# Открываем порт (Flask по умолчанию 5000)
EXPOSE 5000

# Запускаем приложение через Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
