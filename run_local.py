#!/usr/bin/env python3
"""
Local development script for AI Service
Run this from the project root directory
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for local development
os.environ['LOGGING_CONFIG'] = str(project_root / 'src' / 'ai_service' / 'config' / 'logging_dev.yml')
os.environ['NLTK_DATA'] = str(project_root / 'nltk_data')

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.ai_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
