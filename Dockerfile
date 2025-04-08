# Use official Python 3.9 slim image
FROM python:3.9-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . /app

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run Streamlit on port 8080 and listen on 0.0.0.0
CMD ["streamlit", "run", "main.py", \
     "--server.port=8080", "--server.address=0.0.0.0", \
     "--browser.gatherUsageStats=false"]
