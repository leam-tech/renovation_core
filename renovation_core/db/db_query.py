import ast
import json

import frappe
from frappe.model.db_query import DatabaseQuery
from six import string_types
from frappe import _
import copy


class UpdatedDBQuery(DatabaseQuery):
  def execute(self, query=None, fields=None, filters=None, or_filters=None,
              docstatus=None, group_by=None, order_by=None, limit_start=False,
              limit_page_length=None, as_list=False, with_childnames=False, debug=False,
              ignore_permissions=False, user=None, with_comment_count=False,
              join='left join', distinct=False, start=None, page_length=None, limit=None,
              ignore_ifnull=False, save_user_settings=False, save_user_settings_fields=False,
              update=None, add_total_row=None, user_settings=None, return_query=False, join_relation=None,
              with_link_fields=None):
    """Join Relation should be like this format:
    {
        "Child DocType": {
            "parent_doctype": "Name of Parent Doctype or None",
            "parent_field": "parent file like parent",
            "main_field": "Name of Child Field like name",
            "join": "like left join"
        }
    }
    """
    self.join_relation = {}
    if join_relation:
      if isinstance(join_relation, string_types):
        self.join_relation = json.loads(join_relation)
      else:
        self.join_relation = join_relation

    self.with_link_fields = []
    if with_link_fields:
      if isinstance(with_link_fields, string_types):
        self.with_link_fields = ast.literal_eval(
            with_link_fields) if with_link_fields.startswith('[') else [with_link_fields]
      else:
        self.with_link_fields = with_link_fields
    _d = super(UpdatedDBQuery, self).execute(query=query, fields=fields, filters=filters, or_filters=or_filters,
                                             docstatus=docstatus, group_by=group_by, order_by=order_by,
                                             limit_start=limit_start,
                                             limit_page_length=limit_page_length, as_list=as_list,
                                             with_childnames=with_childnames, debug=debug,
                                             ignore_permissions=ignore_permissions, user=user,
                                             with_comment_count=with_comment_count,
                                             join=join, distinct=distinct, start=start, page_length=page_length,
                                             limit=limit,
                                             ignore_ifnull=ignore_ifnull, save_user_settings=save_user_settings,
                                             save_user_settings_fields=save_user_settings_fields,
                                             update=update, add_total_row=add_total_row, user_settings=user_settings,
                                             return_query=return_query)
    if not self.as_list and self.with_link_fields:
      _d = self.get_with_link_fields(_d)
    # Translate
    if not self.as_list and frappe.local.lang != 'en':
      _d = update_transalte(self.doctype, _d)
    return _d

  def get_with_link_fields(self, data):
    self.meta = frappe.get_meta(self.doctype)
    _lilnk_dict = frappe._dict()
    _docs = frappe._dict()
    for d in data or []:
      for i in self.with_link_fields:
        if d.get(i):
          opt = self.meta.get_options(i) if self.meta.get_field(i).fieldtype=="Link" else d.get(self.meta.get_options(i))
          key = '{}:{}'.format(i, opt)
          _lilnk_dict.setdefault(key, []).append(d.get(i))
    for l in _lilnk_dict:
      field, options = l.split(':')
      if not (self.meta.has_field(field) and options):
        continue
      _d = frappe.db.sql('''select * from `tab{}` where name in ('{}')'''.format(
          options, "', '".join(_lilnk_dict[l])), as_dict=True)
      for d in _d:
        _docs[d.name] = update_transalte(options, d) if frappe.local.lang != 'en' else d
    for d in data or []:
      for i in self.with_link_fields:
        if d.get(i):
          d['{}_doc'.format(i)] = _docs.get(d.get(i))
    return data

  def prepare_args(self):
    args = super(UpdatedDBQuery, self).prepare_args()
    # query dict
    args.tables = self.tables[0]
    # left join parent, child tables
    for child in self.tables[1:]:
      join_rel = self.join_relation.get(child, {})
      args.tables += " {join} {child} on ({child}.{parent_field} = {main}.{main_field})".format(
          join=join_rel.get('join', self.join),
          child=child, parent_field=join_rel.get(
              'parent_field', 'parent'),
          main=join_rel.get('parent_dotype', self.tables[0]), main_field=join_rel.get('main_field', 'name'))
    return args


@frappe.whitelist()
def get_list(doctype, *args, **kwargs):
  '''wrapper for DatabaseQuery'''
  kwargs.pop('cmd', None)
  return UpdatedDBQuery(doctype).execute(None, *args, **kwargs)


def update_transalte(doctype, data):
  if not isinstance(data, list):
    return data
  translateable_fields = frappe.get_meta(doctype).get_translatable_fields()
  for d in data:
    if not isinstance(d, dict):
      continue
    orld_d = copy.deepcopy(d)
    for f in orld_d:
      if f not in translateable_fields:
        continue
      d[f'{f}_en'] = d[f]
      d[f] = _(d[f])
  return data
