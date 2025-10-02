# Stage 1: Build dependencies
FROM python:3.9-slim-buster AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: Create a minimal runtime image
FROM python:3.9-slim-buster
WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy your application files (not dependencies)
COPY . /app

# The ENTRYPOINT can be set to just the python executable
ENTRYPOINT ["python"]