from renovation.utils.doctype import (
    on_doctype_update as _on_doctype_update,
    on_custom_field_update as _on_custom_field_update)


def on_update(*args, **kwargs):
    return _on_doctype_update(*args, **kwargs)


def on_custom_field_update(*args, **kwargs):
    return _on_custom_field_update(*args, **kwargs)
