import os
from fastapi import FastAPI

import frappe
from .frappehandler import FrappeMiddleware
from .utils.app import load_renovation_app_info


def get_app():
    fastapi_app = FastAPI()
    fastapi_app.add_middleware(FrappeMiddleware)

    @fastapi_app.get("/info")
    def read_root():
        available_doctypes = frappe.get_list("DocType")
        settings = frappe.get_single("System Settings")
        return {
            "available_doctypes": available_doctypes,
            "settings": settings.as_dict(),
        }

    frappe.init(site=os.environ.get("SITE_NAME", "test.localhost"))
    info = load_renovation_app_info()
    frappe.destroy()

    # Load Renovation App Routers
    for app in info.apps:
        router = getattr(frappe.get_module(f"{app}.api"), "router", None)
        if router:
            fastapi_app.include_router(router)

    return fastapi_app


app = get_app()
