FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 7860

# Command to run the application using Gunicorn (uses the PORT environment variable)
CMD gunicorn -b 0.0.0.0:${PORT:-10000} app:app
