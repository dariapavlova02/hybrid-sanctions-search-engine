#!/usr/bin/env python3
"""Deploy decision engine fix to production server"""

import paramiko
import os
from pathlib import Path

# Production server details
PROD_HOST = "95.217.84.234"
PROD_USER = "root"
PROD_PATH = "/root/ai-service"

def deploy_decision_fix():
    """Deploy only the decision_engine.py file with the search fix"""

    local_file = "/Users/dariapavlova/Desktop/ai-service/src/ai_service/core/decision_engine.py"
    remote_file = f"{PROD_PATH}/src/ai_service/core/decision_engine.py"

    print("🚀 Deploying decision engine fix to production...")

    # Check if local file exists and has the fix
    with open(local_file, 'r') as f:
        content = f.read()
        if 'search=inp.search' not in content:
            print("❌ Local file doesn't contain the search fix!")
            return False

    print("✅ Local file contains the search fix")

    # Upload to production
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"📡 Connecting to {PROD_HOST}...")
        ssh.connect(PROD_HOST, username=PROD_USER)

        # Backup original file
        print("💾 Creating backup...")
        stdin, stdout, stderr = ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S)")
        stdout.read()

        # Upload the fixed file
        print("📤 Uploading fixed decision_engine.py...")
        sftp = ssh.open_sftp()
        sftp.put(local_file, remote_file)
        sftp.close()

        # Restart AI service
        print("🔄 Restarting AI service...")
        stdin, stdout, stderr = ssh.exec_command("cd /root/ai-service && docker-compose restart ai-service")
        restart_output = stdout.read().decode()
        restart_error = stderr.read().decode()

        if restart_error:
            print(f"⚠️ Restart output: {restart_error}")

        print("✅ Decision engine fix deployed successfully!")
        print("🧪 Test with: curl -X POST http://95.217.84.234:8002/process -H 'Content-Type: application/json' -d '{\"text\": \"Петро Порошенко\"}'")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy_decision_fix()