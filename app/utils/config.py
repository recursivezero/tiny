import os

from dotenv import load_dotenv


def load_env():
    env = os.getenv("ENV", "development")
    file_map = {
        "production": ".env",
        "local": ".env.local",
        "development": ".env.development",
    }
    load_dotenv(file_map.get(env, ".env.development"), override=True)
    print(f"Environment selected: {env}")
    print(f"MODE value: {os.getenv('MODE')}")
