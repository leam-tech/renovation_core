import frappe
import requests
from frappe.utils import cint
from six import string_types
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True)
def log_info(content, title=None, tags=None):
  return make_log(
      log_type="Info", content=content, title=title, tags=tags
  )


@frappe.whitelist(allow_guest=True)
def log_warning(content, title=None, tags=None):
  return make_log(
      log_type="Warning", content=content, title=title, tags=tags
  )


@frappe.whitelist(allow_guest=True)
def log_error(content, title=None, tags=None):
  return make_log(
      log_type="Error", content=content, title=title, tags=tags
  )


@frappe.whitelist(allow_guest=True)
def log_client_request(request, response, http_code=None, tags=None):
  return make_log(
      log_type="Request",
      request=request,
      http_code=http_code,
      response=response,
      tags=tags
  )


def make_log(**kwargs):
  tags = kwargs.get("tags") or []
  if isinstance(tags, string_types):
    if tags.startswith("["):
      tags = frappe.parse_json(tags)
    else:
      tags = [tags]
  tags.append(frappe.local.site)
  kwargs["tags"] = frappe.as_json(tags)

  header = requests.utils.default_headers()
  header.update({
      "Accept": "application/json",
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
  })
  r = requests.post(
      frappe.get_site_config().get("log_url"),
      json=frappe._dict(
          cmd="renovation_logging.api.make_log",
          user=frappe.session.user,
          **kwargs
      ),
      headers=header
  )

  if not r.ok:
    frappe.throw(r.text)
  return r.json().get("message")


def log_request(response):
  if not isinstance(response, Response):
    return
  if not logging_enabled(response) or ignore_cmd():
    return

  if response.calculate_content_length() < (1024 * 1024 * 2):  # 2MB
    if response.content_type == "application/json":
      d = frappe.as_json(frappe.parse_json(response.get_data(as_text=True)))
    elif response.content_type == "application/pdf":
      d = "-- pdf-file --"
    else:
      d = "-- response-content-type: {} --".format(response.content_type)
  else:
    d = "-- response-bigger-than 2048 Bytes --"

  frappe.enqueue(
      "renovation_core.utils.logging._log_request",
      req_headers=frappe.as_json(dict(frappe.local.request.headers)),
      req_params=frappe.as_json(frappe.local.form_dict),
      response=d,
      http_code=response.status_code,
      response_headers=frappe.as_json(dict(response.headers))
  )


def _log_request(req_headers, req_params, response, http_code, response_headers):
  make_log(
      log_type="Request",
      tags=[],
      request="Headers:\n{}\n\nParams:\n{}".format(req_headers, req_params),
      http_code=http_code,
      response="Code: {}\nHeaders:\n{}\n\nBody:\n{}".format(
          http_code, response_headers, response)
  )


def ignore_cmd():
  limited = get_limited_apps()
  if not len(limited):
    return False

  cmd = frappe.local.form_dict.cmd
  if not cmd:
    return False

  if cmd.split(".")[0] in limited:
    return False

  return True


def logging_enabled(response):
  if not isinstance(response, Response):
    return
  logging_settings = frappe.cache().get_value("logging_settings")

  if not logging_settings:
    update_cache()
    return logging_enabled(response)

  if logging_settings.always_log_4xx_request and response.status_code in range(400, 600):
    return True

  if logging_settings.log_all_requests:
    return True

  return False


def get_limited_apps():
  return frappe.cache().get_value("limit_logging_to_apps") or []


def update_cache():
  logging_settings = frappe.get_value("System Settings", None,
                                      ["log_all_requests", "always_log_4xx_request",
                                       "limit_logging_to_apps"],
                                      as_dict=1)
  if not logging_settings:
    # there are some rare conditions when this can be null
    # maybe when frappe errored out before init db?
    logging_settings = frappe._dict()
  logging_settings.log_all_requests = cint(
      logging_settings.get("log_all_requests", 0))
  logging_settings.always_log_4xx_request = cint(
      logging_settings.get("always_log_4xx_request", 0))
  logging_settings.limit_logging_to_apps = (
      logging_settings.get("limit_logging_to_apps", None) or "").split("\n")

  frappe.cache().set_value("logging_settings", logging_settings)
