"""
KNA Archive - Unified Configuration
Supports development, production, and containerized deployments
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()


class Config:
    """Base configuration - works for all environments"""
    
    # ─── Flask Core ──────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # ─── File Upload ─────────────────────────────────────────────
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "pdf", "mp4", "mov", "docx", "doc"}
    
    # ─── Database ────────────────────────────────────────────────
    # For containers: /data/db/kna_archive.db
    # For local dev:  ../data/kna_archive.db (outside src/)
    DATABASE_DIR = os.getenv("DATABASE_DIR", str(Path(__file__).parent.parent / "data"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(DATABASE_DIR) / 'kna_archive.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQL_ECHO", "False").lower() == "true"
    
    # ─── Media Storage ───────────────────────────────────────────
    # For containers: /data/resources/
    # For local dev:  ../resources/ (outside src/)
    RESOURCES_DIR = os.getenv("RESOURCES_DIR", str(Path(__file__).parent.parent / "resources"))
    RESOURCES_FOLDER = RESOURCES_DIR  # Alias for backward compatibility
    
    # Temporary upload staging area
    UPLOADS_DIR = os.getenv("UPLOADS_DIR", str(Path(__file__).parent.parent / "uploads"))
    UPLOAD_FOLDER = UPLOADS_DIR  # Alias
    
    # Static assets (inside src/ - these get copied into containers)
    STATIC_IMAGES_FOLDER = "static/images"
    THUMBNAIL_SUBDIR = "thumbnails"
    
    # ─── Directory Creation ──────────────────────────────────────
    @classmethod
    def ensure_directories(cls):
        """Create all necessary directories"""
        directories = [
            Path(cls.DATABASE_DIR),
            Path(cls.RESOURCES_DIR),
            Path(cls.UPLOADS_DIR),
            Path(cls.STATIC_IMAGES_FOLDER),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    @classmethod
    def init_app(cls, app):
        """Initialize Flask app with this config"""
        cls.ensure_directories()


class DevelopmentConfig(Config):
    """Development-specific settings"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production-specific settings"""
    DEBUG = False
    
    # In production, require SECRET_KEY from environment
    def __init__(self):
        if Config.SECRET_KEY == "dev-secret-key-CHANGE-IN-PRODUCTION":
            raise ValueError("SECRET_KEY must be set in production! Add to .env or environment")


class TestingConfig(Config):
    """Testing-specific settings"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # In-memory for tests


# ─── Config Selection ────────────────────────────────────────────
_configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

def get_config(env=None):
    """Get configuration for specified environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    config_class = _configs.get(env, DevelopmentConfig)
    return config_class()
