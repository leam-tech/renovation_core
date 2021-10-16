import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist(allow_guest=True)
def translate_value(values, lang, translateable_kyes=None, key=None):
  if isinstance(values, (dict, Document)):
    if isinstance(values, Document):
      values = values.as_dict()
    for k, val in values.items():
      values[k] = translate_value(val, lang, translateable_kyes, k)
  elif isinstance(values, (list, tuple, set)):
    if isinstance(values, (tuple, set)):
      values = list(values)
    for k, val in enumerate(values):
      values[k] = translate_value(val, lang, translateable_kyes, key)
  elif not (translateable_kyes and key) or key in translateable_kyes:
    values = _(values, lang)
  return values


@frappe.whitelist()
def add_translation(
        language,
        source_text,
        translated_text,
        context=None,
        doctype=None,
        docname=None,
        docfield=None):
  """
  Precedence while reading
        key:doctype:name:fieldname
        key:doctype:name
        key:parenttype:parent
        key:doctype:fieldname
        key:doctype
        key:parenttype
        key
  """

  if doctype:
    context = doctype

  if doctype and docname:
    context += f":{docname}"

  if doctype and docfield:
    meta = frappe.get_meta(doctype)
    if not meta.get_field(docfield):
      frappe.throw("Field {} do not belong to doctype {}".format(docfield, doctype))
    context += f":{docfield}"

  existing_tr = frappe.db.get_value("Translation", frappe._dict(
      language=language,
      source_text=source_text,
      context=context
  ))
  if existing_tr:
    frappe.set_value("Translation", existing_tr, "translated_text", translated_text)
    tr_doc = frappe.get_doc("Translation", existing_tr)
  else:
    tr_doc = frappe.get_doc(frappe._dict(
        doctype="Translation",
        language=language,
        source_text=source_text,
        translated_text=translated_text,
        context=context
    )).insert()

  return tr_doc


@frappe.whitelist(allow_guest=True)
def get_doc_translations(doctype, name):
  """
  Returns a dict custom tailored for the document.

  - Translations with the following contexts are handled:
    - doctype:name:docfield
    - doctype:name
    - doctype:docfield (Select fields only)
  - 'Select' docfields will have a values dict which will have
    translations for each option

  document(doctype, name) {
    [lang_code_1]: {
      title: lang_1_title,
      status: {
        value: lang_1_status,
        values: {
          option_1: lang_1_option_1,
          ...
        }
      }
    },
    [lang_code_2]: {
      title: lang_2_title,
    }
  }
  """
  context = f"{doctype}:"

  translations = frappe.db.sql("""
  SELECT
    t.language,
    t.source_text,
    t.context,
    t.translated_text
  FROM `tabTranslation` t
  WHERE
    t.context LIKE %(context)s
  """, {
      "context": f"{context}%"
  }, as_dict=1)

  tr_dict = frappe._dict()

  if not len(translations):
    return tr_dict

  doc = frappe.get_cached_doc(doctype, name)
  value_fieldname_dict = None

  def get_value_fieldname_dict():
    nonlocal value_fieldname_dict
    if value_fieldname_dict is not None:
      return value_fieldname_dict

    d = frappe._dict()
    for fieldname in frappe.get_meta(doctype).get_valid_columns():
      v = doc.get(fieldname)
      if not v:
        continue

      if v not in d:
        d[v] = []

      d[v].append(fieldname)

    value_fieldname_dict = d
    return value_fieldname_dict

  for t in translations:
    if t.language not in tr_dict:
      tr_dict[t.language] = frappe._dict()

    ctx = t.context.split(":")
    if len(ctx) == 3 and ctx[1] == name:
      # Docfield translation
      # doctype:name:docfield
      fieldname = t.context.split(":")[2]
      if t.source_text == "*" or doc.get(fieldname) == t.source_text:
        tr_dict[t.language][fieldname] = t.translated_text

    elif len(ctx) == 2 and ctx[1] != name:
      # Select DocField
      select_df = ctx[1]
      if select_df not in [x.fieldname for x in frappe.get_meta(doctype).get_select_fields()]:
        continue

      select_tr = tr_dict[t.language].setdefault(
          select_df, frappe._dict(value=None, values=frappe._dict()))
      select_tr.get("values")[t.source_text] = t.translated_text
      if doc.get(select_df) == t.source_text:
        select_tr.value = t.translated_text

    elif len(ctx) == 2:
      # Document Translation
      # doctype:name
      d = get_value_fieldname_dict()
      if t.source_text in d:
        for fieldname in d[t.source_text]:
          if tr_dict[t.language].get(fieldname, None):
            continue
          tr_dict[t.language][fieldname] = t.translated_text

  return tr_dict
