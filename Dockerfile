# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV NLTK_DATA=/app/nltk_data
# Ensure HuggingFace/Sentence-Transformers caches persist in image and are readable by non-root
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers
ENV EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Enable search functionality with partial name patterns
ENV ENABLE_SEARCH=true
ENV ENABLE_EMBEDDINGS=true

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock README.md ./

# Copy application code first
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config.py ./

# Make entrypoint executable
RUN chmod +x /app/scripts/docker-entrypoint.sh
# Do not bake runtime secrets into the image.
# Provide env.production as documentation only (do not auto-load as .env in container)

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Fix httpx dependency conflict for elasticsearch BEFORE installing other dependencies
RUN pip install --no-cache-dir httpx==0.25.2 elasticsearch==8.10.0

# Install additional required dependencies for FastAPI and Elasticsearch
RUN pip install --no-cache-dir python-multipart aiohttp

# Install dependencies
RUN poetry install --only=main --no-interaction --no-ansi

# Ensure torch CPU is present for sentence-transformers (some slim images miss it)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

# Install SpaCy models directly
RUN pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
RUN pip install https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.8.0/ru_core_news_sm-3.8.0-py3-none-any.whl
RUN pip install https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl

# Install NLTK and download data (after dependencies are installed)
RUN pip install --no-cache-dir nltk
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Create logs directory and set permissions
RUN mkdir -p /app/logs "$HF_HOME" "$SENTENCE_TRANSFORMERS_HOME" && \
    chown -R app:app /app
USER app

# Pre-fetch embedding model into cache to work offline at runtime (skip for now to speed up build)
# RUN python -c "import os; from sentence_transformers import SentenceTransformer; model_name = os.getenv('EMBEDDING_MODEL','sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); print(f'Preloading embedding model: {model_name}'); SentenceTransformer(model_name); print('Model cached successfully.')" || echo "Model preload failed, will try at runtime"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint for automatic Elasticsearch initialization
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

# Run the application (passed to entrypoint)
CMD ["python", "-m", "uvicorn", "src.ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
