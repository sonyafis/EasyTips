FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/easy_tips
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "easy_tips.wsgi:application", "--bind", "0.0.0.0:8000"]