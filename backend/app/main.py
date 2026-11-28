import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.routes import admin, applications, auth, members, notifications, public, super_admin
from app.core.config import settings
from app.middleware.security import CSRFMiddleware, SecurityHeadersMiddleware

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("avtbvs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_production:
        problems = settings.validate_production()
        if problems:
            raise RuntimeError("Refusing to start in production: " + "; ".join(problems))
    if settings.EMAIL_PROVIDER == "console" or settings.SMS_PROVIDER == "console":
        logger.warning("Console notification provider active: messages are written to %s, not delivered",
                       settings.CONSOLE_OUTBOX_FILE)
    stop = asyncio.Event()
    task = None
    if settings.NOTIFICATION_WORKER_ENABLED:
        from app.workers.notifications import worker_loop
        task = asyncio.create_task(worker_loop(stop))
    yield
    stop.set()
    if task:
        await task


TAGS = [
    {"name": "Authentication", "description": "Accounts, login, verification, password reset. Auth uses HttpOnly "
                                              "cookies; Bearer tokens are accepted for API clients."},
    {"name": "Membership Applications", "description": "Applicant workflow for the Life Membership Application form."},
    {"name": "Member Directory & Member Self-Service", "description": "Public (name + father's name only) and "
                                                                      "member-only directory; profile edit requests."},
    {"name": "Admin", "description": "Admin & Super Admin: review, approval, existing members, edit requests, reports."},
    {"name": "Super Admin", "description": "Super Admin only: admin management, audit logs, system settings."},
    {"name": "Notifications", "description": "Website notifications for the logged-in user."},
    {"name": "Private Files", "description": "Authorised access to photographs and documents."},
    {"name": "Public", "description": "Health and public configuration."},
]

app = FastAPI(
    title="AVTBVS Membership API",
    version="1.0.0",
    description="Membership management API for Ayira Vaisyar Telugu Beri Vysya Sabha (AVTBVS).",
    openapi_tags=TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": False, "displayRequestDuration": True},
)

app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
        msg = err.get("msg", "Invalid value").removeprefix("Value error, ")
        errors[".".join(loc) or "request"] = msg
    return JSONResponse(status_code=422, content={"detail": {"message": "Please correct the highlighted fields",
                                                             "errors": errors}})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred. Please try again."})


for module in (public, auth, applications, members, admin, super_admin, notifications):
    app.include_router(module.router, prefix=settings.API_PREFIX)
app.include_router(members.files_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """This server is the API only; send people who open it in a browser to the website."""
    return RedirectResponse(settings.PUBLIC_APP_URL)
