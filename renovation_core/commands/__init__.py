import click
from frappe.commands import pass_context
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


renovation.add_command(setup)
renovation.add_command(setup_nginx)
renovation.add_command(serve)
commands = [renovation]
