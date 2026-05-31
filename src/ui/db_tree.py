from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from src.db_engine import DbEngine
from src.ui.connection_dlg import ConnectionDialog
import src.config as config

# Define custom QTreeWidgetItem classes or use setData to differentiate node types
NODE_TYPE_CONNECTION = "connection"
NODE_TYPE_DATABASE_LIST = "db_list"
NODE_TYPE_DATABASE = "database"
NODE_TYPE_SCHEMA = "schema"
NODE_TYPE_TABLE_GROUP = "table_group"
NODE_TYPE_VIEW_GROUP = "view_group"
NODE_TYPE_FUNCTION_GROUP = "function_group"
NODE_TYPE_TABLE = "table"
NODE_TYPE_VIEW = "view"
NODE_TYPE_FUNCTION = "function"

class DbTreeWidget(QTreeWidget):
    # Signals to communicate actions back to main window
    open_query_editor_signal = pyqtSignal(object, str, str, str)  # (db_engine, database_name, schema_name, initial_sql)
    open_table_viewer_signal = pyqtSignal(object, str, str, str) # (db_engine, database_name, schema_name, table_name)
    connection_changed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Database Explorer")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.setIndentation(12)  # Reduce indentation for compact hierarchy
        
        # Keep track of active DB engines by connection ID and database name
        # Format: {(connection_id, dbname): DbEngine}
        self.db_engines = {}
        
        self.load_profiles()

    def load_profiles(self):
        self.clear()
        self.db_engines.clear()
        
        profiles = config.load_profiles()
        for p in profiles:
            item = QTreeWidgetItem(self)
            item.setText(0, p.get("name", "Unnamed Connection"))
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_CONNECTION,
                "profile": p,
                "loaded": False
            })
            # Add a dummy child to make it expandable
            dummy = QTreeWidgetItem(item)
            dummy.setText(0, "Loading...")

    def on_item_expanded(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("loaded", True):
            return

        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            node_type = data["type"]
            if node_type == NODE_TYPE_CONNECTION:
                self.expand_connection(item, data["profile"])
            elif node_type == NODE_TYPE_DATABASE:
                self.expand_database(item, data)
            elif node_type == NODE_TYPE_SCHEMA:
                self.expand_schema(item, data)
            elif node_type == NODE_TYPE_TABLE_GROUP:
                self.expand_table_group(item, data)
            elif node_type == NODE_TYPE_VIEW_GROUP:
                self.expand_view_group(item, data)
            elif node_type == NODE_TYPE_FUNCTION_GROUP:
                self.expand_function_group(item, data)
            
            data["loaded"] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to expand items:\n{str(e)}")
            item.setExpanded(False)
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def expand_connection(self, item, profile):
        # Remove dummy child
        item.takeChildren()

        # Connect to default database first to list databases
        engine = DbEngine(
            host=profile["host"],
            port=profile["port"],
            database=profile["database"],
            username=profile["username"],
            password=profile["password"],
            sslmode=profile["sslmode"]
        )
        engine.connect()
        
        # Save engine for future database listing
        self.db_engines[(profile["id"], profile["database"])] = engine
        
        databases = engine.get_databases()
        for db in databases:
            db_item = QTreeWidgetItem(item)
            db_item.setText(0, db)
            db_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_DATABASE,
                "profile": profile,
                "dbname": db,
                "loaded": False
            })
            # Add dummy child
            dummy = QTreeWidgetItem(db_item)
            dummy.setText(0, "Loading...")

    def expand_database(self, item, data):
        item.takeChildren()
        
        profile = data["profile"]
        dbname = data["dbname"]
        
        # Get or create engine for this database
        engine_key = (profile["id"], dbname)
        if engine_key in self.db_engines:
            engine = self.db_engines[engine_key]
        else:
            engine = DbEngine(
                host=profile["host"],
                port=profile["port"],
                database=dbname,
                username=profile["username"],
                password=profile["password"],
                sslmode=profile["sslmode"]
            )
            engine.connect()
            self.db_engines[engine_key] = engine
            
        schemas = engine.get_schemas()
        for schema in schemas:
            schema_item = QTreeWidgetItem(item)
            schema_item.setText(0, schema)
            schema_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_SCHEMA,
                "profile": profile,
                "dbname": dbname,
                "schema": schema,
                "loaded": False
            })
            dummy = QTreeWidgetItem(schema_item)
            dummy.setText(0, "Loading...")

    def expand_schema(self, item, data):
        item.takeChildren()
        
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data["schema"]
        
        # Create Table and View group folders
        table_group = QTreeWidgetItem(item)
        table_group.setText(0, "Tables")
        table_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_TABLE_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": False
        })
        dummy_t = QTreeWidgetItem(table_group)
        dummy_t.setText(0, "Loading...")

        view_group = QTreeWidgetItem(item)
        view_group.setText(0, "Views")
        view_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_VIEW_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": False
        })
        dummy_v = QTreeWidgetItem(view_group)
        dummy_v.setText(0, "Loading...")

        func_group = QTreeWidgetItem(item)
        func_group.setText(0, "Functions")
        func_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_FUNCTION_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": False
        })
        dummy_f = QTreeWidgetItem(func_group)
        dummy_f.setText(0, "Loading...")

    def expand_table_group(self, item, data):
        item.takeChildren()
        
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data["schema"]
        
        engine = self.db_engines[(profile["id"], dbname)]
        tables = engine.get_tables(schema)
        
        for table in tables:
            t_item = QTreeWidgetItem(item)
            t_item.setText(0, table)
            t_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_TABLE,
                "profile": profile,
                "dbname": dbname,
                "schema": schema,
                "table_name": table
            })

    def expand_view_group(self, item, data):
        item.takeChildren()
        
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data["schema"]
        
        engine = self.db_engines[(profile["id"], dbname)]
        views = engine.get_views(schema)
        
        for view in views:
            v_item = QTreeWidgetItem(item)
            v_item.setText(0, view)
            v_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_VIEW,
                "profile": profile,
                "dbname": dbname,
                "schema": schema,
                "table_name": view
            })

    def expand_function_group(self, item, data):
        item.takeChildren()
        
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data["schema"]
        
        engine = self.db_engines[(profile["id"], dbname)]
        funcs = engine.get_functions(schema)
        
        for func in funcs:
            f_item = QTreeWidgetItem(item)
            f_item.setText(0, func)
            f_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_FUNCTION,
                "profile": profile,
                "dbname": dbname,
                "schema": schema,
                "func_name": func
            })

    def on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        node_type = data.get("type")
        if node_type in (NODE_TYPE_TABLE, NODE_TYPE_VIEW):
            profile = data["profile"]
            dbname = data["dbname"]
            schema = data["schema"]
            table_name = data["table_name"]
            
            engine = self.db_engines.get((profile["id"], dbname))
            if engine:
                self.open_table_viewer_signal.emit(engine, dbname, schema, table_name)
        elif node_type == NODE_TYPE_FUNCTION:
            profile = data["profile"]
            dbname = data["dbname"]
            schema = data["schema"]
            func_name = data["func_name"]
            
            engine = self.db_engines.get((profile["id"], dbname))
            if engine:
                self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
                try:
                    sql_def = engine.get_function_definition(schema, func_name)
                    self.open_query_editor_signal.emit(engine, dbname, schema, sql_def)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not retrieve function definition:\n{str(e)}")
                finally:
                    self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        node_type = data.get("type")
        
        menu = QMenu(self)
        
        if node_type == NODE_TYPE_CONNECTION:
            open_action = menu.addAction("Open Connection")
            close_action = menu.addAction("Close Connection")
            menu.addSeparator()
            edit_action = menu.addAction("Edit Connection...")
            delete_action = menu.addAction("Delete Connection")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == open_action:
                item.setExpanded(True)
            elif action == close_action:
                item.setExpanded(False)
            elif action == edit_action:
                self.edit_connection(item, data["profile"])
            elif action == delete_action:
                self.delete_connection(item, data["profile"])
                
        elif node_type == NODE_TYPE_DATABASE:
            query_action = menu.addAction("New Query Editor")
            refresh_action = menu.addAction("Refresh")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == query_action:
                self.open_query_for_node(data)
            elif action == refresh_action:
                data["loaded"] = False
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                item.setExpanded(False)
                item.setExpanded(True)

        elif node_type == NODE_TYPE_SCHEMA:
            query_action = menu.addAction("New Query Editor")
            refresh_action = menu.addAction("Refresh")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == query_action:
                self.open_query_for_node(data)
            elif action == refresh_action:
                data["loaded"] = False
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                item.setExpanded(False)
                item.setExpanded(True)

        elif node_type in (NODE_TYPE_TABLE, NODE_TYPE_VIEW):
            open_data_action = menu.addAction("Open Table Data")
            query_action = menu.addAction("New Query Editor")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == open_data_action:
                self.on_item_double_clicked(item, 0)
            elif action == query_action:
                self.open_query_for_node(data)

    def open_query_for_node(self, data):
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        
        engine = self.db_engines.get((profile["id"], dbname))
        if not engine:
            # Expand to create engine if not already created
            engine = DbEngine(
                host=profile["host"],
                port=profile["port"],
                database=dbname,
                username=profile["username"],
                password=profile["password"],
                sslmode=profile["sslmode"]
            )
            engine.connect()
            self.db_engines[(profile["id"], dbname)] = engine
            
        self.open_query_editor_signal.emit(engine, dbname, schema, "")

    def edit_connection(self, item, profile):
        dlg = ConnectionDialog(self, profile)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            config.add_or_update_profile(new_data)
            # Reload configuration
            self.load_profiles()
            self.connection_changed_signal.emit()

    def delete_connection(self, item, profile):
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete connection '{profile.get('name')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            config.delete_profile(profile["id"])
            # Remove from active engine cache if any
            for key in list(self.db_engines.keys()):
                if key[0] == profile["id"]:
                    self.db_engines[key].close()
                    del self.db_engines[key]
            self.load_profiles()
            self.connection_changed_signal.emit()
