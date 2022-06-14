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

    # FastAPI-Routes are not properly multi tenanted
    # This is assuming that all sites in the bench will share the same set of
    # installed-apps
    # eg. All sites in pms-clients-bench will have same set of apps and routes
    # Hence, provide SAMPLE_SITE as one of the sites in bench for reading routes info
    # This could be improved in the future with @renovation.api decorator
    site = os.environ.get("SAMPLE_SITE", None) or os.environ.get("SITE_NAME", None)
    frappe.init(site=site)
    info = load_renovation_app_info()
    frappe.destroy()

    # Load Renovation App Routers
    for app in info.apps:
        router = getattr(frappe.get_module(f"{app}.api"), "router", None)
        if router:
            fastapi_app.include_router(router)

    return fastapi_app


app = get_app()
