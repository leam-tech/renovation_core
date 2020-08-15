import json
import subprocess

import frappe
from datetime import datetime, timedelta
import jwt


def generate_apple_client_secret():
  apple_keys = frappe.conf.get('apple_keys')
  if not apple_keys:
    frappe.log_error("Please set the apple keys in common_site_config")
    return

  headers = {
      "kid": apple_keys.get("kid")
  }

  # Common payload details for all platforms
  payload = {
      "iss": apple_keys.get("iss"),
      "iat": datetime.timestamp(datetime.now()),
      "exp": datetime.timestamp(datetime.now() + timedelta(days=180)),
      "aud": "https://appleid.apple.com"
  }

  native_keys = frappe.conf.get('apple_login_native')

  native_payload = {**payload, "sub": native_keys.get('client_id')}

  web_keys = frappe.conf.get('apple_login_web')
  android_keys = frappe.conf.get('apple_login_android')

  web_payload = {**payload, "sub": web_keys.get('client_id')}

  native_client_secret = jwt.encode(native_payload, apple_keys.get('private_key'), algorithm='ES256',
                                    headers=headers).decode('utf-8')

  web_client_secret = jwt.encode(web_payload, apple_keys.get('private_key'), algorithm='ES256', headers=headers).decode(
      'utf-8')

  native_keys['client_secret'] = native_client_secret

  # Since web and Android are considered non-native to Apple, and they have the same client ID they will have the same
  # client secret
  web_keys['client_secret'] = web_client_secret
  android_keys['client_secret'] = web_client_secret

  # Finally update the file `common_site_config.json`
  subprocess.check_output(["bench", "set-config", "apple_login_native", json.dumps(native_keys), '--as-dict', '-g'],
                          cwd="..")
  subprocess.check_output(["bench", "set-config", "apple_login_web", json.dumps(web_keys), '--as-dict', '-g'], cwd="..")
  subprocess.check_output(["bench", "set-config", "apple_login_android", json.dumps(android_keys), '--as-dict', '-g'],
                          cwd="..")
