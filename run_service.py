#!/usr/bin/env python3
"""
Script for running AI Service with dependency checks
"""

import sys
import os
import subprocess
from pathlib import Path
import logging

try:
    import spacy
except ImportError:
    spacy = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 12):
        logger.error("Python 3.12 or higher required")
        logger.error(f"Current version: {sys.version}")
        return False
    
    logger.info(f"Python version: {sys.version.split()[0]}")
    return True


def check_poetry():
    """Check Poetry availability"""
    try:
        result = subprocess.run(['poetry', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Poetry: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    logger.error("Poetry not found")
    logger.info("Install Poetry: https://python-poetry.org/docs/#installation")
    return False


def check_dependencies():
    """Check dependencies"""
    try:
        result = subprocess.run(['poetry', 'install'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Dependencies installed")
            return True
        else:
            logger.error(f"Error installing dependencies: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def check_spacy_models():
    """Check SpaCy models"""
    models = ['en_core_web_sm', 'ru_core_news_sm']
    missing_models = []
    
    if spacy is None:
        logger.error("SpaCy not installed")
        return False
    
    for model in models:
        try:
            nlp = spacy.load(model)
            logger.info(f"SpaCy model {model} loaded")
        except OSError:
            missing_models.append(model)
            logger.warning(f"SpaCy model {model} not found")
    
    if missing_models:
        logger.info("Install missing models:")
        for model in missing_models:
            logger.info(f"  poetry run post-install")
        
        # Try to install automatically
        logger.info("Automatic model installation...")
        for model in missing_models:
            try:
                result = subprocess.run([
                    'poetry', 'run', 'python', '-m', 'spacy', 'download', model
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"{model} installed")
                else:
                    logger.error(f"Error installing {model}")
            except Exception as e:
                logger.error(f"Error: {e}")
    
    return len(missing_models) == 0


def run_service():
    """Run service"""
    logger.info("Starting AI Service...")
    
    # Handle both real file path and mocked __file__ in tests
    try:
        service_path = Path(__file__).parent / "src" / "ai_service" / "main.py"
    except (TypeError, AttributeError):
        # Fallback for tests where __file__ is mocked
        service_path = Path("src") / "ai_service" / "main.py"
    
    if not service_path.exists():
        logger.error(f"Service file not found: {service_path}")
        return False
    
    try:
        logger.info(f"Service path: {service_path}")
        logger.info("Service will be available at: http://localhost:8000")
        logger.info("API documentation: http://localhost:8000/docs")
        logger.info("Press Ctrl+C to stop")
        
        # Starting service
        subprocess.run([
            'poetry', 'run', 'python', str(service_path)
        ])
        
    except KeyboardInterrupt:
        logger.info("Service stopped")
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        return False
    
    return True


def main():
    """Main function"""
    logger.info("Checking dependencies for AI Service...")
    
    checks = [
        ("Python Version", check_python_version),
        ("Poetry", check_poetry),
        ("Dependencies", check_dependencies),
        ("SpaCy Models", check_spacy_models),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        logger.info(f"--- {check_name} ---")
        if not check_func():
            all_passed = False
    
    if all_passed:
        logger.info("All checks passed successfully!")
        run_service()
    else:
        logger.error("Some checks failed")
        logger.info("Fix errors and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()
