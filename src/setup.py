#!/usr/bin/env python3
"""
Setup script for KNA Theatre Archive
Run this before starting the application for the first time
"""
import os
import sys

def create_directories():
    """Create all necessary directories"""
    directories = [
        'data',
        'uploads',
        'resources',
        'static/images',
        'templates/partials',
    ]
    
    print("Creating directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ {directory}")
    print()

def create_database():
    """Initialize the database with all tables"""
    print("Initializing database...")
    
    # Import after directories exist
    from content_db.database import db
    from app import app
    
    with app.app_context():
        db.create_all()
        print("  ✓ Database tables created")
    print()

def check_config():
    """Check if config.py has the right settings"""
    print("Checking configuration...")
    try:
        from config import Config
        
        required_settings = [
            'SECRET_KEY',
            'SQLALCHEMY_DATABASE_URI',
            'UPLOAD_FOLDER',
            'RESOURCES_FOLDER',
        ]
        
        for setting in required_settings:
            if hasattr(Config, setting):
                print(f"  ✓ {setting}")
            else:
                print(f"  ✗ {setting} - MISSING!")
                return False
        print()
        return True
    except ImportError:
        print("  ✗ config.py not found!")
        return False

def main():
    print("=" * 60)
    print("KNA Theatre Archive - Setup")
    print("=" * 60)
    print()
    
    # Check we're in the right directory
    if not os.path.exists('app.py'):
        print("ERROR: Please run this script from the src/ directory")
        print("  cd src")
        print("  python setup.py")
        sys.exit(1)
    
    # Check config
    if not check_config():
        print("\nPlease fix your config.py before continuing")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create database
    try:
        create_database()
    except Exception as e:
        print(f"  ✗ Error creating database: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("Setup complete! You can now run the application:")
    print("  python app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
