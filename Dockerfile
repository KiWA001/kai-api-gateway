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
# Explicitly install playwright (removed from requirements.txt for Vercel compatibility)
RUN pip install --no-cache-dir playwright

# Install Playwright browsers (specifically Chromium)
# The base image has them, but we run this to ensure linking is correct
RUN playwright install chromium

# Copy application code
COPY . .

# Remove user creation for debugging permissions
# RUN useradd -m -u 1001 user
# RUN chown -R user:user /app
# USER user
# ENV HOME=/home/user
# ENV PATH=$HOME/.local/bin:$PATH

# Run as root for now to fix 404 crash
ENV HOME=/root
ENV PATH=/root/.local/bin:$PATH

# Expose the port (Hugging Face uses 7860 by default)
EXPOSE 7860

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
