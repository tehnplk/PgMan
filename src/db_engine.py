import psycopg
from psycopg.rows import dict_row

class DbEngine:
    def __init__(self, host, port, database, username, password, sslmode="prefer"):
        self.host = host
        self.port = int(port)
        self.database = database
        self.username = username
        self.password = password
        self.sslmode = sslmode
        self._connection = None

    def connect(self):
        """Establish connection to the database."""
        if self._connection and not self._connection.closed:
            return self._connection
            
        self._connection = psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.username,
            password=self.password,
            sslmode=self.sslmode,
            connect_timeout=10
        )
        return self._connection

    def close(self):
        """Close current connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
        self._connection = None

    def execute_query(self, query, params=None, fetch_results=True):
        """
        Execute an arbitrary SQL query.
        Returns:
            columns: list of column names (or empty list if no results)
            rows: list of tuples (or empty list)
            message: string with rowcount or status message
        """
        conn = self.connect()
        # Set autocommit to True to allow DDL / transactions in raw SQL
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
                # For INSERT/UPDATE/DELETE/DDL queries
                return [], [], message
        except Exception as e:
            raise e
        finally:
            cursor.close()

    def get_databases(self):
        """Fetch list of all databases on the server."""
        query = "SELECT datname FROM pg_database WHERE datistemplate = false AND datallowconn = true ORDER BY datname;"
        _, rows, _ = self.execute_query(query)
        return [row[0] for row in rows]

    def get_schemas(self):
        """Fetch list of schemas in the current database."""
        query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema' 
        ORDER BY schema_name;
        """
        _, rows, _ = self.execute_query(query)
        return [row[0] for row in rows]

    def get_tables(self, schema="public"):
        """Fetch list of tables in a schema."""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        _, rows, _ = self.execute_query(query, (schema,))
        return [row[0] for row in rows]

    def get_views(self, schema="public"):
        """Fetch list of views in a schema."""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_type = 'VIEW'
        ORDER BY table_name;
        """
        _, rows, _ = self.execute_query(query, (schema,))
        return [row[0] for row in rows]

    def get_columns(self, schema, table_name):
        """
        Fetch columns of a table.
        Returns list of dicts: [{'name': colname, 'type': coltype, 'nullable': True/False, 'default': default}]
        """
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        _, rows, _ = self.execute_query(query, (schema, table_name))
        cols = []
        for row in rows:
            cols.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3]
            })
        return cols

    def get_primary_keys(self, schema, table_name):
        """Fetch list of primary key columns for a table."""
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
        _, rows, _ = self.execute_query(query, (schema, table_name))
        return [row[0] for row in rows]

    def update_row(self, schema, table_name, primary_keys_dict, updates_dict):
        """
        Dynamically construct and execute an UPDATE statement.
        """
        if not updates_dict:
            return
        
        set_clauses = []
        params = []
        for col, val in updates_dict.items():
            set_clauses.append(f'"{col}" = %s')
            params.append(val)
            
        where_clauses = []
        for col, val in primary_keys_dict.items():
            where_clauses.append(f'"{col}" = %s')
            params.append(val)
            
        sql = f'UPDATE "{schema}"."{table_name}" SET {", ".join(set_clauses)} WHERE {" AND ".join(where_clauses)}'
        self.execute_query(sql, params, fetch_results=False)

    def insert_row(self, schema, table_name, row_dict):
        """
        Dynamically construct and execute an INSERT statement.
        """
        if not row_dict:
            return
        
        cols = list(row_dict.keys())
        vals = list(row_dict.values())
        
        col_placeholders = ", ".join([f'"{c}"' for c in cols])
        val_placeholders = ", ".join(["%s"] * len(vals))
        
        sql = f'INSERT INTO "{schema}"."{table_name}" ({col_placeholders}) VALUES ({val_placeholders})'
        self.execute_query(sql, vals, fetch_results=False)

    def delete_row(self, schema, table_name, row_identifier_dict):
        """
        Dynamically construct and execute a DELETE statement.
        """
        if not row_identifier_dict:
            return
            
        where_clauses = []
        params = []
        for col, val in row_identifier_dict.items():
            where_clauses.append(f'"{col}" = %s')
            params.append(val)
            
        sql = f'DELETE FROM "{schema}"."{table_name}" WHERE {" AND ".join(where_clauses)}'
        self.execute_query(sql, params, fetch_results=False)

    def get_functions(self, schema="public"):
        """Fetch list of functions/procedures in a schema."""
        query = """
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = %s
        ORDER BY routine_name;
        """
        _, rows, _ = self.execute_query(query, (schema,))
        return [row[0] for row in rows]

    def get_function_definition(self, schema, func_name):
        """Fetch full CREATE OR REPLACE FUNCTION SQL definition."""
        query = """
        SELECT pg_get_functiondef(p.oid)
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = %s AND p.proname = %s;
        """
        try:
            _, rows, _ = self.execute_query(query, (schema, func_name))
            return rows[0][0] if rows else ""
        except Exception:
            return f"-- Definition for {schema}.{func_name} could not be retrieved."
