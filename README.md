## Renovation Frappe

Renovation Frappe Framework

## Why ?
- Provide better performance with ASGI & FastAPI
- Have project code completely independent of any third-party framework

## Features
- FastAPI will take over things on the API side of things
- Full support for existing frappe-cms & endpoints out of the box
- DocType creation, their migration & patches are still handled by frappe
- All READ operations on the DB will be driven by async-db-drivers

## Guides
- [Setting Up](./docs/setting-up.md)
- [Make your new app](./docs/new-app.md)
- [Playing with DocTypes](./docs/doctypes.md)
- FastAPI Endpoints in your app
- [Setting up Multi-Tenancy](./docs/multi-tenancy.md)
- [Multi Threading (asyncer) and DB Connection](./docs/db-multithreaded.md)

#### License

MIT