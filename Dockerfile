FROM python:3.12-slim

WORKDIR /app

# Install pipenv and production dependencies
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy

# Copy application code
COPY service/ ./service/
COPY wsgi.py .flaskenv ./

# Set environment variables
ENV PORT=8080
EXPOSE 8080

# Run the service
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--log-level=info", "wsgi:app"]
