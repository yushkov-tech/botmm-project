FROM python:3.11-slim AS builder

WORKDIR /app

# Устанавливаем системные зависимости только для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.11-slim

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /root/.local

# Копируем исходный код
COPY . .

# Убедимся, что python будет использовать локальные пакеты
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages:$PYTHONPATH

# Здоровье-чек для Kubernetes
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; import os; \
    try: \
        bot_name = os.getenv('BOT_NAME', 'unknown'); \
        print(f'Health check for {bot_name}'); \
    except: \
        exit(1)"

# Команда запуска
CMD ["python", "main.py"]