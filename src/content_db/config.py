"""
KNA Configuration Module

Loads configuration from .env files using python-dotenv.
Environment variables are automatically loaded before reading.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from dotenv import load_dotenv, find_dotenv


def _load_environment():
    """
    Load environment variables from .env file.

    Search order:
    1. .env.{FLASK_ENV} (e.g., .env.development) - if FLASK_ENV is set
    2. .env (default)
    3. System environment variables (fallback)

    Returns:
        str: Path to loaded .env file, or None if not found
    """
    if env := os.getenv("FLASK_ENV"):
        env_file = f".env.{env}"
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            print(f"✓ Loaded environment from: {env_file}")
            return env_file

    if env_file := find_dotenv():
        load_dotenv(env_file)
        print(f"✓ Loaded environment from: {env_file}")
        return env_file

    print("⚠ No .env file found - using system environment variables")
    return None


# Load environment variables from .env file
# This runs when the module is imported
_env_file = _load_environment()


class BaseConfig:
    """Base configuration with common settings"""

    # Flask settings (loaded from .env)
    SECRET_KEY = os.getenv("FLASK_SECRET", os.urandom(32).hex())
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MiB

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

    # Resources directory (from .env)
    DIR_RESOURCES = os.getenv("DIR_RESOURCES", "./resources/")

    # Database paths (to be overridden in subclasses)
    SQLITE_KNA_PATH = None
    SQLITE_USERS_PATH = None

    @property
    def kna_database_uri(self) -> str:
        """
        SQLAlchemy URI for KNA content database.
        
        Uses absolute path to avoid SQLite path resolution issues.
        """
        if not self.SQLITE_KNA_PATH:
            raise ValueError("SQLITE_KNA_PATH not configured")
        
        # Convert to absolute path for SQLite reliability
        db_path = Path(self.SQLITE_KNA_PATH).resolve()
        return f"sqlite:///{db_path}"

    @property
    def users_database_uri(self) -> str:
        """
        SQLAlchemy URI for Users database (Flask-Login).
        
        Uses absolute path to avoid SQLite path resolution issues.
        """
        if not self.SQLITE_USERS_PATH:
            raise ValueError("SQLITE_USERS_PATH not configured")
        
        # Convert to absolute path for SQLite reliability
        db_path = Path(self.SQLITE_USERS_PATH).resolve()
        return f"sqlite:///{db_path}"

    # Alias for Flask-SQLAlchemy (uses users database)
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Primary database for Flask-SQLAlchemy (users)"""
        return self.users_database_uri

    def get_kna_engine(self):
        """Get SQLAlchemy engine for KNA content database"""
        return create_engine(
            self.kna_database_uri,
            connect_args={"check_same_thread": False}  # Allow multi-threading
        )

    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        # Create resources directory
        Path(self.DIR_RESOURCES).mkdir(parents=True, exist_ok=True)

        # Create database directories
        for db_path in [self.SQLITE_KNA_PATH, self.SQLITE_USERS_PATH]:
            if db_path and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(BaseConfig):
    """Development configuration"""

    DEBUG = True
    TESTING = False

    # Database paths from .env file (loaded above)
    SQLITE_KNA_PATH = os.getenv("SQLITE_KNA_PATH", "data/kna_dev.db")
    SQLITE_USERS_PATH = os.getenv("SQLITE_USERS_PATH", "data/users_dev.db")


class ProductionConfig(BaseConfig):
    """Production configuration"""

    DEBUG = False
    TESTING = False

    # Database paths from .env file (required in production)
    SQLITE_KNA_PATH = os.getenv("SQLITE_KNA_PATH")
    SQLITE_USERS_PATH = os.getenv("SQLITE_USERS_PATH")

    def __init__(self):
        super().__init__()
        # Validate required environment variables in production
        if not self.SQLITE_KNA_PATH:
            raise ValueError(
                "SQLITE_KNA_PATH environment variable required in production. "
                "Set it in .env file or environment."
            )
        if not self.SQLITE_USERS_PATH:
            raise ValueError(
                "SQLITE_USERS_PATH environment variable required in production. "
                "Set it in .env file or environment."
            )


class TestingConfig(BaseConfig):
    """Testing configuration"""

    DEBUG = False
    TESTING = True

    # Use in-memory databases for testing
    SQLITE_KNA_PATH = ":memory:"
    SQLITE_USERS_PATH = ":memory:"

    # Temporary resources for testing
    DIR_RESOURCES = "/tmp/kna_test_resources/"


# Configuration registry
_config_registry = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(env: str = None) -> BaseConfig:
    """
    Get configuration object for specified environment.

    Args:
        env: Environment name ('development', 'production', 'testing')
             If None, uses FLASK_ENV from .env file or environment

    Returns:
        Configuration object instance

    Example:
        >>> # With .env file containing FLASK_ENV=development
        >>> config = get_config()
        >>> print(config.SQLITE_KNA_PATH)
        data/kna_dev.db

        >>> # Explicit environment
        >>> config = get_config('production')
        >>> print(config.DEBUG)
        False
    """
    if env is None:
        env = os.getenv("FLASK_ENV", "production")

    config_class = _config_registry.get(env)
    if not config_class:
        raise ValueError(
            f"Unknown environment: {env}. "
            f"Must be one of {list(_config_registry.keys())}"
        )

    config = config_class()
    config.ensure_directories()
    return config


# Convenience accessors for backwards compatibility
def get_development_config() -> DevelopmentConfig:
    """Get development configuration"""
    return get_config("development")


def get_production_config() -> ProductionConfig:
    """Get production configuration"""
    return get_config("production")


def get_testing_config() -> TestingConfig:
    """Get testing configuration"""
    return get_config("testing")
