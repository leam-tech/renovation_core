import frappe, json
from renovation_core.utils.fcm import _add_user_token

def execute():
  fcm_defaults_key = "fcm_reg_tokens"
  tokens = frappe.db.get_all("DefaultValue", fields=["parent", "defValue"], filters={
    "defKey": fcm_defaults_key
  })

  for token_json in tokens:
    try:
      user_tokens = json.loads(token_json.defValue or "[]")
      for t in user_tokens:
        try:
          _add_user_token(user=token_json.parent, token=t)
        except:
          pass
    except:
      print("Failed FCM Migration for {}".format(token_json.parent))
      print(frappe.get_traceback())