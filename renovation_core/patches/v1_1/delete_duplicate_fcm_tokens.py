import frappe


def execute():
  duplicate_tokens = frappe.db.sql("""
  SELECT
    token.name as token_name,
    token.creation as token_creation,
    token_dup.name as token_dup_name,
    token_dup.creation as token_dup_creation
  FROM `tabFCM User Token` token
    INNER JOIN `tabFCM User Token` token_dup
  ON token.token = token_dup.token
  WHERE
    token.name != token_dup.name
  """, as_dict=1)

  for d in duplicate_tokens:
    if d.token_creation > d.token_dup_creation:
      frappe.delete_doc("FCM User Token", d.token_dup_name, force=1)
    else:
      frappe.delete_doc("FCM User Token", d.token_name, force=1)
