import renovation
from renovation.utils.doctype import (
    on_doctype_update as _on_doctype_update,
    on_custom_field_update as _on_custom_field_update)

model_generation_skip_flags = ["in_migrate", "in_install", "in_patch", "in_import",
                               "in_setup_wizard", "in_uninstall", ]


def _ignore_model_generation():
    return any(renovation.cint(getattr(renovation.local.flags, f, None)) for f in
               model_generation_skip_flags)


def on_update(*args, **kwargs):
    if _ignore_model_generation():
        return
    return _on_doctype_update(*args, **kwargs)


def on_custom_field_update(*args, **kwargs):
    if _ignore_model_generation():
        return
    return _on_custom_field_update(*args, **kwargs)
