import os

# Server configuration
SIGNALING_PORT = int(os.getenv("SIGNALING_PORT", 8000))

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Other settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
