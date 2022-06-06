import re
import ast
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")


# get version from __version__ variable in renovation/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('renovation/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name="renovation_core",
    version=version,
    description="Renovation Frappe Framework",
    author="Leam",
    author_email="fahimalizain@gmail.com",
    packages=find_packages(),
    package_dir={"": "./"},
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
