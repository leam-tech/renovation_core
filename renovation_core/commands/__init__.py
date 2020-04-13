import click

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

renovation.add_command(setup)
renovation.add_command(setup_nginx)
commands = [renovation]