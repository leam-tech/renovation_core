import os


def get_sites(bench_path='..'):
  # cwd will be sites
  sites_dir = os.path.join(bench_path, "sites")
  sites = [site for site in os.listdir(sites_dir)
           if os.path.isdir(os.path.join(sites_dir, site)) and site not in ('assets',)]
  return sites


def get_bench_name(bench_path=".."):
  return os.path.basename(os.path.abspath(bench_path))
