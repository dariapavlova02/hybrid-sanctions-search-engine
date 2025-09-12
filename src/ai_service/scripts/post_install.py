#!/usr/bin/env python3
"""
Post-install script for automatic SpaCy models installation
Runs automatically after poetry install
"""

import subprocess
import sys
import os
import importlib.util
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def is_model_installed(model_name: str) -> bool:
    """Check if model is installed"""
    try:
        import spacy
        # Try to actually load the model
        nlp = spacy.load(model_name)
        return True
    except OSError:
        return False


def install_spacy_model(model_name: str, display_name: str) -> bool:
    """Install SpaCy model"""
    logger.info(f"Installing {display_name}...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "spacy", "download", model_name
        ], capture_output=True, text=True, check=True)
        logger.info(f"{display_name} successfully installed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing {display_name}: {e}")
        if e.stderr:
            logger.error(f"Details: {e.stderr}")
        return False


def install_nltk_data():
    """Install NLTK data"""
    logger.info("Installing NLTK data...")
    try:
        import nltk
        import os
        
        # Set NLTK data path to a writable location
        nltk_data_path = "/app/nltk_data"
        os.environ['NLTK_DATA'] = nltk_data_path
        
        # Download NLTK data
        nltk.download('stopwords', download_dir=nltk_data_path, quiet=True)
        nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
        nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_path, quiet=True)
        
        logger.info(f"NLTK data successfully installed to {nltk_data_path}")
        return True
    except Exception as e:
        logger.error(f"Error installing NLTK data: {e}")
        return False

def main():
    """Main post-install script function"""
    logger.info("Post-install: Checking and installing SpaCy models and NLTK data...")
    
    # Install NLTK data first
    if install_nltk_data():
        logger.info("NLTK data installed successfully")
    else:
        logger.warning("Failed to install NLTK data")
    
    models = [
        ("en_core_web_sm", "English model (en_core_web_sm)"),
        ("ru_core_news_sm", "Russian model (ru_core_news_sm)"),
        ("uk_core_news_sm", "Ukrainian model (uk_core_news_sm)")
    ]
    
    models_to_install = []
    
    # Check which models are already installed
    for model_name, display_name in models:
        if is_model_installed(model_name):
            logger.info(f"{display_name} already installed")
        else:
            logger.warning(f"{display_name} not found, will be installed")
            models_to_install.append((model_name, display_name))
    
    if not models_to_install:
        logger.info("All models already installed!")
        return
    
    logger.info(f"Installing {len(models_to_install)} missing models...")
    
    success_count = 0
    for model_name, display_name in models_to_install:
        if install_spacy_model(model_name, display_name):
            success_count += 1
    
    logger.info(f"Result: {success_count}/{len(models_to_install)} models installed")
    
    if success_count == len(models_to_install):
        logger.info("All models installed! Service is ready to work.")
    else:
        logger.warning("Some models could not be installed automatically.")
        logger.info("Try running manually: python -m spacy download <model_name>")


if __name__ == "__main__":
    main()
