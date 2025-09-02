# websites domain
import os

REDDIT = os.environ.get("REDDIT", "")
SHOPPING = os.environ.get("SHOPPING", "")
SHOPPING_ADMIN = os.environ.get("SHOPPING_ADMIN", "")
GITLAB = os.environ.get("GITLAB", "")
WIKIPEDIA = os.environ.get("WIKIPEDIA", "")
MAP = os.environ.get("MAP", "")
HOMEPAGE = os.environ.get("HOMEPAGE", "")

# Environment variables are optional for testing
# Only assert if they're needed for actual evaluation runs
if any([REDDIT, SHOPPING, SHOPPING_ADMIN, GITLAB, WIKIPEDIA, MAP, HOMEPAGE]):
    # If any are set, warn about missing ones but don't fail
    missing = []
    if not REDDIT:
        missing.append("REDDIT")
    if not SHOPPING:
        missing.append("SHOPPING")
    if not SHOPPING_ADMIN:
        missing.append("SHOPPING_ADMIN")
    if not GITLAB:
        missing.append("GITLAB")
    if not WIKIPEDIA:
        missing.append("WIKIPEDIA")
    if not MAP:
        missing.append("MAP")
    if not HOMEPAGE:
        missing.append("HOMEPAGE")

    if missing:
        print(f"Warning: Missing environment variables: {', '.join(missing)}")
        print("Set these for full evaluation functionality.")


ACCOUNTS = {
    "reddit": {"username": "MarvelsGrantMan136", "password": "test1234"},
    "gitlab": {"username": "byteblaze", "password": "hello1234"},
    "shopping": {
        "username": "emma.lopez@gmail.com",
        "password": "Password.123",
    },
    "shopping_admin": {"username": "admin", "password": "admin1234"},
    "shopping_site_admin": {"username": "admin", "password": "admin1234"},
}

URL_MAPPINGS = {
    REDDIT: "http://reddit.com",
    SHOPPING: "http://onestopmarket.com",
    SHOPPING_ADMIN: "http://luma.com/admin",
    GITLAB: "http://gitlab.com",
    WIKIPEDIA: "http://wikipedia.org",
    MAP: "http://openstreetmap.org",
    HOMEPAGE: "http://homepage.com",
}
