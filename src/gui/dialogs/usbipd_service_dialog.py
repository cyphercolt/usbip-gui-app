"""
Windows usbipd Service Management Dialog

Provides a GUI interface for managing the Windows usbipd service
on remote Windows systems via SSH.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import paramiko
from utils.usbipd_service_manager import USBIPDServiceManager


class ServiceWorkerThread(QThread):
    """Worker thread for service operations to prevent UI blocking"""
    
    operation_complete = pyqtSignal(bool, str)
    
    def __init__(self, client, operation):
        super().__init__()
        self.client = client
        self.operation = operation
        
    def run(self):
        try:
            if self.operation == 'check_status':
                success, message = USBIPDServiceManager.check_service_status(self.client)
            elif self.operation == 'start':
                success, message = USBIPDServiceManager.start_service(self.client)
            elif self.operation == 'stop':
                success, message = USBIPDServiceManager.stop_service(self.client)
            elif self.operation == 'set_auto':
                success, message = USBIPDServiceManager.set_service_startup_auto(self.client)
            elif self.operation == 'check_install':
                success, message, version = USBIPDServiceManager.install_usbipd_check(self.client)
            else:
                success, message = False, "Unknown operation"
                
            self.operation_complete.emit(success, message)
        except Exception as e:
            self.operation_complete.emit(False, f"Operation failed: {str(e)}")


class USBIPDServiceDialog(QDialog):
    """Dialog for managing Windows usbipd service via SSH"""
    
    def __init__(self, parent=None, ip="", username="", password="", accept_fingerprint=True):
        super().__init__(parent)
        self.ip = ip
        self.username = username
        self.password = password
        self.accept_fingerprint = accept_fingerprint
        self.ssh_client = None
        self.worker_thread = None
        
        self.setWindowTitle(f"usbipd Service Manager - {ip}")
        self.setModal(True)
        self.resize(500, 400)
        
        self.setup_ui()
        self.connect_ssh()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Connection info
        connection_group = QGroupBox("Connection Information")
        connection_layout = QVBoxLayout(connection_group)
        connection_layout.addWidget(QLabel(f"Remote Host: {self.ip}"))
        connection_layout.addWidget(QLabel(f"Username: {self.username}"))
        layout.addWidget(connection_group)
        
        # Service status
        self.status_group = QGroupBox("Service Status")
        status_layout = QVBoxLayout(self.status_group)
        self.status_label = QLabel("Checking service status...")
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_group)
        
        # Service controls
        controls_group = QGroupBox("Service Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Service")
        self.start_button.clicked.connect(self.start_service)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Service")
        self.stop_button.clicked.connect(self.stop_service)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_status)
        button_layout.addWidget(self.refresh_button)
        
        controls_layout.addLayout(button_layout)
        
        # Auto-start option
        auto_layout = QHBoxLayout()
        self.auto_start_button = QPushButton("Set Auto-Start")
        self.auto_start_button.clicked.connect(self.set_auto_start)
        self.auto_start_button.setEnabled(False)
        auto_layout.addWidget(self.auto_start_button)
        auto_layout.addStretch()
        controls_layout.addLayout(auto_layout)
        
        layout.addWidget(controls_group)
        
        # Output log
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)
        
    def connect_ssh(self):
        """Establish SSH connection"""
        try:
            self.log_text.append(f"Connecting to {self.ip}...")
            
            self.ssh_client = paramiko.SSHClient()
            if self.accept_fingerprint:
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                self.ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
                
            self.ssh_client.connect(
                self.ip, 
                username=self.username, 
                password=self.password, 
                timeout=10
            )
            
            self.log_text.append("✅ SSH connection established")
            self.check_installation()
            
        except Exception as e:
            self.log_text.append(f"❌ SSH connection failed: {str(e)}")
            QMessageBox.critical(self, "Connection Error", 
                               f"Failed to connect to {self.ip}:\n{str(e)}")
            
    def check_installation(self):
        """Check if usbipd is installed"""
        if not self.ssh_client:
            return
            
        self.worker_thread = ServiceWorkerThread(self.ssh_client, 'check_install')
        self.worker_thread.operation_complete.connect(self.on_installation_checked)
        self.worker_thread.start()
        
    def on_installation_checked(self, success, message):
        """Handle installation check result"""
        if success:
            self.log_text.append(f"✅ {message}")
            self.refresh_status()
        else:
            self.log_text.append(f"❌ {message}")
            self.status_label.setText("usbipd not available")
            
    def refresh_status(self):
        """Refresh service status"""
        if not self.ssh_client:
            return
            
        self.status_label.setText("Checking service status...")
        self.disable_buttons()
        
        self.worker_thread = ServiceWorkerThread(self.ssh_client, 'check_status')
        self.worker_thread.operation_complete.connect(self.on_status_checked)
        self.worker_thread.start()
        
    def on_status_checked(self, is_running, message):
        """Handle status check result"""
        self.log_text.append(f"ℹ️ {message}")
        
        if is_running:
            self.status_label.setText("🟢 Service is RUNNING")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.status_label.setText("🔴 Service is STOPPED")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        self.auto_start_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        
    def start_service(self):
        """Start the usbipd service"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Starting usbipd service...")
        self.disable_buttons()
        
        self.worker_thread = ServiceWorkerThread(self.ssh_client, 'start')
        self.worker_thread.operation_complete.connect(self.on_service_started)
        self.worker_thread.start()
        
    def on_service_started(self, success, message):
        """Handle service start result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Refresh status after operation
        self.refresh_status()
        
    def stop_service(self):
        """Stop the usbipd service"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Stopping usbipd service...")
        self.disable_buttons()
        
        self.worker_thread = ServiceWorkerThread(self.ssh_client, 'stop')
        self.worker_thread.operation_complete.connect(self.on_service_stopped)
        self.worker_thread.start()
        
    def on_service_stopped(self, success, message):
        """Handle service stop result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Refresh status after operation
        self.refresh_status()
        
    def set_auto_start(self):
        """Set service to start automatically"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Setting service to auto-start...")
        self.disable_buttons()
        
        self.worker_thread = ServiceWorkerThread(self.ssh_client, 'set_auto')
        self.worker_thread.operation_complete.connect(self.on_auto_start_set)
        self.worker_thread.start()
        
    def on_auto_start_set(self, success, message):
        """Handle auto-start configuration result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        self.enable_buttons()
        
    def disable_buttons(self):
        """Disable all service control buttons"""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.auto_start_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        
    def enable_buttons(self):
        """Enable appropriate service control buttons"""
        self.refresh_button.setEnabled(True)
        # Other buttons will be enabled based on status check
        
    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
            
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
                
        event.accept()
