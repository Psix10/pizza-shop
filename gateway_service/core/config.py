import os


class Settings:
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))

    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service_pizza:8001")
    PROFILE_SERVICE_URL: str = os.getenv("PROFILE_SERVICE_URL", "http://profile_service_pizza:8002")
    CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://catalog_service_pizza:8003")
    STORE_SERVICE_URL: str = os.getenv("STORE_SERVICE_URL", "http://store_service_pizza:8004")
    ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://order_service_pizza:8005")
    KITCHEN_SERVICE_URL: str = os.getenv("KITCHEN_SERVICE_URL", "http://kitchen_service_pizza:8006")
    DELIVERY_SERVICE_URL: str = os.getenv("DELIVERY_SERVICE_URL", "http://delivery_service_pizza:8007")
    SUPPORT_CHAT_SERVICE_URL: str = os.getenv("SUPPORT_CHAT_SERVICE_URL", "http://support_chat_service_pizza:8008")
    NOTIFICATION_SERVICE_URL: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification_service_pizza:8009")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")


settings = Settings()