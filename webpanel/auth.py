from fastapi import Request
from fastapi.responses import RedirectResponse

from config import WEBPANEL_USERNAME, WEBPANEL_PASSWORD


def check_credentials(username: str, password: str) -> bool:
    return username == WEBPANEL_USERNAME and password == WEBPANEL_PASSWORD


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get("logged_in"))


def require_login(request: Request):
    """FastAPI dependency: login qilinmagan bo'lsa, /login sahifasiga yo'naltiradi."""
    if not is_logged_in(request):
        return RedirectResponse(url="/login", status_code=302)
    return None
