import os
from typing import Generator
import graphql
from graphql import GraphQLError, parse, GraphQLSyntaxError

import renovation
from .http import get_masked_variables, get_operation_name


async def graphql_resolver(body: dict):
    graphql_request = renovation.parse_json(body)
    query = graphql_request.query
    variables = graphql_request.variables
    operation_name = graphql_request.operationName
    output = await execute(query, variables, operation_name)
    if len(output.get("errors", [])):
        await log_error(query, variables, operation_name, output)
        errors = []
        for err in output.errors:
            if isinstance(err, GraphQLError):
                err = err.formatted
            errors.append(err)
        output.errors = errors

    return output


async def execute(query=None, variables=None, operation_name=None):
    result = await graphql.graphql(
        # is_awaitable=is_awaitable,
        schema=get_schema(),
        source=query,
        variable_values=variables,
        operation_name=operation_name,
        middleware=[renovation.get_attr(cmd)
                    for cmd in renovation.get_hooks("graphql_middlewares")],
        context_value=renovation._dict()
    )
    output = renovation._dict()
    for k in ("data", "errors"):
        if not getattr(result, k, None):
            continue
        output[k] = getattr(result, k)
    return output


async def log_error(query, variables, operation_name, output):
    import traceback as tb
    import frappe
    from asyncer import asyncify

    tracebacks = []
    for idx, err in enumerate(output.errors):
        if not isinstance(err, GraphQLError):
            continue

        exc = err.original_error
        if not exc:
            continue
        tracebacks.append(
            f"GQLError #{idx}\n"
            + f"Http Status Code: {getattr(exc, 'http_status_code', 500)}\n"
            + f"{str(err)}\n\n"
            + f"{''.join(tb.format_exception(exc, exc, exc.__traceback__))}"
        )

    tracebacks.append(f"Frappe Traceback: \n{renovation.get_traceback()}")

    tracebacks = "\n==========================================\n".join(tracebacks)
    if renovation.local.conf.get("developer_mode"):
        print(tracebacks)

    variables = get_masked_variables(query=query, variables=variables)
    operation_name = get_operation_name(query=query, operation_name=operation_name)

    error_log = frappe.new_doc("Error Log")
    error_log.method = f"GraphQL Error: {operation_name}"
    error_log.error = f"""
OperationName: {operation_name}

Query:
{query}

Variables:
{variables}

Traceback:
{tracebacks}
    """
    await asyncify(error_log.insert)(ignore_permissions=True)


graphql_schemas = {}


def get_schema():
    global graphql_schemas

    if renovation.local.site in graphql_schemas:
        return graphql_schemas.get(renovation.local.site)

    schema = graphql.build_schema(get_typedefs())
    execute_schema_processors(schema=schema)

    graphql_schemas[renovation.local.site] = schema
    return schema


def get_typedefs():
    schema = """
    type Query {
        ping: String
    }

    type Mutation {
        ping: String
    }
    """
    for dir in renovation.get_hooks("graphql_sdl_dir"):
        """
        graphql_sdl_dir = "pms_app/graphql/types"

        The first part of path signifies a python module
        """
        dir = dir.lstrip("/")
        _dir = os.path.join(
            os.path.dirname(renovation.get_module(dir.split("/")[0]).__file__),
            "/".join(dir.split("/")[1:])
        )

        schema += f"\n\n\n# {dir}\n\n"
        schema += load_schema_from_path(_dir)

    return schema


def load_schema_from_path(path: str) -> str:
    if os.path.isdir(path):
        schema_list = [read_graphql_file(f) for f in
                       sorted(walk_graphql_files(path))]
        return "\n".join(schema_list)
    return read_graphql_file(os.path.abspath(path))


def execute_schema_processors(schema):
    for cmd in renovation.get_hooks("graphql_schema_processors"):
        renovation.get_attr(cmd)(schema=schema)


def walk_graphql_files(path: str) -> Generator[str, None, None]:
    extension = ".graphql"
    for dirpath, _, files in os.walk(path):
        for name in files:
            if extension and name.lower().endswith(extension):
                yield os.path.join(dirpath, name)


def read_graphql_file(path: str) -> str:
    with open(path, "r") as graphql_file:
        schema = graphql_file.read()
    try:
        parse(schema)
    except GraphQLSyntaxError as e:
        raise GraphQLFileSyntaxError(path, str(e)) from e
    return schema


class GraphQLFileSyntaxError(Exception):
    def __init__(self, schema_file, message) -> None:
        super().__init__()
        self.message = self.format_message(schema_file, message)

    def format_message(self, schema_file, message):
        return f"Could not load {schema_file}:\n{message}"

    def __str__(self):
        return self.message
