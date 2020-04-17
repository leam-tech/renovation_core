from __future__ import unicode_literals

import logging
import os

import frappe
from frappe.app import (NotFound, after_request,
                        get_site_name, handle_exception, local_manager,
                        make_form_dict)
from frappe.middlewares import StaticDataMiddleware
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.profiler import ProfilerMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.wrappers import Request, Response

from .auth import RenovationHTTPRequest
from .utils.logging import log_request


@Request.application
def application(request):
  response = None

  try:
    rollback = True

    init_request(request)

    frappe.recorder.record()

    if should_redirect_http() and 'localhost' not in application.config['SERVER_NAME']:
      response = Response(status=302, headers={
          "Location": "https://{}{}".format(frappe.request.host, frappe.request.path)})

    elif frappe.local.form_dict.cmd:
      response = frappe.handler.handle()

    elif frappe.request.path.startswith("/api/"):
      response = frappe.api.handle()

    elif frappe.request.path.startswith('/backups'):
      response = frappe.utils.response.download_backup(request.path)

    elif frappe.request.path.startswith('/private/files/'):
      response = frappe.utils.response.download_private_file(request.path)

    elif frappe.local.request.method in ('GET', 'HEAD', 'POST'):
      response = frappe.website.render.render()

    else:
      raise NotFound

  except HTTPException as e:
    return e

  except frappe.SessionStopped as e:
    response = frappe.utils.response.handle_session_stopped()

  except Exception as e:
    response = handle_exception(e)

  else:
    rollback = after_request(rollback)

  finally:
    if frappe.local.request.method in ("POST", "PUT") and frappe.db and rollback:
      frappe.db.rollback()

    # set cookies
    if response and hasattr(frappe.local, 'cookie_manager'):
      frappe.local.cookie_manager.flush_cookies(response=response)

    frappe.recorder.dump()
    log_request(response)

    frappe.destroy()

  return response


# just like how it is done in frappe.app
application = local_manager.make_middleware(application)


def serve(port=8000, profile=False, no_reload=False, no_threading=False, site=None, sites_path='.'):
  global application, _site, _sites_path
  _site = site
  _sites_path = sites_path

  from werkzeug.serving import run_simple

  if profile:
    application = ProfilerMiddleware(
        application, sort_by=('cumtime', 'calls'))

  if not os.environ.get('NO_STATICS'):
    application = SharedDataMiddleware(application, {
        str('/assets'): str(os.path.join(sites_path, 'assets'))
    })

    application = StaticDataMiddleware(application, {
        str('/files'): str(os.path.abspath(sites_path))
    })

  application.debug = True
  application.config = {
      'SERVER_NAME': 'localhost:8000'
  }

  in_test_env = os.environ.get('CI')
  if in_test_env:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

  run_simple('0.0.0.0', int(port), application,
             use_reloader=False if in_test_env else not no_reload,
             use_debugger=not in_test_env,
             use_evalex=not in_test_env,
             threaded=not no_threading)


def init_request(request):
  frappe.local.request = request
  frappe.local.is_ajax = frappe.get_request_header(
      "X-Requested-With") == "XMLHttpRequest"

  site = _site or request.headers.get(
      'X-Frappe-Site-Name') or get_site_name(request.host)
  frappe.init(site=site, sites_path=_sites_path)

  if not (frappe.local.conf and frappe.local.conf.db_name):
    # site does not exist
    raise NotFound

  if frappe.local.conf.get('maintenance_mode'):
    raise frappe.SessionStopped

  make_form_dict(request)

  frappe.local.http_request = RenovationHTTPRequest()


# frappe.app.init_request.__code__ = init_request.__code__


def should_redirect_http():
  if frappe.request.scheme == "https" or frappe.local.conf.do_not_redirect_browser_http:
    return False

  if frappe.get_request_header("X-Original-Host", None):
    # probably a reverse proxied request from another front end project
    # All existing reverse proxy set up uses the X-Original-Host header
    return False

  userAgent = frappe.local.request.headers.get("User-Agent").lower()
  if "mozilla" in userAgent or "chrome" in userAgent or "applewebkit" in userAgent:
    return True
