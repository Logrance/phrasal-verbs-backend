from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str
    COLAB_WS_URL: str
    Mongo_DB: str

    class Config:
        env_file = ".env"

settings = Settings()
