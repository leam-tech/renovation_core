import os

import frappe
from PIL import Image
from frappe.utils import cint


def is_image_path(path):
  if not path:
    return
  exts = ["jpg", "jpeg", "png"]
  path = path.lower()
  for e in exts:
    if e in path:
      return True
  return False


def get_extension(filename):
  s = filename.rsplit('.', 1)
  return s[1] if len(s) > 1 else ''


"""
Changes
  /files/a.png -> ./test-site/public/files/a.png
  /private/files/a.png -> ./test-site/private/files/a.png
"""


def get_file_path(path):
  return frappe.get_site_path(
      (("" if "/private/" in path else "/public")
       + path).strip("/"))


def on_file_update(doc):
  if not is_image_path(doc.file_url):
    return

  # apply watermark first, thumbnail next
  if cint(frappe.get_value("Renovation Image Settings", "Renovation Image Settings", "auto_apply_wm")):
    apply_watermark(doc)

  if cint(frappe.get_value("Renovation Image Settings", "Renovation Image Settings", "auto_convert_thumbs")):
    generate_thumbnail(doc)


def after_file_delete(doc):
  # delete file from watermark_og_ folder
  og_folder = get_watermarks_og_folder_path()
  extn = get_extension(doc.file_url)
  og_file = os.path.join(og_folder, doc.name + '.' + extn)
  if os.path.exists(og_file):
    # delete
    os.remove(og_file)


# Thumbnails Section
def generate_thumbnail(doc):
  # private files fails to generate_thumbnail, File.get_local_image references Public folder
  if not is_image_path(doc.file_url) or doc.is_private:
    return
  thumb_width = cint(frappe.get_value(
      "Renovation Image Settings", "Renovation Image Settings", "thumb_width"))
  if not thumb_width:
    frappe.msgprint("Please define thumbnail width in Image Settings")
    thumb_width = 256
  im = Image.open(get_file_path(doc.file_url))
  width, height = im.size

  thumb_height = thumb_width * height / width
  doc.make_thumbnail(width=thumb_width, height=thumb_height)


def regenerate_all_thumbnails():
  for f in frappe.get_list("File"):
    doc = frappe.get_doc("File", f.name)
    generate_thumbnail(doc)

# Watermarks Section


def apply_watermark(doc):
  if not is_image_path(doc.file_url):
    return
  image_settings = frappe.get_doc(
      "Renovation Image Settings", "Renovation Image Settings")

  if not image_settings.wm_image:
    return  # No watermark

  if doc.file_url == image_settings.wm_image \
          or doc.attached_to_doctype == "Renovation Image Settings":
    return  # dont apply watermark on watermark :p

  if not os.path.exists(get_file_path(image_settings.wm_image)):
    return  # file not found

  og_folder = get_watermarks_og_folder_path()
  if not os.path.isdir(og_folder):
    os.makedirs(og_folder)

  extn = get_extension(doc.file_url)
  # check if og_folder has doc.name already
  # if not copy file_url there
  og_file = os.path.join(og_folder, doc.name + '.' + extn)
  if not os.path.exists(og_file):
    # copy file_url to og_folder
    im = Image.open(get_file_path(doc.file_url)).convert("RGBA")
    saveImage(im, og_file, extn)
  else:
    im = Image.open(og_file).convert("RGBA")

  wt_im = Image.open(get_file_path(image_settings.wm_image))
  wt_w, wt_h = wt_im.size
  width, height = im.size

  # scale watermark down according to size specified
  wm_p = image_settings.wm_percent / 100
  wt_size = (cint(width * wm_p), cint(wt_h * width * wm_p / wt_w))
  # resize using thumbnail
  wt_im.thumbnail(wt_size, Image.ANTIALIAS)
  wt_im = wt_im.convert("RGBA")
  wt_im_copy = wt_im.copy()

  # opacity
  # thresh = 200
  # fn = lambda x : 255 if x > thresh else 0
  # mask = wt_im.convert("L").point(fn, mode='1') # 8-bit per pixel
  # mask = mask.convert("L")
  # this will have the transparent part a bit dark
  wt_im.putalpha(cint(256 * image_settings.wm_opacity / 100))
  # wt_im.putalpha(mask)

  # wt_pos
  pos = image_settings.wm_position
  margin = width * image_settings.wm_margin_percent / 100
  # calculate lft and top seperately
  if "Left" in pos:
    lft = margin
  elif "Right" in pos:
    lft = width - wt_size[0] - margin
  else:
    lft = (width - wt_size[0]) // 2  # Center

  if "Top" in pos:
    top = margin
  elif "Bottom" in pos:
    top = height - wt_size[1] - margin
  else:
    top = (height - wt_size[1]) // 2

  # make wt same size
  wt_scaled = Image.new('RGBA', (width, height), (0, 0, 0, 0))
  wt_scaled.paste(wt_im, (cint(lft), cint(top)), mask=wt_im_copy)

  b = Image.new('RGBA', (width, height), (0, 0, 0, 0))
  b = Image.alpha_composite(b, im)
  b = Image.alpha_composite(b, wt_scaled)

  saveImage(b, get_file_path(doc.file_url), extn)


def reapply_all_watermarks():
  for f in frappe.get_list("File"):
    doc = frappe.get_doc("File", f.name)
    apply_watermark(doc)
    generate_thumbnail(doc)


def get_watermarks_og_folder_path():
  return frappe.get_site_path("wm_image_files")


def saveImage(im, filename, extn):
  if not extn or "png" not in extn:
    # overwriting im may update in calling fn ?
    im.convert("RGB").save(filename)
  else:
    im.save(filename)


@frappe.whitelist()
def get_attachments(doctype, name, only_images=False, ignore_permissions=False):
  from .files import get_attachments as get_attach
  return get_attach(doctype, name, only_images, ignore_permissions)


def get_thumbnail_url(dt, dn, df):
  """
  Fetches the thumbnail url (if it exists) of an image field given:

  dt: `str`
    The Doc-type it is defined on
  dn: `str`
    The name of Doc it is attached to
  df: `str`
    The field on the Doc it is attached to i.e: the "Attach" field
  """

  file_url = frappe.get_value(dt, dn, df)
  if not file_url:
    return

  if frappe.is_table(dt):
    dt, dn = frappe.get_value(dt, dn, ("parenttype", "parent"))

  thumbnail_url = get_thumbnail_url_by_docfield(dt, dn, df, file_url)
  if not thumbnail_url:
    thumbnail_url = get_thumbnail_url_by_file_url(file_url)

  return thumbnail_url


def get_thumbnail_url_by_docfield(dt, dn, df, file_url):
  '''Will try to find the thumbnail url by the field the image is attached to'''
  fields = ["thumbnail_url"]
  filters = {"attached_to_name": dn,
             "file_url": file_url,
             "attached_to_doctype": dt,
             "attached_to_field": df}
  files = frappe.get_all(
      "File",
      fields=fields,
      filters=filters
  )
  return files[0].get("thumbnail_url") if len(files) else None


def get_thumbnail_url_by_file_url(file_url):
  '''Will try to find a thumbnail url by file_url'''
  files = frappe.get_all(
      "File",
      fields=["thumbnail_url"],
      filters={"file_url": file_url,
               "thumbnail_url": ("!=", "")}
  )
  return files[0].get("thumbnail_url") if len(files) else None
