import frappe
import jwt
from frappe.auth import HTTPRequest, LoginManager, get_lang_code, check_session_stopped, CookieManager


# frappe's CookieManager is having old class style
class CookieManagerJWT(CookieManager, object):
  def flush_cookies(self, response):
    # use this opportunity to set the response headers
    response.headers["X-Client-Site"] = frappe.local.site
    if frappe.flags.jwt_clear_cookies:
      # Case when right after login
      # We set the flag on session_create
      self.cookies = frappe._dict()
    if frappe.flags.jwt:
      # Case when the incoming request has jwt token
      # We leave cookies untouched
      # There can be other browser tabs
      return
    return super(CookieManagerJWT, self).flush_cookies(response)


class RenovationHTTPRequest(HTTPRequest):
  def __init__(self):
    # Get Environment variables
    self.domain = frappe.request.host
    if self.domain and self.domain.startswith('www.'):
      self.domain = self.domain[4:]

    if frappe.get_request_header('X-Forwarded-For'):
      frappe.local.request_ip = (frappe.get_request_header(
          'X-Forwarded-For').split(",")[0]).strip()

    elif frappe.get_request_header('REMOTE_ADDR'):
      frappe.local.request_ip = frappe.get_request_header('REMOTE_ADDR')

    else:
      frappe.local.request_ip = '127.0.0.1'

    # language
    self.set_lang()

    # set db before jwt check, so token error handling can be stored
    # We get Internal Server Error otherwise
    self.connect()

    # JWT
    jwt_token = None
    # Check for Auth Header, if present, replace the request cookie value
    if frappe.get_request_header("Authorization"):
      token_header = frappe.get_request_header(
          "Authorization").split(" ")

      if token_header[0].lower() not in ("basic", "bearer") and ":" not in token_header[-1]:
        jwt_token = token_header[-1]
    elif frappe.request.path.startswith('/private/files/') and frappe.request.args.get("token"):
      jwt_token = frappe.request.args.get("token")

    if jwt_token:
      headers = frappe._dict(frappe.request.headers)
      headers["Authorization"] = f"Bearer {jwt_token}"
      frappe.request.headers = headers

    # load cookies
    frappe.local.cookie_manager = CookieManagerJWT()

    # login
    frappe.local.login_manager = LoginManager()

    if frappe.form_dict._lang:
      lang = get_lang_code(frappe.form_dict._lang)
      if lang:
        frappe.local.lang = lang

    self.validate_csrf_token()

    # write out latest cookies
    frappe.local.cookie_manager.init_cookies()

    # check status
    check_session_stopped()
