FROM python:3.6

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /uploads /downloads

EXPOSE 5000

CMD ["python", "app.py"]
