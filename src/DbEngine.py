import os
import psycopg
from psycopg.rows import dict_row
import threading

def decode_val(val):
    if isinstance(val, (bytes, bytearray)):
        return val.decode('utf-8', errors='replace')
    return val

class DbEngine:
    def __init__(self, host, port, database, username, password, sslmode="prefer", db_type="postgresql", file_path="", charset=""):
        self.host = host
        self.port = int(port) if port else 0
        self.database = database
        self.username = username
        self.password = password
        self.sslmode = sslmode
        self.db_type = db_type.lower()
        self.file_path = file_path
        self.charset = charset
        self._local = threading.local()
        
        # Metadata Cache
        self._tables_cache = {}
        self._views_cache = {}
        self._funcs_cache = {}
        self._tables_detailed_cache = {}

    @property
    def _connection(self):
        if not hasattr(self._local, "connection"):
            return None
        return self._local.connection

    @_connection.setter
    def _connection(self, value):
        self._local.connection = value

    def connect(self):
        """Establish connection to the database."""
        if self._connection:
            if self.db_type == "postgresql":
                if not self._connection.closed:
                    return self._connection
            elif self.db_type == "mysql":
                if self._connection.open:
                    return self._connection
            elif self.db_type == "sqlite":
                try:
                    self._connection.execute("SELECT 1")
                    return self._connection
                except Exception:
                    self._connection = None
            
        if self.db_type == "postgresql":
            self._connection = psycopg.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.username,
                password=self.password,
                sslmode=self.sslmode,
                connect_timeout=5
            )
        elif self.db_type == "mysql":
            import pymysql
            conn_args = {
                "host": self.host,
                "port": self.port,
                "user": self.username,
                "password": self.password,
                "database": self.database if self.database else None,
                "connect_timeout": 5,
                "autocommit": True
            }
            if self.charset:
                conn_args["charset"] = self.charset
            self._connection = pymysql.connect(**conn_args)
        elif self.db_type == "sqlite":
            import sqlite3
            self._connection = sqlite3.connect(self.file_path)
            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection

    def close(self):
        """Close current connection."""
        if self._connection:
            if self.db_type == "postgresql":
                if not self._connection.closed:
                    self._connection.close()
            elif self.db_type == "mysql":
                if self._connection.open:
                    self._connection.close()
            elif self.db_type == "sqlite":
                try:
                    self._connection.close()
                except Exception:
                    pass
        self._connection = None

    def clear_cache(self):
        """Clear all metadata cache."""
        self._tables_cache.clear()
        self._views_cache.clear()
        self._funcs_cache.clear()
        self._tables_detailed_cache.clear()

    def _resolve_schema(self, schema):
        if self.db_type == "mysql":
            if schema in ("(default)", "public", "", None):
                return self.database
        elif self.db_type == "sqlite":
            return "main"
        return schema

    def _quote_ident(self, name):
        if self.db_type == "mysql":
            return f"`{name}`"
        return f'"{name}"'

    def quote_table_name(self, schema, table_name):
        if self.db_type == "sqlite":
            return f'"{table_name}"'
        resolved = self._resolve_schema(schema)
        return f"{self._quote_ident(resolved)}.{self._quote_ident(table_name)}"

    def translate_query(self, query):
        import re
        query_stripped = query.strip().rstrip(';').strip()
        
        # 1. Handle DESC / DESCRIBE
        match_desc = re.match(r'^(DESC|DESCRIBE)\s+(.+)$', query_stripped, re.IGNORECASE)
        if match_desc:
            table_name = match_desc.group(2).strip().strip('"').strip("'").strip('`')
            if self.db_type == "postgresql":
                if '.' in table_name:
                    parts = table_name.split('.')
                    qualified = f'"{parts[0]}"."{parts[1]}"'
                else:
                    qualified = f'"{table_name}"'
                return f"""
                SELECT 
                    a.attname AS "Column",
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS "Type",
                    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS "Nullable",
                    pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS "Default"
                FROM pg_catalog.pg_attribute a
                LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
                WHERE a.attrelid = '{qualified}'::regclass
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum;
                """
            elif self.db_type == "sqlite":
                return f'PRAGMA table_info("{table_name}");'
            elif self.db_type == "mysql":
                return query
                
        # 2. Handle SHOW TABLES, SHOW DATABASES, SHOW SCHEMAS, SHOW VIEWS
        match_show = re.match(r'^SHOW\s+(TABLES|DATABASES|SCHEMAS|VIEWS)$', query_stripped, re.IGNORECASE)
        if match_show:
            show_type = match_show.group(1).upper()
            if self.db_type == "postgresql":
                if show_type == "TABLES":
                    return "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;"
                elif show_type == "DATABASES":
                    return "SELECT datname FROM pg_database WHERE datistemplate = false AND datallowconn = true ORDER BY datname;"
                elif show_type == "SCHEMAS":
                    return "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema' ORDER BY schema_name;"
                elif show_type == "VIEWS":
                    return "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'VIEW' ORDER BY table_name;"
            elif self.db_type == "sqlite":
                if show_type == "TABLES":
                    return "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
                elif show_type == "DATABASES":
                    return "SELECT 'main' AS database;"
                elif show_type == "SCHEMAS":
                    return "SELECT 'main' AS schema;"
                elif show_type == "VIEWS":
                    return "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;"
            elif self.db_type == "mysql":
                return query

        return query

    def execute_query(self, query, params=None, fetch_results=True):
        """
        Execute an arbitrary SQL query.
        Returns:
            columns: list of column names (or empty list if no results)
            rows: list of tuples (or empty list)
            message: string with rowcount or status message
        """
        query = self.translate_query(query)
        conn = self.connect()
        if self.db_type == "postgresql":
            conn.autocommit = True
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                message = f"Query executed successfully. Row count: {cursor.rowcount}"
                if fetch_results and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return columns, rows, message
                else:
                    return [], [], message
            except Exception as e:
                raise e
            finally:
                cursor.close()
        elif self.db_type == "mysql":
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                message = f"Query executed successfully. Row count: {cursor.rowcount}"
                if fetch_results and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return columns, rows, message
                else:
                    return [], [], message
            except Exception as e:
                raise e
            finally:
                cursor.close()
        elif self.db_type == "sqlite":
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                message = f"Query executed successfully. Row count: {cursor.rowcount}"
                if fetch_results and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return columns, rows, message
                else:
                    return [], [], message
            except Exception as e:
                raise e
            finally:
                cursor.close()

    def _sqlite_execute(self, query, params=None):
        """Helper for SQLite queries using ? placeholders."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return columns, rows
            return [], []
        finally:
            cursor.close()

    def get_databases(self):
        """Fetch list of all databases on the server."""
        if self.db_type == "sqlite":
            # SQLite has a single database — use filename as name
            return [os.path.basename(self.file_path)]
        elif self.db_type == "mysql":
            _, rows, _ = self.execute_query("SHOW DATABASES;")
            return [decode_val(row[0]) for row in rows]
        else:
            query = "SELECT datname FROM pg_database WHERE datistemplate = false AND datallowconn = true ORDER BY datname;"
            _, rows, _ = self.execute_query(query)
            return [decode_val(row[0]) for row in rows]

    def get_schemas(self):
        """Fetch list of schemas in the current database."""
        if self.db_type == "sqlite":
            return ["main"]
        elif self.db_type == "mysql":
            return ["(default)"]
        else:
            query = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema' 
            ORDER BY schema_name;
            """
            _, rows, _ = self.execute_query(query)
            return [decode_val(row[0]) for row in rows]

    def get_tables(self, schema="public"):
        """Fetch list of tables in a schema."""
        resolved = self._resolve_schema(schema)
        if resolved in self._tables_cache:
            return self._tables_cache[resolved]
        
        if self.db_type == "sqlite":
            _, rows = self._sqlite_execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [decode_val(row[0]) for row in rows]
        elif self.db_type == "mysql":
            query = f"SHOW FULL TABLES FROM `{resolved}` WHERE Table_type = 'BASE TABLE';"
            _, rows, _ = self.execute_query(query)
            tables = [decode_val(row[0]) for row in rows]
        else:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """
            _, rows, _ = self.execute_query(query, (resolved,))
            tables = [decode_val(row[0]) for row in rows]
        
        self._tables_cache[resolved] = tables
        return tables

    def _format_size(self, bytes_val):
        if bytes_val is None:
            return "0 Bytes"
        try:
            bytes_val = float(bytes_val)
        except Exception:
            return "0 Bytes"
            
        for unit in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                if unit == 'Bytes':
                    return f"{int(bytes_val)} {unit}"
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"

    def get_tables_detailed(self, schema="public"):
        """Fetch detailed information for tables (name, row_count, size)."""
        resolved = self._resolve_schema(schema)
        if resolved in self._tables_detailed_cache:
            return self._tables_detailed_cache[resolved]
        
        if self.db_type == "sqlite":
            tables = self.get_tables(schema)
            result = []
            # Get total file size once
            try:
                file_size = os.path.getsize(self.file_path)
            except Exception:
                file_size = 0
            
            for t in tables:
                # Get row count per table
                try:
                    _, count_rows = self._sqlite_execute(f'SELECT COUNT(*) FROM "{t}"')
                    row_count = int(count_rows[0][0])
                except Exception:
                    row_count = 0
                result.append({
                    "name": decode_val(t),
                    "rows": f"{row_count:,}",
                    "size": "-"
                })
            
            # Show file size on first table if any
            if result:
                result[0]["size"] = self._format_size(file_size)
            
            self._tables_detailed_cache[resolved] = result
            return result
        elif self.db_type == "mysql":
            query = """
            SELECT 
                table_name,
                COALESCE(table_rows, 0) AS row_count,
                COALESCE(data_length + index_length, 0) AS total_size
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """
            try:
                try:
                    self.execute_query("SET SESSION innodb_stats_on_metadata = 0;", fetch_results=False)
                except Exception:
                    pass
                _, rows, _ = self.execute_query(query, (resolved,))
                result = []
                for r in rows:
                    name = decode_val(r[0])
                    row_count = int(r[1])
                    size_bytes = r[2]
                    result.append({
                        "name": name,
                        "rows": f"{row_count:,}",
                        "size": self._format_size(size_bytes)
                    })
                self._tables_detailed_cache[resolved] = result
                return result
            except Exception:
                return []
        else:
            # PostgreSQL
            query = """
            SELECT 
                c.relname AS table_name,
                CASE WHEN c.reltuples < 0 THEN 0 ELSE c.reltuples::bigint END AS row_count,
                pg_total_relation_size(c.oid) AS total_size
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relkind = 'r'
            ORDER BY c.relname;
            """
            try:
                _, rows, _ = self.execute_query(query, (resolved,))
                result = []
                for r in rows:
                    name = decode_val(r[0])
                    row_count = int(r[1])
                    size_bytes = r[2]
                    result.append({
                        "name": name,
                        "rows": f"{row_count:,}",
                        "size": self._format_size(size_bytes)
                    })
                self._tables_detailed_cache[resolved] = result
                return result
            except Exception:
                return []

    def get_views(self, schema="public"):
        """Fetch list of views in a schema."""
        resolved = self._resolve_schema(schema)
        if resolved in self._views_cache:
            return self._views_cache[resolved]
        
        if self.db_type == "sqlite":
            _, rows = self._sqlite_execute(
                "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
            )
            views = [decode_val(row[0]) for row in rows]
        elif self.db_type == "mysql":
            query = f"SHOW FULL TABLES FROM `{resolved}` WHERE Table_type = 'VIEW';"
            _, rows, _ = self.execute_query(query)
            views = [decode_val(row[0]) for row in rows]
        else:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_type = 'VIEW'
            ORDER BY table_name;
            """
            _, rows, _ = self.execute_query(query, (resolved,))
            views = [decode_val(row[0]) for row in rows]
        
        self._views_cache[resolved] = views
        return views

    def get_columns(self, schema, table_name):
        """
        Fetch columns of a table.
        Returns list of dicts: [{'name': colname, 'type': coltype, 'nullable': True/False, 'default': default}]
        """
        if self.db_type == "sqlite":
            _, rows = self._sqlite_execute(f'PRAGMA table_info("{table_name}")')
            cols = []
            for row in rows:
                # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
                cols.append({
                    "name": row[1],
                    "type": row[2] or "TEXT",
                    "nullable": not bool(row[3]),
                    "default": row[4]
                })
            return cols
        
        resolved = self._resolve_schema(schema)
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        _, rows, _ = self.execute_query(query, (resolved, table_name))
        cols = []
        for row in rows:
            cols.append({
                "name": decode_val(row[0]),
                "type": decode_val(row[1]),
                "nullable": decode_val(row[2]) == "YES" or decode_val(row[2]) == "yes",
                "default": decode_val(row[3])
            })
        return cols

    def get_columns_detailed(self, schema, table_name):
        """
        Fetch detailed column info for the Table Designer.
        Returns list of dicts with: name, column_type, nullable, default, key, extra, comment
        """
        if self.db_type == "sqlite":
            _, rows = self._sqlite_execute(f'PRAGMA table_info("{table_name}")')
            cols = []
            for row in rows:
                cols.append({
                    "name": decode_val(row[1]),
                    "column_type": decode_val(row[2]) or "TEXT",
                    "nullable": not bool(row[3]),
                    "default": decode_val(row[4]),
                    "key": "PRI" if row[5] else "",
                    "extra": "",
                    "comment": ""
                })
            return cols

        resolved = self._resolve_schema(schema)
        if self.db_type == "mysql":
            query = """
            SELECT column_name, column_type, is_nullable, column_default,
                   column_key, extra, column_comment
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
            """
            _, rows, _ = self.execute_query(query, (resolved, table_name))
            cols = []
            for row in rows:
                cols.append({
                    "name": decode_val(row[0]),
                    "column_type": decode_val(row[1]),
                    "nullable": decode_val(row[2]) in ("YES", "yes"),
                    "default": decode_val(row[3]),
                    "key": decode_val(row[4]) or "",
                    "extra": decode_val(row[5]) or "",
                    "comment": decode_val(row[6]) or ""
                })
            return cols
        else:
            # PostgreSQL
            query = """
            SELECT
                a.attname AS column_name,
                format_type(a.atttypid, a.atttypmod) AS column_type,
                NOT a.attnotnull AS nullable,
                pg_get_expr(ad.adbin, ad.adrelid) AS column_default,
                CASE WHEN pk.contype = 'p' THEN 'PRI' ELSE '' END AS key,
                CASE WHEN pg_get_expr(ad.adbin, ad.adrelid) LIKE 'nextval%%' THEN 'auto_increment' ELSE '' END AS extra,
                COALESCE(col_description(a.attrelid, a.attnum), '') AS comment
            FROM pg_attribute a
            LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
            LEFT JOIN LATERAL (
                SELECT c.contype FROM pg_constraint c
                WHERE c.conrelid = a.attrelid AND c.contype = 'p' AND a.attnum = ANY(c.conkey)
                LIMIT 1
            ) pk ON true
            WHERE a.attrelid = %s::regclass
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum;
            """
            qualified_tbl = f'"{resolved}"."{table_name}"'
            _, rows, _ = self.execute_query(query, (qualified_tbl,))
            cols = []
            for row in rows:
                cols.append({
                    "name": decode_val(row[0]),
                    "column_type": decode_val(row[1]),
                    "nullable": bool(row[2]),
                    "default": decode_val(row[3]),
                    "key": decode_val(row[4]) or "",
                    "extra": decode_val(row[5]) or "",
                    "comment": decode_val(row[6]) or ""
                })
            return cols

    def get_primary_keys(self, schema, table_name):
        """Fetch list of primary key columns for a table."""
        if self.db_type == "sqlite":
            _, rows = self._sqlite_execute(f'PRAGMA table_info("{table_name}")')
            pk_cols = []
            for row in rows:
                # row[5] is the pk flag (1-based index in composite PK, 0 if not PK)
                if row[5]:
                    pk_cols.append(decode_val(row[1]))
            return pk_cols
        
        resolved = self._resolve_schema(schema)
        if self.db_type == "mysql":
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s AND column_key = 'PRI';
            """
            _, rows, _ = self.execute_query(query, (resolved, table_name))
            return [decode_val(row[0]) for row in rows]
        else:
            query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s;
            """
            _, rows, _ = self.execute_query(query, (resolved, table_name))
            return [decode_val(row[0]) for row in rows]

    def update_row(self, schema, table_name, primary_keys_dict, updates_dict):
        """
        Dynamically construct and execute an UPDATE statement.
        """
        if not updates_dict:
            return
        
        if self.db_type == "sqlite":
            set_clauses = []
            params = []
            for col, val in updates_dict.items():
                set_clauses.append(f'"{col}" = ?')
                params.append(val)
            where_clauses = []
            for col, val in primary_keys_dict.items():
                where_clauses.append(f'"{col}" = ?')
                params.append(val)
            sql = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE {" AND ".join(where_clauses)}'
            self._sqlite_execute(sql, params)
            self.connect().commit()
            return
        
        resolved = self._resolve_schema(schema)
        q_schema = self._quote_ident(resolved)
        q_table = self._quote_ident(table_name)
        
        set_clauses = []
        params = []
        for col, val in updates_dict.items():
            set_clauses.append(f'{self._quote_ident(col)} = %s')
            params.append(val)
            
        where_clauses = []
        for col, val in primary_keys_dict.items():
            where_clauses.append(f'{self._quote_ident(col)} = %s')
            params.append(val)
            
        sql = f'UPDATE {q_schema}.{q_table} SET {", ".join(set_clauses)} WHERE {" AND ".join(where_clauses)}'
        self.execute_query(sql, params, fetch_results=False)

    def insert_row(self, schema, table_name, row_dict):
        """
        Dynamically construct and execute an INSERT statement.
        """
        if not row_dict:
            return
        
        if self.db_type == "sqlite":
            cols = list(row_dict.keys())
            vals = list(row_dict.values())
            col_placeholders = ", ".join([f'"{c}"' for c in cols])
            val_placeholders = ", ".join(["?"] * len(vals))
            sql = f'INSERT INTO "{table_name}" ({col_placeholders}) VALUES ({val_placeholders})'
            self._sqlite_execute(sql, vals)
            self.connect().commit()
            return
        
        resolved = self._resolve_schema(schema)
        q_schema = self._quote_ident(resolved)
        q_table = self._quote_ident(table_name)
        
        cols = list(row_dict.keys())
        vals = list(row_dict.values())
        
        col_placeholders = ", ".join([self._quote_ident(c) for c in cols])
        val_placeholders = ", ".join(["%s"] * len(vals))
        
        sql = f'INSERT INTO {q_schema}.{q_table} ({col_placeholders}) VALUES ({val_placeholders})'
        self.execute_query(sql, vals, fetch_results=False)

    def delete_row(self, schema, table_name, row_identifier_dict):
        """
        Dynamically construct and execute a DELETE statement.
        """
        if not row_identifier_dict:
            return
        
        if self.db_type == "sqlite":
            where_clauses = []
            params = []
            for col, val in row_identifier_dict.items():
                where_clauses.append(f'"{col}" = ?')
                params.append(val)
            sql = f'DELETE FROM "{table_name}" WHERE {" AND ".join(where_clauses)}'
            self._sqlite_execute(sql, params)
            self.connect().commit()
            return
            
        resolved = self._resolve_schema(schema)
        q_schema = self._quote_ident(resolved)
        q_table = self._quote_ident(table_name)
        
        where_clauses = []
        params = []
        for col, val in row_identifier_dict.items():
            where_clauses.append(f'{self._quote_ident(col)} = %s')
            params.append(val)
            
        sql = f'DELETE FROM {q_schema}.{q_table} WHERE {" AND ".join(where_clauses)}'
        self.execute_query(sql, params, fetch_results=False)

    def get_functions(self, schema="public"):
        """Fetch list of functions/procedures in a schema."""
        if self.db_type == "sqlite":
            # SQLite has no stored procedures/functions
            return []
        
        resolved = self._resolve_schema(schema)
        if resolved in self._funcs_cache:
            return self._funcs_cache[resolved]
        if self.db_type == "mysql":
            funcs = []
            try:
                _, rows, _ = self.execute_query(f"SHOW PROCEDURE STATUS WHERE Db = '{resolved}';")
                funcs.extend([decode_val(row[1]) for row in rows])
            except Exception:
                pass
            try:
                _, rows, _ = self.execute_query(f"SHOW FUNCTION STATUS WHERE Db = '{resolved}';")
                funcs.extend([decode_val(row[1]) for row in rows])
            except Exception:
                pass
            funcs.sort()
            self._funcs_cache[resolved] = funcs
            return funcs
        else:
            query = """
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = %s
            ORDER BY routine_name;
            """
            _, rows, _ = self.execute_query(query, (resolved,))
            funcs = [decode_val(row[0]) for row in rows]
            self._funcs_cache[resolved] = funcs
            return funcs

    def get_function_definition(self, schema, func_name):
        """Fetch full CREATE OR REPLACE FUNCTION SQL definition."""
        if self.db_type == "sqlite":
            return "-- SQLite does not support stored functions."
        
        resolved = self._resolve_schema(schema)
        if self.db_type == "mysql":
            query = """
            SELECT routine_type, routine_definition 
            FROM information_schema.routines 
            WHERE routine_schema = %s AND routine_name = %s;
            """
            try:
                _, rows, _ = self.execute_query(query, (resolved, func_name))
                if rows:
                    r_type, definition = rows[0]
                    r_type = decode_val(r_type)
                    definition = decode_val(definition)
                    return f"/* CREATE {r_type} {func_name} */\n{definition or ''}"
                return f"-- Definition for {resolved}.{func_name} could not be retrieved."
            except Exception:
                return f"-- Definition for {resolved}.{func_name} could not be retrieved."
        else:
            query = """
            SELECT pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = %s AND p.proname = %s;
            """
            try:
                _, rows, _ = self.execute_query(query, (resolved, func_name))
                return decode_val(rows[0][0]) if rows else ""
            except Exception:
                return f"-- Definition for {resolved}.{func_name} could not be retrieved."

    def get_table_definition(self, schema, table_name):
        if self.db_type == "sqlite":
            try:
                _, rows = self._sqlite_execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                if rows and rows[0][0]:
                    return rows[0][0] + ";"
                return f"-- Definition for {table_name} could not be retrieved."
            except Exception as e:
                return f"-- Definition for {table_name} could not be retrieved: {str(e)}"
        
        resolved = self._resolve_schema(schema)
        if self.db_type == "mysql":
            q_table = f"`{resolved}`.`{table_name}`"
            query = f"SHOW CREATE TABLE {q_table};"
            try:
                _, rows, _ = self.execute_query(query)
                if rows:
                    return decode_val(rows[0][1])
            except Exception as e:
                return f"-- Definition for {resolved}.{table_name} could not be retrieved: {str(e)}"
        else:
            # PostgreSQL advanced table def generator
            import re
            try:
                qualified_tbl = f'"{resolved}"."{table_name}"'

                # 1. Fetch columns via catalog
                col_query = """
                SELECT 
                    a.attname AS column_name,
                    t.typname AS type_name,
                    format_type(a.atttypid, a.atttypmod) AS formatted_type,
                    a.attnotnull,
                    pg_get_expr(ad.adbin, ad.adrelid) AS column_default,
                    c.collname AS collation_name,
                    n.nspname AS collation_schema
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
                LEFT JOIN pg_collation c ON a.attcollation = c.oid
                LEFT JOIN pg_namespace n ON c.collnamespace = n.oid
                WHERE a.attrelid = %s::regclass 
                  AND a.attnum > 0 
                  AND NOT a.attisdropped
                ORDER BY a.attnum;
                """
                _, col_rows, _ = self.execute_query(col_query, (qualified_tbl,))

                # 2. Fetch constraints (PK first, then Unique, then FK)
                const_query = """
                SELECT conname, pg_get_constraintdef(oid, true)
                FROM pg_constraint
                WHERE conrelid = %s::regclass AND contype IN ('p', 'u', 'f')
                ORDER BY CASE contype WHEN 'p' THEN 1 WHEN 'u' THEN 2 WHEN 'f' THEN 3 ELSE 4 END, conname;
                """
                const_rows = []
                try:
                    _, const_rows, _ = self.execute_query(const_query, (qualified_tbl,))
                except Exception:
                    pass
                const_names = {row[0] for row in const_rows}

                # 3. Fetch Owner
                owner_query = "SELECT tableowner FROM pg_tables WHERE schemaname = %s AND tablename = %s;"
                owner_rows = []
                try:
                    _, owner_rows, _ = self.execute_query(owner_query, (resolved, table_name))
                except Exception:
                    pass
                owner = owner_rows[0][0] if owner_rows else "postgres"

                # 4. Fetch Indexes
                idx_query = "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s ORDER BY indexname;"
                idx_rows = []
                try:
                    _, idx_rows, _ = self.execute_query(idx_query, (resolved, table_name))
                except Exception:
                    pass

                # Create type/columns mapping for index formatting
                table_columns = {row[0]: row[1] for row in col_rows}

                # Build DDL
                ddl = f'CREATE TABLE "{resolved}"."{table_name}" (\n'
                lines = []

                # Format Columns
                for col in col_rows:
                    name, dtype, formatted_type, attnotnull, default, coll_name, coll_schema = col
                    
                    # Determine target type representation
                    if dtype == 'varchar':
                        m = re.search(r'\((.*?)\)', formatted_type)
                        len_part = f"({m.group(1)})" if m else ""
                        col_type = f"varchar{len_part}"
                    elif dtype == 'bpchar':
                        m = re.search(r'\((.*?)\)', formatted_type)
                        len_part = f"({m.group(1)})" if m else ""
                        col_type = f"char{len_part}"
                    elif dtype == 'numeric':
                        col_type = formatted_type
                    elif dtype == 'timestamp':
                        m = re.search(r'\((.*?)\)', formatted_type)
                        len_part = f"({m.group(1)})" if m else ""
                        col_type = f"timestamp{len_part}"
                    elif dtype == 'timestamptz':
                        m = re.search(r'\((.*?)\)', formatted_type)
                        len_part = f"({m.group(1)})" if m else ""
                        col_type = f"timestamptz{len_part}"
                    elif dtype in ('int4', 'int8', 'int2', 'bool'):
                        col_type = dtype
                    else:
                        col_type = dtype

                    col_def = f'  "{name}" {col_type}'
                    
                    # Collation
                    if coll_name and coll_schema:
                        col_def += f' COLLATE "{coll_schema}"."{coll_name}"'
                        
                    # Nullability
                    if attnotnull:
                        col_def += " NOT NULL"
                        
                    # Default
                    if default is not None:
                        col_def += f" DEFAULT {default}"
                        
                    lines.append(col_def)

                # Format Constraints helper
                def format_constraint_def(con_def):
                    def quote_refs(m):
                        schema_or_table = m.group(1)
                        maybe_table = m.group(2)
                        cols = m.group(3)
                        if maybe_table:
                            ref_part = f'"{schema_or_table}"."{maybe_table}"'
                        else:
                            ref_part = f'"{schema_or_table}"'
                        quoted_cols = [f'"{c.strip()}"' if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', c.strip()) else c.strip() for c in cols.split(',')]
                        return f'REFERENCES {ref_part} ({", ".join(quoted_cols)})'
                        
                    con_def = re.sub(
                        r'REFERENCES\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\.([a-zA-Z_][a-zA-Z0-9_]*))?\s*\((.*?)\)', 
                        quote_refs, 
                        con_def, 
                        flags=re.IGNORECASE
                    )
                    
                    def quote_key_cols(m):
                        key_type = m.group(1)
                        cols = m.group(2)
                        quoted_cols = [f'"{c.strip()}"' if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', c.strip()) else c.strip() for c in cols.split(',')]
                        return f'{key_type} ({", ".join(quoted_cols)})'
                        
                    con_def = re.sub(
                        r'\b(PRIMARY KEY|UNIQUE|FOREIGN KEY)\s*\((.*?)\)', 
                        quote_key_cols, 
                        con_def, 
                        flags=re.IGNORECASE
                    )
                    return con_def

                # Add Constraints
                for con_name, con_def in const_rows:
                    formatted_con = format_constraint_def(con_def)
                    lines.append(f'  CONSTRAINT "{con_name}" {formatted_con}')

                ddl += ",\n".join(lines)
                ddl += "\n)\n;\n\n"

                # Add Alter Owner
                ddl += f'ALTER TABLE "{resolved}"."{table_name}" \n  OWNER TO "{owner}";\n\n'

                # Format Index helper
                def format_index_def(index_def, table_columns):
                    m = re.match(r'^CREATE\s+(UNIQUE\s+)?INDEX\s+(\S+)\s+ON\s+(\S+)\s+USING\s+(\S+)\s*\((.*)\)$', index_def, re.IGNORECASE)
                    if not m:
                        return index_def
                    is_unique = m.group(1) or ""
                    idx_name = m.group(2)
                    table_path = m.group(3)
                    method = m.group(4)
                    cols_expr = m.group(5)
                    
                    if not idx_name.startswith('"'):
                        idx_name = f'"{idx_name}"'
                        
                    parts = table_path.split('.')
                    quoted_parts = []
                    for p in parts:
                        clean_p = p.replace('"', '')
                        quoted_parts.append(f'"{clean_p}"')
                    quoted_table_path = '.'.join(quoted_parts)
                    
                    col_parts = [c.strip() for c in cols_expr.split(',')]
                    formatted_cols = []
                    for part in col_parts:
                        sub_m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)(.*)$', part)
                        if sub_m:
                            col_name = sub_m.group(1)
                            rest = sub_m.group(2).strip()
                            quoted_col = f'"{col_name}"'
                            col_type = table_columns.get(col_name, "")
                            if col_type in ('varchar', 'text', 'bpchar') and method.lower() == 'btree':
                                if not rest:
                                    quoted_col = f'{quoted_col} COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST'
                                else:
                                    quoted_col = f'{quoted_col} {rest}'
                            else:
                                if rest:
                                    quoted_col = f'{quoted_col} {rest}'
                            formatted_cols.append(quoted_col)
                        else:
                            formatted_cols.append(part)
                            
                    unique_str = "UNIQUE " if is_unique else ""
                    formatted_def = f'CREATE {unique_str}INDEX {idx_name} ON {quoted_table_path} USING {method} (\n  ' + ',\n  '.join(formatted_cols) + '\n);'
                    formatted_def = re.sub(r'\s+', ' ', formatted_def, count=2)
                    formatted_def = formatted_def.replace(' ( ', ' (\n  ').replace(' );', '\n);')
                    return formatted_def

                # Add Indexes
                for idx_name, idx_def in idx_rows:
                    if idx_name not in const_names:
                        formatted_idx = format_index_def(idx_def, table_columns)
                        ddl += f"{formatted_idx}\n\n"

                # Remove trailing newlines
                ddl = ddl.strip() + "\n"
                return ddl
            except Exception as e:
                return f"-- Definition for {resolved}.{table_name} could not be retrieved: {str(e)}"

    def get_view_definition(self, schema, view_name):
        if self.db_type == "sqlite":
            try:
                _, rows = self._sqlite_execute(
                    "SELECT sql FROM sqlite_master WHERE type='view' AND name=?",
                    (view_name,)
                )
                if rows and rows[0][0]:
                    return rows[0][0] + ";"
                return f"-- Definition for {view_name} could not be retrieved."
            except Exception as e:
                return f"-- Definition for {view_name} could not be retrieved: {str(e)}"
        
        resolved = self._resolve_schema(schema)
        if self.db_type == "mysql":
            q_table = f"`{resolved}`.`{view_name}`"
            query = f"SHOW CREATE VIEW {q_table};"
            try:
                _, rows, _ = self.execute_query(query)
                if rows:
                    return decode_val(rows[0][1])
            except Exception:
                # Fallback to SHOW CREATE TABLE
                query = f"SHOW CREATE TABLE {q_table};"
                try:
                    _, rows, _ = self.execute_query(query)
                    if rows:
                        return decode_val(rows[0][1])
                except Exception as e:
                    return f"-- Definition for {resolved}.{view_name} could not be retrieved: {str(e)}"
            return f"-- Definition for {resolved}.{view_name} could not be retrieved."
        else:
            # PostgreSQL view def query
            query = """
            SELECT pg_get_viewdef(c.oid, true)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s;
            """
            try:
                _, rows, _ = self.execute_query(query, (resolved, view_name))
                if rows and rows[0][0]:
                    return f"CREATE OR REPLACE VIEW {resolved}.{view_name} AS\n{decode_val(rows[0][0])}"
                return f"-- Definition for {resolved}.{view_name} could not be retrieved."
            except Exception as e:
                return f"-- Definition for {resolved}.{view_name} could not be retrieved: {str(e)}"
