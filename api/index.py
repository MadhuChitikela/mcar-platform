import sys
import os

# Append root directory to sys.path so Vercel can locate main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
