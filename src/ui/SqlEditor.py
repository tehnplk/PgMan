from PyQt6.QtWidgets import QPlainTextEdit, QCompleter
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QTextCursor, QKeyEvent
import re

class SqlEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None
        self.resolve_columns_callback = None
        
        # Default SQL keywords
        self.sql_keywords = [
            "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "JOIN",
            "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR", "NOT",
            "IN", "LIKE", "IS", "NULL", "ORDER", "BY", "GROUP", "LIMIT",
            "CREATE", "TABLE", "VIEW", "FUNCTION", "DROP", "ALTER", "INTO",
            "VALUES", "SET", "AS", "HAVING", "UNION", "ALL", "COUNT", "SUM",
            "AVG", "MIN", "MAX", "DISTINCT", "EXISTS", "INDEX", "SHOW", "DESC",
            "DESCRIBE"
        ]
        
        self.autocomplete_words = self.sql_keywords + [w.lower() for w in self.sql_keywords]
        self.setup_completer()

    def setup_completer(self):
        self.completer = QCompleter(self.autocomplete_words, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)

    def set_autocomplete_words(self, words):
        # Merge new words (like table names) with SQL keywords, keeping them unique
        unique_words = list(set(self.sql_keywords + [w.lower() for w in self.sql_keywords] + words))
        unique_words.sort()
        self.autocomplete_words = unique_words
        
        # Re-set the completer model
        model = QStringListModel(self.autocomplete_words, self.completer)
        self.completer.setModel(model)

    def insert_completion(self, completion):
        if self.completer.widget() is not self:
            return
            
        # If it is an SQL keyword, force it to uppercase
        upper_keyword = completion.upper()
        if upper_keyword in self.sql_keywords:
            completion = upper_keyword
            
        tc = self.textCursor()
        prefix = self.completer.completionPrefix()
        if prefix:
            tc.movePosition(QTextCursor.MoveOperation.Left)
            tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
            tc.select(QTextCursor.SelectionType.WordUnderCursor)
            tc.insertText(completion + " ")
        else:
            tc.insertText(completion + " ")
        self.setTextCursor(tc)

    def text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        text = tc.selectedText()
        if text and re.match(r'^[a-zA-Z0-9_]+$', text):
            return text
        return ""

    def keyPressEvent(self, event: QKeyEvent):
        # 1. If completer is visible and user presses navigation keys, pass to completer
        if self.completer and self.completer.popup() and self.completer.popup().isVisible():
            if event.key() in (
                Qt.Key.Key_Enter, Qt.Key.Key_Return,
                Qt.Key.Key_Escape, Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab, Qt.Key.Key_Down, Qt.Key.Key_Up
            ):
                event.ignore()
                return
                
        is_shortcut = (event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space)
        
        if not is_shortcut:
            super().keyPressEvent(event)
            
        # 2. Check if we should show the completer popup
        if self.completer:
            tc = self.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
            line_text = tc.selectedText()
            
            alias_match = re.search(r'\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]*)$', line_text)
            
            is_word_char = event.text() and (event.text().isalnum() or event.text() in ('_', '.'))
            
            if alias_match and self.resolve_columns_callback:
                alias = alias_match.group(1)
                prefix = alias_match.group(2)
                
                columns = self.resolve_columns_callback(alias)
                if columns:
                    col_suggestions = columns + [c.lower() for c in columns]
                    model = QStringListModel(col_suggestions, self.completer)
                    self.completer.setModel(model)
                    self.completer.setCompletionPrefix(prefix)
                    
                    cr = self.cursorRect()
                    cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
                    self.completer.complete(cr)
                    return
            
            # Revert to standard model
            model = QStringListModel(self.autocomplete_words, self.completer)
            self.completer.setModel(model)
            
            completion_prefix = self.text_under_cursor()
            
            if is_shortcut or (is_word_char and len(completion_prefix) >= 1):
                self.completer.setCompletionPrefix(completion_prefix)
                popup = self.completer.popup()
                popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
                
                # Position popup at the cursor
                cr = self.cursorRect()
                cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cr)
            else:
                if not completion_prefix:
                    self.completer.popup().hide()
