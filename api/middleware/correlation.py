import uuid
from fastapi import Request
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract existing X-Request-ID from headers or generate a new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        # Bind the request ID to the structured logger context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Process the request
        response = await call_next(request)
        
        # Add the request ID to the response headers
        response.headers["X-Request-ID"] = request_id
        
        # Clear the context variables for the next request (though structlog does this automatically per asyncio task)
        structlog.contextvars.clear_contextvars()
        
        return response
