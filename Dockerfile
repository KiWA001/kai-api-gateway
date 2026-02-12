# Use the official image with Playwright browsers pre-installed
# This saves time and ensures all system dependencies for Chromium are present
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Set working directory
WORKDIR /app

# Improve output logging
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (specifically Chromium)
# The base image has them, but we run this to ensure linking is correct
RUN playwright install chromium

# Copy application code
COPY . .

# Create a non-root user (Hugging Face Spaces requirement)
# UID 1000 is taken by the base image, so we use 1001
RUN useradd -m -u 1001 user

# Ensure the user owns the application directory
# This is CRITICAL for g4f/playwright to write temporary files/caches
RUN chown -R user:user /app

USER user
ENV HOME=/home/user
ENV PATH=$HOME/.local/bin:$PATH

# Expose the port (Hugging Face uses 7860 by default)
EXPOSE 7860

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
