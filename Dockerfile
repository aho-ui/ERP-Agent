FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "mkdir -p dbdata && python manage.py migrate --no-input && python manage.py create_default_users && uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --reload"]
