#!/usr/bin/env python3
"""
Simple database creation script.
This is now just a wrapper around the comprehensive migrate.py script.
"""

import os
import sys

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    try:
        from app.db.migrate import main
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root and dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        sys.exit(1)