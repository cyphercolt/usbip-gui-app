from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QDialogButtonBox,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal
from security.validator import SecurityValidator


class IPManagementDialog(QDialog):
    """Dialog for managing IP addresses without switching to them"""

    ips_changed = pyqtSignal()  # Signal emitted when IPs are modified

    def __init__(self, parent=None, current_ips=None):
        super().__init__(parent)
        self.setWindowTitle("IP Address Management")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        self.resize(500, 400)

        # Store IPs list (copy to avoid modifying original during editing)
        self.ips = current_ips.copy() if current_ips else []
        self.original_ips = current_ips.copy() if current_ips else []

        self.setup_ui()
        self.populate_ip_list()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title and description
        title_label = QLabel("IP Address Management")
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; margin-bottom: 10px;"
        )
        layout.addWidget(title_label)

        desc_label = QLabel(
            "Add, remove, or edit IP addresses and hostnames safely without connecting to them."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc_label)

        # IP list widget
        list_layout = QVBoxLayout()
        list_label = QLabel("Saved IP Addresses:")
        list_label.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(list_label)

        self.ip_list = QListWidget()
        self.ip_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_layout.addWidget(self.ip_list)
        layout.addLayout(list_layout)

        # Buttons for IP management
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add IP")
        self.add_button.clicked.connect(self.add_ip)
        self.add_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit IP")
        self.edit_button.clicked.connect(self.edit_ip)
        self.edit_button.setEnabled(False)
        self.edit_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        button_layout.addWidget(self.edit_button)

        self.remove_button = QPushButton("Remove IP")
        self.remove_button.clicked.connect(self.remove_ip)
        self.remove_button.setEnabled(False)
        self.remove_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        button_layout.addWidget(self.remove_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Connect selection change to enable/disable buttons
        self.ip_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Dialog buttons
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

    def populate_ip_list(self):
        """Populate the IP list widget"""
        self.ip_list.clear()
        for ip in self.ips:
            item = QListWidgetItem(ip)
            self.ip_list.addItem(item)

    def on_selection_changed(self):
        """Handle selection change to enable/disable buttons"""
        has_selection = bool(self.ip_list.selectedItems())
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def add_ip(self):
        """Add a new IP address"""
        text, ok = QInputDialog.getText(
            self,
            "Add IP Address",
            "Enter IP address or hostname:\n\nNote: This will be validated but not tested until you select it.",
            text="",
        )

        if ok and text.strip():
            ip = text.strip()

            # Validate the IP/hostname format
            if not SecurityValidator.validate_ip_or_hostname(ip):
                QMessageBox.warning(
                    self,
                    "Invalid Format",
                    "Invalid IP address or hostname format.\n\n"
                    "Valid examples:\n"
                    "• 192.168.1.1\n"
                    "• server.example.com\n"
                    "• my-server",
                )
                return

            # Check for duplicates
            if ip in self.ips:
                QMessageBox.information(
                    self,
                    "Duplicate Entry",
                    f"IP address '{ip}' already exists in the list.",
                )
                return

            # Add to list
            self.ips.append(ip)
            self.populate_ip_list()

            # Select the newly added item
            for i in range(self.ip_list.count()):
                if self.ip_list.item(i).text() == ip:
                    self.ip_list.setCurrentRow(i)
                    break

    def edit_ip(self):
        """Edit the selected IP address"""
        current_item = self.ip_list.currentItem()
        if not current_item:
            return

        current_ip = current_item.text()
        text, ok = QInputDialog.getText(
            self, "Edit IP Address", "Edit IP address or hostname:", text=current_ip
        )

        if ok and text.strip():
            new_ip = text.strip()

            # Validate the IP/hostname format
            if not SecurityValidator.validate_ip_or_hostname(new_ip):
                QMessageBox.warning(
                    self,
                    "Invalid Format",
                    "Invalid IP address or hostname format.\n\n"
                    "Valid examples:\n"
                    "• 192.168.1.1\n"
                    "• server.example.com\n"
                    "• my-server",
                )
                return

            # Check for duplicates (excluding current IP)
            if new_ip in self.ips and new_ip != current_ip:
                QMessageBox.information(
                    self,
                    "Duplicate Entry",
                    f"IP address '{new_ip}' already exists in the list.",
                )
                return

            # Update the IP
            current_index = self.ips.index(current_ip)
            self.ips[current_index] = new_ip
            self.populate_ip_list()

            # Reselect the edited item
            self.ip_list.setCurrentRow(current_index)

    def remove_ip(self):
        """Remove the selected IP address"""
        current_item = self.ip_list.currentItem()
        if not current_item:
            return

        ip_to_remove = current_item.text()

        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{ip_to_remove}' from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.ips.remove(ip_to_remove)
            self.populate_ip_list()

    def get_ips(self):
        """Get the current list of IPs"""
        return self.ips.copy()

    def has_changes(self):
        """Check if any changes were made"""
        return self.ips != self.original_ips

    def accept(self):
        """Handle dialog acceptance"""
        if self.has_changes():
            self.ips_changed.emit()
        super().accept()
