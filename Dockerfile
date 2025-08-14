FROM python:3.13

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x app.py

RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*

RUN dos2unix app.py

RUN mkdir -p /uploads /downloads

EXPOSE 5000

CMD ["python", "app.py"]
