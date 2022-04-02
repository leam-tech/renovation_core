from pymysql import Connection
import pymysqlpool
from asyncer import asyncify as _asyncify

import frappe
import sys
import anyio
from typing import Callable, Optional, Awaitable, TypeVar
if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from frappe.database import get_db
from frappe.database.database import Database

pool = None


def obtain_pool_connection(db: Database):
    """
    Frappe's Database calls connect() only inside frappe.db.sql method, like lazy-connection
    Here, we are eager. But still, its obtained from Pool - so its cool
    """
    global pool
    if not pool:
        pool = DBPool()

    conn = pool.get_connection()
    conn.select_db(frappe.conf.db_name)
    db._conn = conn
    db.cur_db_name = frappe.conf.db_name
    db._cursor = conn.cursor()
    frappe.local.rollback_observers = []

    def _close():
        """Close database connection."""

        global pool
        if db._conn:
            pool.release_connection(db._conn)
            db._cursor = None
            db._conn = None

    db.close = _close


def thread_safe_db(db):
    import threading

    def lock_fn(fn):
        lock = threading.RLock()

        def inner(*args, **kwargs):
            with lock:
                return fn(*args, **kwargs)

        return inner

    db.sql = lock_fn(db.sql)


T_Retval = TypeVar("T_Retval")
T_ParamSpec = ParamSpec("T_ParamSpec")
T = TypeVar("T")


def asyncify(
    function: Callable[T_ParamSpec, T_Retval],
    *,
    cancellable: bool = False,
    limiter: Optional[anyio.CapacityLimiter] = None,
    db_read_only=False,
) -> Callable[T_ParamSpec, Awaitable[T_Retval]]:
    # db_read_only = True
    def wrap_db(fn):
        def inner(*args, **kwargs):
            if db_read_only:
                frappe.local.db = get_db()
                obtain_pool_connection(frappe.local.db)
            try:
                val = fn(*args, **kwargs)
            finally:
                if db_read_only:
                    frappe.local.db.close()

            return val

        return inner

    return _asyncify(function=wrap_db(function), cancellable=cancellable, limiter=limiter)


class DBPool:
    def __init__(self):
        self.db_host = frappe.conf.db_host or "127.0.0.1"
        self.db_port = frappe.conf.db_port or ""
        self.db_user = frappe.conf.db_root_user
        self.db_pwd = frappe.conf.db_root_pwd
        self.pool = pymysqlpool.ConnectionPool(
            size=20,
            pre_create=True,
            host=self.db_host,
            port=self.db_port,
            database="",
            user=self.db_user,
            password=self.db_pwd,
        )

    def get_connection(self) -> Connection:
        conn = self.pool.get_connection(
            timeout=10,
            retry_num=2
        )
        return conn

    def release_connection(self, conn: Connection) -> None:
        if not hasattr(conn, "_pool"):
            conn._pool = self.pool
        self.pool.put_connection(conn)
