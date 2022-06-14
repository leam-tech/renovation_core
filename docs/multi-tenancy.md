# Multi Tenancy Setup

A single uvicorn process can serve multiple bench sites.

- To Turn `OFF` Multi Tenancy

  Specify `SITE_NAME` environment variable to the site you would like to serve always

- To Turn `ON` Multi Tenancy

  - Unset `SITE_NAME` environment variable
  - Set `SAMPLE_SITE` environment variable to load doctype info

### Misc

FastAPI-Routes are not properly multi tenanted. This is assuming that all sites in the bench will share the same set of installed-apps.
eg. All sites in pms-clients-bench will have same set of apps and routes

Hence, provide `SAMPLE_SITE` as one of the sites in bench for reading routes info. This could be improved in the future with `@renovation.api` decorator
