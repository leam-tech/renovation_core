import frappe
from frappe.model.db_query import DatabaseQuery
from frappe.model.meta import is_single
from frappe.client import get_value


def __check_read_renovation_translation_tool_perm():
    doc = frappe.get_doc("Page", "renovation_translation_tool")
    if not doc.is_permitted():
        frappe.throw(
            frappe._("You don't have access to page Renovation Translation Tool."),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_translatable_docfields(doctype):
    __check_read_renovation_translation_tool_perm()
    doctype_meta = frappe.get_meta(doctype)
    translatable_docfields = doctype_meta.get_translatable_fields()
    translatable_docfields_list = [{"label": frappe._(d), "value": d} for d in translatable_docfields]
    return {
        "docfields": sorted(translatable_docfields_list, key=lambda d: d['label'])
    }


def __formulate_possible_contexts(doctype=None, docname=None, fieldname=None, parenttype=None, parent=None):
    """
     Possible Contexts in Precedence Order:
      key:doctype:name:fieldname
      key:doctype:name
      key:parenttype:parent
      key:doctype:fieldname
      key:doctype
      key:parenttype
    """
    contexts = []
    if doctype and docname and fieldname:
        contexts.append(f'{doctype}:{docname}:{fieldname}')
    if doctype and docname:
        contexts.append(f'{doctype}:{docname}')
    if parenttype and parent:
        contexts.append(f'{parenttype}:{parent}')
    if doctype and fieldname:
        contexts.append(f'{doctype}:{fieldname}')
    if doctype:
        contexts.append(f'{doctype}')
    if parenttype:
        contexts.append(f'{parenttype}')
    return contexts


@frappe.whitelist()
def get_translations(language: str, doctype: str, docname: str = None, docfield: str = None):
    """
    Try and get all possible translations as seen in Translation doctype only..
    Arguments:
        language: [Required]
        doctype: [Required]
        docname: [Optional]
        docfield: [Optional]
    """
    __check_read_renovation_translation_tool_perm()
    if is_single(doctype):
        docname = doctype
    possible_contexts = __formulate_possible_contexts(doctype=doctype, fieldname=docfield, docname=docname)
    if frappe.is_table(doctype):
        possible_parenttypes_and_parents = frappe.get_all(doctype, fields="Distinct parent,parenttype",
                                                          filters=[["parenttype", "!=", ""], ['parent', '!=', '']])
        for p in possible_parenttypes_and_parents:
            possible_contexts.extend(
                __formulate_possible_contexts(parenttype=p.get("parenttype"), parent=p.get("parent")))
    filters = [["language", "=", language]]
    context_filters = [["context", "in", possible_contexts]]
    filters_conditions = []
    context_filters_conditions = []
    DatabaseQuery("Translation").build_filter_conditions(filters, filters_conditions, ignore_permissions=True)
    DatabaseQuery("Translation").build_filter_conditions(context_filters, context_filters_conditions,
                                                         ignore_permissions=True)
    filters_conditions = ' and '.join(filters_conditions)
    where_conditions = filters_conditions
    context_filters_conditions = ' or '.join(context_filters_conditions)

    if doctype and not docname and not docfield:
        context_filters_conditions += f" or context LIKE '{doctype}:%'"
    if doctype and docfield and not docname:
        context_filters_conditions += f" or (context LIKE '{doctype}:%' and context LIKE '%:{docfield}')"
    if doctype and docname and not docfield:
        context_filters_conditions += f" or context LIKE '{doctype}:{docname}%'"

    where_conditions += f" and ( {context_filters_conditions} )"

    sql = """
    SELECT  `tabTranslation`.name,
            #  extract doctype from context
            SUBSTRING_INDEX(context, ':', 1)  as 'document_type',
            #  extract docname from context
            CASE LENGTH(context) - LENGTH(REPLACE(context, ':', ''))
            WHEN 2 THEN SUBSTR(context, LOCATE(':', context) + 1,
                              LOCATE(':', SUBSTR(context, LOCATE(':', context) + 1), 1) - 1)
            WHEN 1 THEN SUBSTRING_INDEX(context, ':', -1)
            ELSE '' END     as 'docname', 
            #  extract docfield from context
            IF(LENGTH(context) - LENGTH(REPLACE(context, ':', '')) = 2, SUBSTRING_INDEX(context, ':', -1),'')  as 'docfield',
            #  extract value from context if docname and docfield are present
            IF(length(SUBSTRING_INDEX(context, ':', 1)) and length((SUBSTR(context, LOCATE(':', context) + 1,
                                                                      LOCATE(':', SUBSTR(context, LOCATE(':', context) + 1), 1) -
                                                                      1))) and
          length(IF(LENGTH(context) - LENGTH(REPLACE(context, ':', '')) = 2, SUBSTRING_INDEX(context, ':', -1),
                    '')),({select_condition}), '') as 'value', 
            source_text, translated_text , context
    from `tabTranslation`
    where {where_conditions}
    """.format(where_conditions=where_conditions,
               select_condition=(
                   "(SELECT `tab{doctype}`.{docfield} from `tab{doctype}` WHERE `tab{doctype}`.name ='{docname}')".format(
                       doctype=doctype, docfield=docfield, docname=docname) if not is_single(doctype) else """
                    (SELECT `tabSingles`.value
                      from `tabSingles`
                      WHERE `tabSingles`.doctype = '{doctype}'
                        and `tabSingles`.field = '{docfield}')
                   """.format(doctype=doctype, docfield=docfield)) if docfield else frappe.db.escape(""))
    translations = [{**translation,
                     'value': frappe.get_cached_value(translation.get("document_type"), translation.get("docname"),
                                                      translation.get("docfield")) if translation.get(
                         "document_type") and translation.get("docname") and translation.get(
                         "docfield") and (frappe.db.table_exists(translation.get("document_type")) or is_single(
                         translation.get("document_type"))) and frappe.db.exists(
                         translation.get("document_type"), translation.get("docname")) else translation.get("value")
                     } for translation in frappe.db.sql(sql, as_dict=1, debug=0)]
    return {
        "translations": translations
    }


@frappe.whitelist()
def get_value_from_doc_for_translation(doctype, docname, docfield):
    parent = frappe.get_value(doctype, docname, 'parenttype')
    return get_value(doctype, fieldname=docfield, filters=docname, parent=parent)
