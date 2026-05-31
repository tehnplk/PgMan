from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import QRegularExpression, Qt

class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keyword format (Cyan / Light Blue)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#00e5ff"))
        keyword_format.setFontWeight(QFont.Weight.Bold)

        # SQL System Functions / Types (Yellowish/Amber)
        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#e5c07b"))

        # String format (Green)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#98c379"))

        # Number format (Orange)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#d19a66"))

        # Identifier/Column quotes (Light cyan/grey)
        identifier_format = QTextCharFormat()
        identifier_format.setForeground(QColor("#61afef"))

        # Comment format (Muted Gray)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#5c6370"))
        comment_format.setFontItalic(True)

        # SQL keywords
        keywords = [
            r"\bselect\b", r"\binsert\b", r"\bupdate\b", r"\bdelete\b",
            r"\bfrom\b", r"\bwhere\b", r"\band\b", r"\bor\b", r"\bjoin\b",
            r"\bleft\b", r"\bright\b", r"\binner\b", r"\bouter\b", r"\bon\b",
            r"\bgroup\b", r"\bby\b", r"\border\b", r"\blimit\b", r"\boffset\b",
            r"\bcreate\b", r"\bdrop\b", r"\balter\b", r"\btable\b", r"\bdatabase\b",
            r"\binto\b", r"\bvalues\b", r"\bset\b", r"\bas\b", r"\bin\b",
            r"\bis\b", r"\bnull\b", r"\bnot\b", r"\blike\b", r"\bilike\b",
            r"\bcase\b", r"\bwhen\b", r"\bthen\b", r"\belse\b", r"\bend\b",
            r"\bunion\b", r"\ball\b", r"\bexists\b", r"\bhaving\b", r"\bindex\b",
            r"\bprimary\b", r"\bkey\b", r"\bforeign\b", r"\breferences\b"
        ]

        for word in keywords:
            pattern = QRegularExpression(word, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((pattern, keyword_format))

        # Data types
        types = [
            r"\binteger\b", r"\bint\b", r"\bvarchar\b", r"\btext\b",
            r"\bboolean\b", r"\bbool\b", r"\btimestamp\b", r"\bdate\b",
            r"\bnumeric\b", r"\bdouble\b", r"\bfloat\b", r"\bjson\b", r"\bjsonb\b",
            r"\buuid\b", r"\bchar\b", r"\bbigint\b", r"\bsmallint\b", r"\breal\b"
        ]

        for t in types:
            pattern = QRegularExpression(t, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((pattern, type_format))

        # Numbers
        self.highlighting_rules.append((QRegularExpression(r"\b\d+\b"), number_format))

        # Identifiers in double quotes
        self.highlighting_rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), identifier_format))

        # Strings in single quotes
        self.highlighting_rules.append((QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Single line comments --
        self.highlighting_rules.append((QRegularExpression(r"--[^\n]*"), comment_format))

        # Multi-line comment borders (basic handling inside block)
        self.multi_line_comment_format = comment_format
        self.comment_start_expression = QRegularExpression(r"/\*")
        self.comment_end_expression = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        # 1. Apply standard rules
        for pattern, char_format in self.highlighting_rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), char_format)

        # 2. Multi-line comments /* ... */
        self.setCurrentBlockState(0)

        start_index = 0
        if self.previousBlockState() != 1:
            start_index = self.comment_start_expression.match(text).capturedStart()

        while start_index >= 0:
            match_end = self.comment_end_expression.match(text, start_index)
            end_index = match_end.capturedStart()
            comment_length = 0

            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + match_end.capturedLength()

            self.setFormat(start_index, comment_length, self.multi_line_comment_format)
            start_index = self.comment_start_expression.match(text, start_index + comment_length).capturedStart()
