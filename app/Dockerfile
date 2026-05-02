FROM python:3.12-alpine

# Install uv properly
RUN pip install uv

WORKDIR /app

COPY pyproject.toml . uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
