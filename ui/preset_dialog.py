from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox

class PresetDialog(QDialog):
    def __init__(self, parent=None, name="", content="", notes=""):
        super().__init__(parent)
        self.setWindowTitle("提示词预设")
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.name_edit = QLineEdit(name)
        self.content_edit = QTextEdit(content)
        self.notes_edit = QTextEdit(notes)
        
        self.content_edit.setMinimumHeight(200)
        self.notes_edit.setMaximumHeight(80)
        
        form.addRow("预设名称:", self.name_edit)
        form.addRow("提示词内容:", self.content_edit)
        form.addRow("备注说明:", self.notes_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)
    
    def get_data(self):
        return (
            self.name_edit.text().strip(),
            self.content_edit.toPlainText().strip(),
            self.notes_edit.toPlainText().strip()
        ) 