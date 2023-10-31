FROM python:3.11
COPY bot.py .
COPY yaHelper.py .
COPY stringHelper.py .
COPY requirements.txt .
COPY credentials.py .
RUN pip install -r requirements.txt
CMD python bot.py