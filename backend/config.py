# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    
    # ============ Server Settings ============
    APP_NAME: str = os.getenv("APP_NAME", "AI Job Recommender API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ============ Database Settings ============
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://user:password@localhost/job_recommender"
    )
    
    # ============ JWT Settings ============
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # ============ OCR Settings (Tesseract) ============
    # Đường dẫn đến Tesseract executable (Windows)
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    
    # Ngôn ngữ OCR (eng: English, vie: Vietnamese)
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng")
    
    # Cấu hình Tesseract
    TESSERACT_CONFIG: str = os.getenv(
        "TESSERACT_CONFIG", 
        "--oem 3 --psm 6"
    )
    
    # ============ Image Preprocessing Settings ============
    OCR_IMAGE_MIN_WIDTH: int = int(os.getenv("OCR_IMAGE_MIN_WIDTH", "1000"))
    OCR_CONTRAST_ENHANCE_FACTOR: float = float(os.getenv("OCR_CONTRAST_ENHANCE_FACTOR", "2.0"))
    
    # ============ Embedding Settings ============
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # ============ CORS Settings ============
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:3001,http://localhost:3002"
    ).split(",")
    
    # ============ File Upload Settings ============
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: list = os.getenv(
        "ALLOWED_EXTENSIONS",
        ".pdf,.docx,.txt,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
    ).split(",")
    
    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Return max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    def get_tesseract_config(self) -> str:
        """Get Tesseract configuration with language setting."""
        return f"--oem 3 --psm 6 -l {self.OCR_LANGUAGE}"

# Create a single instance of settings
settings = Settings()