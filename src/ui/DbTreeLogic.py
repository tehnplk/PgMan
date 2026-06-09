from PyQt6.QtWidgets import QTreeWidgetItem, QMenu, QMessageBox, QDialog, QInputDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from src.DbEngine import DbEngine
from src.ui.ConnectionDlgLogic import ConnectionDialog
from src.ui.DbTreeUI import DbTreeUI
import src.Config as config
from src.ui.UiUtils import show_exception_dialog

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

class DbTreeWidget(DbTreeUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.itemClicked.connect(self.on_item_clicked)
        
        # Cache active DB engines by connection ID and database name
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
            # Add dummy child
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
            
            data["loaded"] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        except Exception as e:
            show_exception_dialog(self, "Error", f"Failed to expand items:\n{str(e)}")
            item.setExpanded(False)
            if data and data.get("type") in (NODE_TYPE_CONNECTION, NODE_TYPE_DATABASE, NODE_TYPE_SCHEMA):
                item.takeChildren()
                dummy = QTreeWidgetItem(item)
                dummy.setText(0, "Loading...")
                data["loaded"] = False
                item.setData(0, Qt.ItemDataRole.UserRole, data)
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def _create_engine(self, profile, dbname=None):
        """Helper to create a DbEngine from a profile."""
        return DbEngine(
            host=profile.get("host", ""),
            port=profile.get("port", 0),
            database=dbname or profile.get("database", ""),
            username=profile.get("username", ""),
            password=profile.get("password", ""),
            sslmode=profile.get("sslmode", "prefer"),
            db_type=profile.get("db_type", "PostgreSQL"),
            file_path=profile.get("file_path", ""),
            charset=profile.get("charset", "")
        )

    def expand_connection(self, item, profile):
        item.takeChildren()

        engine = self._create_engine(profile)
        engine.connect()
        
        db_type = profile.get("db_type", "PostgreSQL").lower()
        
        if db_type == "sqlite":
            # SQLite has a single database — use filename
            import os
            db_display = os.path.basename(profile.get("file_path", "database"))
            self.db_engines[(profile["id"], db_display)] = engine
            
            db_item = QTreeWidgetItem(item)
            db_item.setText(0, db_display)
            db_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": NODE_TYPE_DATABASE,
                "profile": profile,
                "dbname": db_display,
                "loaded": False
            })
            dummy = QTreeWidgetItem(db_item)
            dummy.setText(0, "Loading...")
        else:
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
                dummy = QTreeWidgetItem(db_item)
                dummy.setText(0, "Loading...")

    def expand_database(self, item, data):
        item.takeChildren()
        profile = data["profile"]
        dbname = data["dbname"]
        
        engine_key = (profile["id"], dbname)
        if engine_key in self.db_engines:
            engine = self.db_engines[engine_key]
        else:
            engine = self._create_engine(profile, dbname)
            engine.connect()
            self.db_engines[engine_key] = engine
            
        schemas = engine.get_schemas()
        
        db_type = profile.get("db_type", "PostgreSQL").lower()
        
        if db_type == "sqlite" and len(schemas) == 1:
            # For SQLite, skip the schema level and go directly to table/view/function groups
            self.expand_schema(item, {
                "profile": profile,
                "dbname": dbname,
                "schema": schemas[0]
            })
            # Mark as loaded so the schema groups are visible immediately
            return
        
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
        
        table_group = QTreeWidgetItem(item)
        table_group.setText(0, "Tables")
        table_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_TABLE_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": True
        })

        view_group = QTreeWidgetItem(item)
        view_group.setText(0, "Views")
        view_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_VIEW_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": True
        })

        func_group = QTreeWidgetItem(item)
        func_group.setText(0, "Functions")
        func_group.setData(0, Qt.ItemDataRole.UserRole, {
            "type": NODE_TYPE_FUNCTION_GROUP,
            "profile": profile,
            "dbname": dbname,
            "schema": schema,
            "loaded": True
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
                    show_exception_dialog(self, "Error", f"Could not retrieve function definition:\n{str(e)}")
                finally:
                    self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def on_item_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        node_type = data.get("type")
        if node_type in (NODE_TYPE_TABLE_GROUP, NODE_TYPE_VIEW_GROUP, NODE_TYPE_FUNCTION_GROUP):
            profile = data["profile"]
            dbname = data["dbname"]
            schema = data.get("schema", "public")
            group_name = item.text(0)
            
            engine = self.db_engines.get((profile["id"], dbname))
            if not engine:
                return
                
            self.open_object_tab_signal.emit(engine, dbname, schema, group_name, profile)

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
            create_db_action = None
            db_type = data["profile"].get("db_type", "PostgreSQL").lower()
            if db_type != "sqlite":
                create_db_action = menu.addAction("Create New Database")
            menu.addSeparator()
            edit_action = menu.addAction("Edit Connection...")
            delete_action = menu.addAction("Delete Connection")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == open_action:
                item.setExpanded(True)
            elif action == close_action:
                item.setExpanded(False)
            elif action == create_db_action and create_db_action:
                self.create_new_database(item, data)
            elif action == edit_action:
                self.edit_connection(item, data["profile"])
            elif action == delete_action:
                self.delete_connection(item, data["profile"])
                
        elif node_type == NODE_TYPE_DATABASE:
            query_action = menu.addAction("New Query Editor")
            refresh_action = menu.addAction("Refresh")
            drop_db_action = None
            db_type = data["profile"].get("db_type", "PostgreSQL").lower()
            if db_type != "sqlite":
                drop_db_action = menu.addAction("Drop This Database")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == query_action:
                self.open_query_for_node(data)
            elif action == refresh_action:
                data["loaded"] = False
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                item.setExpanded(False)
                item.setExpanded(True)
            elif action == drop_db_action and drop_db_action:
                self.drop_database(item, data)

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

        elif node_type == NODE_TYPE_TABLE_GROUP:
            create_action = menu.addAction("Create New Table")
            refresh_action = menu.addAction("Refresh")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == create_action:
                self.create_new_table_for_group(item, data)
            elif action == refresh_action:
                profile = data["profile"]
                dbname = data["dbname"]
                schema = data.get("schema", "public")
                engine = self.db_engines.get((profile["id"], dbname))
                if engine:
                    self.open_object_tab_signal.emit(engine, dbname, schema, "Tables", profile)

        elif node_type in (NODE_TYPE_TABLE, NODE_TYPE_VIEW):
            open_data_action = menu.addAction("Open Table Data")
            design_action = None
            drop_action = None
            if node_type == NODE_TYPE_TABLE:
                design_action = menu.addAction("Design Table")
                drop_action = menu.addAction("Drop Table")
            query_action = menu.addAction("New Query Editor")
            ddl_action = menu.addAction("Show DDL")
            
            action = menu.exec(self.mapToGlobal(position))
            if action == open_data_action:
                self.on_item_double_clicked(item, 0)
            elif action == design_action and design_action:
                self.open_designer_for_node(data)
            elif action == drop_action and drop_action:
                self.drop_table_for_node(item, data)
            elif action == query_action:
                self.open_query_for_node(data)
            elif action == ddl_action:
                self.show_ddl_for_node(data)

    def show_ddl_for_node(self, data):
        node_type = data.get("type")
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        table_name = data.get("table_name")
        
        engine = self.db_engines.get((profile["id"], dbname))
        if engine:
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                if node_type == NODE_TYPE_TABLE:
                    sql_def = engine.get_table_definition(schema, table_name)
                else:  # VIEW
                    sql_def = engine.get_view_definition(schema, table_name)
                self.open_query_editor_signal.emit(engine, dbname, schema, sql_def)
            except Exception as e:
                show_exception_dialog(self, "Error", f"Could not retrieve definition:\n{str(e)}")
            finally:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def create_new_database(self, item, data):
        profile = data["profile"]
        db_type = profile.get("db_type", "PostgreSQL")
        
        name, ok = QInputDialog.getText(self, "Create New Database", "Enter database name:")
        if not ok or not name.strip():
            return
            
        dbname = name.strip()
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            default_db = profile.get("database", "postgres" if db_type.lower() == "postgresql" else "")
            engine_key = (profile["id"], default_db)
            engine = self.db_engines.get(engine_key)
            if not engine:
                engine = self._create_engine(profile, default_db)
                engine.connect()
                self.db_engines[engine_key] = engine
                
            quoted_db = engine._quote_ident(dbname)
            sql = f"CREATE DATABASE {quoted_db};"
            engine.execute_query(sql, fetch_results=False)
            
            QMessageBox.information(self, "Success", f"Database '{dbname}' created successfully.")
            
            # Refresh connection node
            data["loaded"] = False
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            item.setExpanded(False)
            item.setExpanded(True)
            
        except Exception as e:
            show_exception_dialog(self, "Error", f"Failed to create database:\n{str(e)}")
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def open_designer_for_node(self, data):
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        table_name = data.get("table_name")

        engine = self.db_engines.get((profile["id"], dbname))
        if engine:
            self.open_table_designer_signal.emit(engine, dbname, schema, table_name, False)

    def create_new_table_for_group(self, item, data):
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        engine = self.db_engines.get((profile["id"], dbname))
        if not engine:
            return
            
        name, ok = QInputDialog.getText(self, "Create New Table", "Enter table name:")
        if ok and name.strip():
            table_name = name.strip()
            self.open_table_designer_signal.emit(engine, dbname, schema, table_name, True)

    def drop_table_for_node(self, item, data):
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        table_name = data.get("table_name")
        engine = self.db_engines.get((profile["id"], dbname))
        if not engine or not table_name:
            return
            
        table_ref = engine.quote_table_name(schema, table_name)
        reply = QMessageBox.question(
            self, "Confirm Drop Table",
            f"Are you sure you want to DROP the table {table_ref}?\n\nThis action cannot be undone and all data in the table will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                sql = f"DROP TABLE {table_ref};"
                engine.execute_query(sql, fetch_results=False)
                engine.clear_cache()
                
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                
                # Close any open TableViewerTab or TableDesignerTab for this table
                main_win = self.window()
                if hasattr(main_win, "tabs"):
                    from src.ui.TableViewerLogic import TableViewerTab
                    from src.ui.TableDesignerLogic import TableDesignerTab
                    tabs_to_close = []
                    for idx in range(main_win.tabs.count()):
                        w = main_win.tabs.widget(idx)
                        if isinstance(w, TableViewerTab) or isinstance(w, TableDesignerTab):
                            if w.dbname == dbname and w.schema == schema and w.table_name == table_name:
                                tabs_to_close.append(idx)
                    for idx in sorted(tabs_to_close, reverse=True):
                        w = main_win.tabs.widget(idx)
                        if w:
                            w.deleteLater()
                        main_win.tabs.removeTab(idx)
                        
                # Refresh any open ObjectTab
                if hasattr(main_win, "tabs"):
                    from src.ui.ObjectTabLogic import ObjectTab
                    for idx in range(main_win.tabs.count()):
                        w = main_win.tabs.widget(idx)
                        if isinstance(w, ObjectTab):
                            if w.db_engine == engine and w.schema == schema and w.group_name == "Tables":
                                w.refresh_data()
                                
            except Exception as e:
                show_exception_dialog(self, "Error", f"Failed to drop table:\n{str(e)}")
            finally:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def drop_database(self, item, data):
        profile = data["profile"]
        dbname = data["dbname"]
        db_type = profile.get("db_type", "PostgreSQL")
        
        reply = QMessageBox.question(
            self, "Confirm Drop Database",
            f"Are you sure you want to DROP the database '{dbname}'?\n\nThis action cannot be undone and all schemas, tables, and data in this database will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            # 1. Close the active connection to the database we want to drop if it exists in cache
            target_engine_key = (profile["id"], dbname)
            if target_engine_key in self.db_engines:
                try:
                    self.db_engines[target_engine_key].close()
                except Exception:
                    pass
                del self.db_engines[target_engine_key]
                
            # 2. Close any open tabs related to this database
            main_win = self.window()
            if hasattr(main_win, "tabs"):
                from src.ui.QueryEditorLogic import QueryEditorTab
                from src.ui.TableViewerLogic import TableViewerTab
                from src.ui.ObjectTabLogic import ObjectTab
                from src.ui.TableDesignerLogic import TableDesignerTab
                tabs_to_close = []
                for idx in range(main_win.tabs.count()):
                    w = main_win.tabs.widget(idx)
                    if isinstance(w, (QueryEditorTab, TableViewerTab, ObjectTab, TableDesignerTab)):
                        if hasattr(w, "dbname") and w.dbname == dbname:
                            tabs_to_close.append(idx)
                        elif hasattr(w, "database_name") and w.database_name == dbname:
                            tabs_to_close.append(idx)
                for idx in sorted(tabs_to_close, reverse=True):
                    w = main_win.tabs.widget(idx)
                    if w:
                        w.deleteLater()
                    main_win.tabs.removeTab(idx)
                    
            # 3. Connect to a default database to execute the DROP DATABASE command
            default_db = profile.get("database", "postgres" if db_type.lower() == "postgresql" else "")
            # If the default database configured in the profile is the database we want to drop,
            # we need to fallback to postgres for PostgreSQL, or another generic db.
            if default_db == dbname:
                default_db = "postgres" if db_type.lower() == "postgresql" else ""
                
            engine_key = (profile["id"], default_db)
            engine = self.db_engines.get(engine_key)
            if not engine:
                engine = self._create_engine(profile, default_db)
                engine.connect()
                self.db_engines[engine_key] = engine
                
            quoted_db = engine._quote_ident(dbname)
            
            # Execute DROP DATABASE. For PostgreSQL, try WITH (FORCE) first, then fallback if it fails.
            if db_type.lower() == "postgresql":
                try:
                    sql = f"DROP DATABASE {quoted_db} WITH (FORCE);"
                    engine.execute_query(sql, fetch_results=False)
                except Exception:
                    # Fallback: terminate connections then drop database normally
                    try:
                        terminate_sql = f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{dbname}'
                          AND pid <> pg_backend_pid();
                        """
                        engine.execute_query(terminate_sql, fetch_results=False)
                    except Exception:
                        pass
                    sql = f"DROP DATABASE {quoted_db};"
                    engine.execute_query(sql, fetch_results=False)
            else:
                # MySQL or other
                sql = f"DROP DATABASE {quoted_db};"
                engine.execute_query(sql, fetch_results=False)
                
            QMessageBox.information(self, "Success", f"Database '{dbname}' dropped successfully.")
            
            # Remove the database item from the tree
            parent = item.parent()
            if parent:
                parent.removeChild(item)
                
        except Exception as e:
            show_exception_dialog(self, "Error", f"Failed to drop database:\n{str(e)}")
        finally:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def open_query_for_node(self, data):
        profile = data["profile"]
        dbname = data["dbname"]
        schema = data.get("schema", "public")
        
        engine = self.db_engines.get((profile["id"], dbname))
        if not engine:
            engine = self._create_engine(profile, dbname)
            engine.connect()
            self.db_engines[(profile["id"], dbname)] = engine
            
        self.open_query_editor_signal.emit(engine, dbname, schema, "")

    def edit_connection(self, item, profile):
        dlg = ConnectionDialog(self, profile)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_data()
            config.add_or_update_profile(new_data)
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
            for key in list(self.db_engines.keys()):
                if key[0] == profile["id"]:
                    self.db_engines[key].close()
                    del self.db_engines[key]
            self.load_profiles()
            self.connection_changed_signal.emit()
