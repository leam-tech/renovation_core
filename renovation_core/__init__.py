__version__ = '0.0.1'


from renovation.utils.app import load_renovation_app_info
try:
    load_renovation_app_info()
except BaseException:
    print("Failed load_renovation_app_info")
