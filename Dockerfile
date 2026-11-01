FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install \
    --no-cache-dir \
    --index-url https://pypi.org/simple/ \
    --timeout 120 \
    --retries 5 \
    -r requirements.txt

COPY app.py .
COPY test_app.py .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
