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
  context = f"{doctype}:{name}"

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

    if t.context.count(":") > 1:
      # Docfield translation
      fieldname = t.context.split(":")[2]
      if doc.get(fieldname) == t.source_text:
        tr_dict[t.language][fieldname] = t.translated_text
    else:
      # Document Translation
      d = get_value_fieldname_dict()
      if t.source_text in d:
        for fieldname in d[t.source_text]:
          if tr_dict[t.language].get(fieldname, None):
            continue
          tr_dict[t.language][fieldname] = t.translated_text

  return tr_dict
