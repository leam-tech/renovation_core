from starlette.requests import Request

import renovation

from . import graphql_resolver


async def asgi_gql_resolver(request: Request):
    query, variables, operation_name = await get_query(request)
    return await graphql_resolver(renovation._dict(
        query=query,
        variables=variables,
        operation_name=operation_name
    ))


async def get_query(request: Request):
    query = None
    variables = None
    operation_name = None

    content_type = request.headers.get("content-type") or ""
    if request.method == "GET":
        query = request.query_params.get("query")
        variables = request.query_params.get("variables")
        operation_name = request.query_params.get("operation_name")
    elif request.method != "POST":
        return query, variables, operation_name

    if "application/json" in content_type:
        graphql_request = renovation.parse_json(renovation.safe_decode(await request.body()))
        query = graphql_request.query
        variables = graphql_request.variables
        operation_name = graphql_request.operationName

    elif "multipart/form-data" in content_type:
        # Follows the spec here: https://github.com/jaydenseric/graphql-multipart-request-spec
        # This could be used for file uploads, single / multiple
        # https://www.starlette.io/requests/#request-files
        form = await request.form()
        renovation.local.request_form = form

        operations = renovation.parse_json(form.get("operations"))
        query = operations.get("query")
        variables = operations.get("variables")
        operation_name = operations.get("operationName")

        files_map = renovation.parse_json(form.get("map"))
        for file_key in files_map:
            file_instances = files_map[file_key]
            for file_instance in file_instances:
                path = file_instance.split(".")
                obj = operations
                while len(path) > 1:
                    obj = obj.get(path.pop(0), None)
                    if obj is None:
                        break

                if obj is not None:
                    obj[path.pop(0)] = file_key

    return query, variables, operation_name
