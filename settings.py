from pydantic_settings import BaseSettings
from pydantic import validator, Field
import os

class AppSettings(BaseSettings):
    download_dir: str = Field(default=os.getcwd(), alias='DOWNLOAD_DIR')
    theme: str = Field(default="darkly", alias='THEME')
    video_format: str = Field(default="mp4", alias='VIDEO_FORMAT')
    audio_format: str = Field(default="mp3", alias='AUDIO_FORMAT')
    concurrent_downloads: int = Field(default=1, alias='CONCURRENT_DOWNLOADS')
    extension_id: str = Field(default="", alias='EXTENSION_ID')
    
    @validator('concurrent_downloads')
    def validate_concurrent_downloads(cls, v):
        if not 1 <= v <= 10:
            raise ValueError('Concurrent downloads must be between 1 and 10')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = "ignore"
