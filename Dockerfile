FROM python:3.11-slim

RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

WORKDIR /home/appuser/app

COPY . /home/appuser/app

RUN chown -R appuser:appgroup /home/appuser/

USER appuser
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "bot.py"]
