import click
import frappe
from frappe.commands import pass_context, get_site
from renovation_core.app import serve as _serve


@click.group()
def renovation():
  pass


@click.command("setup")
def setup():
  from renovation_core.install.benchconfig import update_config
  update_config()


@click.command("setup-nginx")
@click.option('--force', help='Yes to regeneration of nginx config file', default=False, is_flag=True)
def setup_nginx(force=False):
  from renovation_core.install.bench.nginx import setup_nginx as _setup_nginx
  _setup_nginx(force=force)


@click.command('serve')
@click.option('--port', default=8000)
@click.option('--profile', is_flag=True, default=False)
@click.option('--noreload', "no_reload", is_flag=True, default=False)
@click.option('--nothreading', "no_threading", is_flag=True, default=False)
@pass_context
def serve(context, port=None, profile=False, no_reload=False, no_threading=False, sites_path='.', site=None):
  "Start development web server"

  if not context.sites:
    site = None
  else:
    site = context.sites[0]

  _serve(port=port, profile=profile, no_reload=no_reload, no_threading=no_threading, site=site,
         sites_path='.')


@click.command('init-test-site')
@click.option('--tests-for', type=click.Choice(["core-py", "core-ts", "core-dart"], case_sensitive=True),
  prompt=True, help="Specify the test target based on which to initialize this site")
@click.option('--reinstall', is_flag=True, prompt=True, help="Reinstall this site before initializing for tests")
@pass_context
def init_test_site(context, tests_for, reinstall):
  """Initializes the current site for renovation-tests"""
  site = get_site(context)
  if reinstall:
    from frappe.commands.site import _reinstall
    _reinstall(site=site, yes=True)

  try:
    frappe.init(site=site)
    frappe.connect()
  
    if tests_for == "core-py":
      from renovation_core.tests import init_site
      init_site()
    elif tests_for == "core-ts":
      from renovation_core.tests.core_ts import init_site
      init_site()
    elif tests_for == "core-dart":
      from renovation_core.tests.core_dart import init_site
      init_site()

    frappe.db.commit()
  except:
    print(frappe.get_traceback())
  finally:
    frappe.destroy()


renovation.add_command(setup)
renovation.add_command(setup_nginx)
renovation.add_command(serve)
renovation.add_command(init_test_site)
commands = [renovation]
