
FROM python:3.10-slim

WORKDIR /app
    
COPY . .
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# streamlit default port
EXPOSE 8501 

ENTRYPOINT ["streamlit", "run", "HOME.py", "--server.port=8501", "--server.address=0.0.0.0"]
