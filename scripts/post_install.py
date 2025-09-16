#!/usr/bin/env python3
"""
Post-installation script for AI Service
Installs all required models and dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Installing {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {description}: {e.stderr}")
        return False

def main():
    """Main post-installation process"""
    print("Starting AI Service post-installation...")
    
    # Change to project directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    success = True
    
    # Install SpaCy models
    spacy_models = [
        "en_core_web_sm",
        "ru_core_news_sm", 
        "uk_core_news_sm"
    ]
    
    for model in spacy_models:
        if not run_command(f"python -m spacy download {model}", f"SpaCy model {model}"):
            success = False
    
    # Download NLTK data
    nltk_data = [
        "stopwords",
        "punkt", 
        "averaged_perceptron_tagger"
    ]
    
    for data in nltk_data:
        if not run_command(f"python -c \"import nltk; nltk.download('{data}')\"", f"NLTK data {data}"):
            success = False
    
    # Install pymorphy3 dictionaries
    if not run_command("python -m pymorphy3 download ru", "Pymorphy3 Russian dictionary"):
        success = False
    
    if not run_command("python -m pymorphy3 download uk", "Pymorphy3 Ukrainian dictionary"):
        success = False
    
    if success:
        print("\n✓ All dependencies installed successfully!")
        return 0
    else:
        print("\n✗ Some dependencies failed to install. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
