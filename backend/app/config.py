from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str
    # Update schedule: cron format (minute, hour, day, month, day_of_week)
    # Default: daily at 2:00 AM
    # Example: "0 2 * * *" = daily at 2 AM, "0 */6 * * *" = every 6 hours
    CONSTRUCTION_UPDATE_SCHEDULE: str = "0 2 * * *"  # Every day at 2 AM
    # Path to store construction.geojson file
    # Default: /app/data/construction.geojson (inside container)
    CONSTRUCTION_GEOJSON_PATH: str = str(Path("/app/data/construction.geojson"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
