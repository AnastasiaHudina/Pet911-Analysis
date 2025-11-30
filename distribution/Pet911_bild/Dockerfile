FROM ubuntu:22.04

# Устанавливаем переменные окружения для избежания проблем с интерактивной установкой
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Обновляем список пакетов и устанавливаем Python и pip
RUN apt-get update && \
apt-get install -y python3 python3-pip && \
rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip3 install -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Запускаем приложение
CMD ["sh", "-c", "python3 main.py && sleep infinity"]
