#!/usr/bin/env python3
"""
Simple runner script for database migrations.
Run this from the notelecture-backend directory.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from app.db.migrations.001_add_users import main
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the notelecture-backend directory")
        print("and that all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)