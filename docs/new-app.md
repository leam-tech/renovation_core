# Make a New App
When working with Frappe, you will need a mirroring frappe-app for each of your renovation-app if it involves DB-Models / DocTypes.

Suppose you want to make a new app -- `test_app`, we will need two python apps.
- A frappe app
    ```
    $ bench new-app test_app_frappe
    ```
- A normal pip package -- `test_app`. There is no command to scaffold one for you (yet).

Now, two link the both of these, you have to specify `renovation_app = "test_app"` in `test_app_frappe`'s hooks.py