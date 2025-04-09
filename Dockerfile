# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file (if needed, or add directly to install)
COPY requirements.txt ./

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY mark6.py ./
COPY monitored_ips.json ./

# Expose the application port
EXPOSE 5000

# Define environment variables
ENV ADMIN_PASSWORD='pass'

# Command to run the application
CMD ["python", "mark6.py"]
