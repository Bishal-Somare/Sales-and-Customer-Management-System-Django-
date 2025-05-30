"""
ASGI config for InventoryMS project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import notifications.routing # Import your app's routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InventoryMS.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing code that may import ORM models, especially for Channels.
http_application = get_asgi_application()

application = ProtocolTypeRouter({
    "http": http_application, # Use the initialized http_application
    "websocket": AuthMiddlewareStack(
        URLRouter(
            notifications.routing.websocket_urlpatterns
        )
    ),
})