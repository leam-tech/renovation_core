from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in renovation/__init__.py
from renovation import __version__ as version

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
