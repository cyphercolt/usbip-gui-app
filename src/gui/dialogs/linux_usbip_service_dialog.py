"""
Linux USB/IP Service Management Dialog

Provides a GUI interface for managing the Linux USB/IP daemon and kernel modules
on remote Linux systems via SSH.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import paramiko
from utils.linux_usbip_service_manager import LinuxUSBIPServiceManager


class LinuxServiceWorkerThread(QThread):
    """Worker thread for Linux service operations to prevent UI blocking"""
    
    operation_complete = pyqtSignal(bool, str)
    status_checked = pyqtSignal(bool, str, bool)  # is_operational, message, daemon_running
    
    def __init__(self, client, operation, password=None):
        super().__init__()
        self.client = client
        self.operation = operation
        self.password = password
        
    def run(self):
        try:
            if self.operation == 'check_status':
                is_operational, message, daemon_running = LinuxUSBIPServiceManager.check_service_status(self.client, self.password)
                self.status_checked.emit(is_operational, message, daemon_running)
                return
            elif self.operation == 'start':
                success, message = LinuxUSBIPServiceManager.start_service(self.client, self.password)
            elif self.operation == 'stop':
                success, message = LinuxUSBIPServiceManager.stop_service(self.client, self.password)
            elif self.operation == 'enable_auto':
                success, message = LinuxUSBIPServiceManager.enable_auto_start(self.client, self.password)
            elif self.operation == 'disable_auto':
                success, message = LinuxUSBIPServiceManager.disable_auto_start(self.client, self.password)
            elif self.operation == 'check_install':
                success, message, version = LinuxUSBIPServiceManager.check_installation(self.client)
            elif self.operation == 'load_modules':
                success, message = LinuxUSBIPServiceManager.load_kernel_modules(self.client, self.password)
            elif self.operation == 'unload_modules':
                success, message = LinuxUSBIPServiceManager.unload_kernel_modules(self.client, self.password)
            else:
                success, message = False, "Unknown operation"
                
            self.operation_complete.emit(success, message)
        except Exception as e:
            self.operation_complete.emit(False, f"Operation failed: {str(e)}")


class LinuxUSBIPServiceDialog(QDialog):
    """Dialog for managing Linux USB/IP service via SSH"""
    
    def __init__(self, parent=None, ip="", username="", password="", accept_fingerprint=True):
        super().__init__(parent)
        self.ip = ip
        self.username = username
        self.password = password
        self.accept_fingerprint = accept_fingerprint
        self.ssh_client = None
        self.worker_thread = None
        
        self.setWindowTitle(f"Linux USB/IP Service Manager - {ip}")
        self.setModal(True)
        self.resize(600, 500)
        
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
        self.status_group = QGroupBox("USB/IP Service Status")
        status_layout = QVBoxLayout(self.status_group)
        self.status_label = QLabel("Checking USB/IP service status...")
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_group)
        
        # Service controls
        controls_group = QGroupBox("Service Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Main service buttons
        service_button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Daemon")
        self.start_button.clicked.connect(self.start_service)
        self.start_button.setEnabled(False)
        service_button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Daemon")
        self.stop_button.clicked.connect(self.stop_service)
        self.stop_button.setEnabled(False)
        service_button_layout.addWidget(self.stop_button)
        
        self.refresh_button = QPushButton("Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_status)
        service_button_layout.addWidget(self.refresh_button)
        
        controls_layout.addLayout(service_button_layout)
        
        # Auto-start controls
        auto_layout = QHBoxLayout()
        self.enable_auto_button = QPushButton("Enable Auto-Start")
        self.enable_auto_button.clicked.connect(self.enable_auto_start)
        self.enable_auto_button.setEnabled(False)
        auto_layout.addWidget(self.enable_auto_button)
        
        self.disable_auto_button = QPushButton("Disable Auto-Start")
        self.disable_auto_button.clicked.connect(self.disable_auto_start)
        self.disable_auto_button.setEnabled(False)
        auto_layout.addWidget(self.disable_auto_button)
        
        controls_layout.addLayout(auto_layout)
        
        # Kernel module controls
        module_layout = QHBoxLayout()
        self.load_modules_button = QPushButton("Load Kernel Modules")
        self.load_modules_button.clicked.connect(self.load_modules)
        self.load_modules_button.setEnabled(False)
        module_layout.addWidget(self.load_modules_button)
        
        self.unload_modules_button = QPushButton("Unload Kernel Modules")
        self.unload_modules_button.clicked.connect(self.unload_modules)
        self.unload_modules_button.setEnabled(False)
        module_layout.addWidget(self.unload_modules_button)
        
        controls_layout.addLayout(module_layout)
        
        layout.addWidget(controls_group)
        
        # Output log
        log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
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
        """Check if USB/IP is installed"""
        if not self.ssh_client:
            return
            
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'check_install')
        self.worker_thread.operation_complete.connect(self.on_installation_checked)
        self.worker_thread.start()
        
    def on_installation_checked(self, success, message):
        """Handle installation check result"""
        if success:
            self.log_text.append(f"✅ {message}")
            self.refresh_status()
        else:
            self.log_text.append(f"❌ {message}")
            self.status_label.setText("USB/IP not available or incomplete installation")
            
    def refresh_status(self):
        """Refresh service status"""
        if not self.ssh_client:
            return
            
        self.status_label.setText("Checking USB/IP service status...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'check_status', self.password)
        self.worker_thread.status_checked.connect(self.on_status_checked)
        self.worker_thread.start()
        
    def on_status_checked(self, is_operational, message, daemon_running):
        """Handle status check result"""
        self.log_text.append(f"ℹ️ Service Status:")
        for line in message.split('\\n'):
            self.log_text.append(f"  {line}")
        
        # Status message based on daemon running status
        if daemon_running:
            self.status_label.setText("🟢 USB/IP Daemon: OPERATIONAL")
        else:
            # Check if it's in a transition state
            if "STARTING" in message or "STOPPING" in message:
                self.status_label.setText("� USB/IP Daemon: TRANSITIONING")
            else:
                self.status_label.setText("�🔴 USB/IP Daemon: OFFLINE")
            
        # Button logic based on daemon running status
        if daemon_running:
            # Daemon is running - enable stop, disable start
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            # Daemon is stopped/stopping/starting - enable start, disable stop
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        self.enable_auto_button.setEnabled(True)
        self.disable_auto_button.setEnabled(True)
        self.load_modules_button.setEnabled(True)
        self.unload_modules_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        
    def start_service(self):
        """Start the USB/IP daemon"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Starting USB/IP daemon...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'start', self.password)
        self.worker_thread.operation_complete.connect(self.on_service_started)
        self.worker_thread.start()
        
    def on_service_started(self, success, message):
        """Handle service start result"""
        if success:
            self.log_text.append(f"✅ Service Start Result:")
            for line in message.split('\\n'):
                self.log_text.append(f"  {line}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Add a small delay before refreshing to let systemd update status
        QTimer.singleShot(1000, self.refresh_status)  # Wait 1 second then refresh
        
    def stop_service(self):
        """Stop the USB/IP daemon"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Stopping USB/IP daemon...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'stop', self.password)
        self.worker_thread.operation_complete.connect(self.on_service_stopped)
        self.worker_thread.start()
        
    def on_service_stopped(self, success, message):
        """Handle service stop result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Add a small delay before refreshing to let systemd update status
        QTimer.singleShot(1000, self.refresh_status)  # Wait 1 second then refresh
        
    def enable_auto_start(self):
        """Enable service to start automatically"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Enabling USB/IP daemon auto-start...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'enable_auto', self.password)
        self.worker_thread.operation_complete.connect(self.on_auto_start_enabled)
        self.worker_thread.start()
        
    def on_auto_start_enabled(self, success, message):
        """Handle auto-start enable result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        self.enable_buttons()
        
    def disable_auto_start(self):
        """Disable service auto-start"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Disabling USB/IP daemon auto-start...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'disable_auto', self.password)
        self.worker_thread.operation_complete.connect(self.on_auto_start_disabled)
        self.worker_thread.start()
        
    def on_auto_start_disabled(self, success, message):
        """Handle auto-start disable result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        self.enable_buttons()
        
    def load_modules(self):
        """Load USB/IP kernel modules"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Loading USB/IP kernel modules...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'load_modules', self.password)
        self.worker_thread.operation_complete.connect(self.on_modules_loaded)
        self.worker_thread.start()
        
    def on_modules_loaded(self, success, message):
        """Handle module load result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Refresh status after module operation
        self.refresh_status()
        
    def unload_modules(self):
        """Unload USB/IP kernel modules"""
        if not self.ssh_client:
            return
            
        self.log_text.append("Unloading USB/IP kernel modules...")
        self.disable_buttons()
        
        self.worker_thread = LinuxServiceWorkerThread(self.ssh_client, 'unload_modules', self.password)
        self.worker_thread.operation_complete.connect(self.on_modules_unloaded)
        self.worker_thread.start()
        
    def on_modules_unloaded(self, success, message):
        """Handle module unload result"""
        if success:
            self.log_text.append(f"✅ {message}")
        else:
            self.log_text.append(f"❌ {message}")
            
        # Refresh status after module operation
        self.refresh_status()
        
    def disable_buttons(self):
        """Disable all service control buttons"""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.enable_auto_button.setEnabled(False)
        self.disable_auto_button.setEnabled(False)
        self.load_modules_button.setEnabled(False)
        self.unload_modules_button.setEnabled(False)
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
