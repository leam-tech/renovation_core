import frappe


def init_site():
  print("Initializing site for core-ts tests")
  # Lets check if setup_complete, else lets do it first
  if not frappe.db.get_value('System Settings', 'System Settings', 'setup_complete'):
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
    setup_complete({
        "language": "English", "country": "United Arab Emirates", "timezone": "Asia/Dubai", "currency": "AED", "full_name": "Example Admin",
        "email": "admin@example.com", "password": "leamadmin"
    })

  create_users()
  create_dashboards()
  create_reports()
  print("Done!")
  print("NB: Please create a secondary site for ENV: CORE_TS_HOST_URL_SECONDARY")


def create_reports():
  print("Creating Reports Fixtures")

  if not frappe.db.exists("Report", "TEST"):
    frappe.get_doc(frappe._dict(
        doctype="Report",
        report_name="TEST",
        report_type="Report Builder",
        ref_doctype="Note",
        disabled=0,
        is_standard="No",
        json="{}"
    )).insert()

  if not frappe.db.exists("Renovation Report", "TEST"):
    frappe.get_doc(frappe._dict(
        doctype="Renovation Report",
        report="TEST"
    )).insert()


def create_dashboards():
  print("Creating dashboard fixtures")

  if not frappe.db.exists("Renovation Dashboard", "TEST"):
    frappe.get_doc(frappe._dict(
        doctype="Renovation Dashboard",
        title="TEST",
        type="lines",
        exc_type="cmd",
        is_standard="No",
        roles=[{"role": "All"}],
    )).insert()

  # make layout
  if not frappe.db.exists("Renovation Dashboard Layout", "TEST"):
    frappe.get_doc(frappe._dict(
        doctype="Renovation Dashboard Layout",
        title="TEST",
        enabled=1,
        can_resize_items=1,
        can_rearrange_items=1,
        roles=[{"role": "All"}],
        dashboards=[{
            "dashboard": "TEST",
            "width": 3,
            "height": 2
        }]
    )).insert()


def create_users():
  print("Setting up users")
  # Set admin email
  frappe.db.set_value("User", "Administrator", "email", "admin@example.com")

  # create user
  if not frappe.db.exists("User", "test@test.com"):
    frappe.get_doc(frappe._dict(
        doctype="User",
        email="test@test.com",
        new_password="test@test",
        first_name="Test User",
        quick_login_pin="1234",
        send_welcome_email=0
    )).insert()
