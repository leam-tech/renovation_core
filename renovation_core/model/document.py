import frappe
from frappe.model.document import Document


class RenovationDocument(Document):
  def __init__(self, *args, **kwargs):
    """
    To get `extend_extra_fields`
    set thard args as True
            or add `add_extra_fields` property in kwargs
    """
    super(RenovationDocument, self).__init__(*args, **kwargs)

    if not hasattr(self, 'flags'):
      self.flags = frappe._dict()
    self.flags.from_as_dict = False
    if len(args) >= 3:
      self.flags.from_as_dict = args[2]
    if kwargs.get('add_extra_fields'):
      self.flags.from_as_dict = kwargs.get('add_extra_fields')

  def get_valid_dict(self, sanitize=True, convert_dates_to_str=False, ignore_nulls=False):
    self.extend_extra_fields()
    return super(RenovationDocument, self).get_valid_dict(sanitize=sanitize, convert_dates_to_str=convert_dates_to_str, ignore_nulls=ignore_nulls)

  def extend_extra_fields(self):
    if hasattr(self, 'extend_fields'):
      if self.get('_metaclass'):
        self.flags.from_as_dict = False
      if not hasattr(self, 'extend_fields_names'):
        self.extend_fields_names = [x.fieldname for x in self.extend_fields]
      if self.flags.get('from_as_dict'):
        self.meta._valid_columns += self.extend_fields_names
        self.meta.fields += self.extend_fields
      else:
        for f in self.extend_fields:
          while f.fieldname in self.meta._valid_columns:
            self.meta._valid_columns.remove(f.fieldname)
          while f in self.meta.fields:
            self.meta.fields.remove(f)
