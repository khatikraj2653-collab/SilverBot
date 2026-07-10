import subprocess
import sys
import os

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
