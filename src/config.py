class Config:
    SECRET_KEY = "your-very-secret-key-change-me"
    SQLALCHEMY_DATABASE_URI = "sqlite:///data/kna_archive.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max per file
    RESOURCES_FOLDER = "resources"  # permanent storage
    UPLOAD_FOLDER = "uploads"       # temporary inbox
    THUMBNAIL_SUBDIR = "thumbnails"
    STATIC_IMAGES_FOLDER = "static/images"  # fallback placeholders