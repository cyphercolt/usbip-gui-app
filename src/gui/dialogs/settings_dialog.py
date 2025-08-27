"""Settings dialog for configuring auto-reconnect, auto-refresh, and theme settings."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout, QCheckBox, QSpinBox,
    QLabel, QComboBox, QDialogButtonBox, QHBoxLayout
)
from PyQt6.QtCore import Qt
from styling.themes import ThemeManager


class SettingsDialog(QDialog):
    """Settings dialog for configuring application preferences."""
    
    def __init__(self, parent, initial_settings, theme_colors):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent widget
            initial_settings: Dictionary with current settings
            theme_colors: Theme color dictionary for styling
        """
        super().__init__(parent)
        self.parent_window = parent
        self.initial_settings = initial_settings
        self.theme_colors = theme_colors
        self.current_settings = initial_settings.copy()
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        # Apply initial theme styling
        self.apply_theme_styling()
        
        layout = QVBoxLayout(self)
        
        # Auto-Reconnect Group
        self.create_auto_reconnect_group(layout)
        
        # Auto-Refresh Group
        self.create_auto_refresh_group(layout)
        
        # Theme Group
        self.create_theme_group(layout)
        
        # Console Group
        self.create_console_group(layout)
        
        # Debug Group
        self.create_debug_group(layout)
        
        # Dialog buttons
        self.create_buttons(layout)
        
    def create_auto_reconnect_group(self, main_layout):
        """Create the auto-reconnect settings group."""
        reconnect_group = QGroupBox("Auto-Reconnect Settings")
        reconnect_layout = QFormLayout(reconnect_group)
        
        # Auto-reconnect enabled checkbox
        self.reconnect_enabled_input = QCheckBox()
        self.reconnect_enabled_input.setChecked(self.initial_settings['auto_reconnect_enabled'])
        reconnect_layout.addRow("Enable Auto-Reconnect:", self.reconnect_enabled_input)
        
        # Auto-reconnect interval setting
        self.interval_input = QSpinBox()
        self.interval_input.setRange(10, 300)  # 10 seconds to 5 minutes
        self.interval_input.setSuffix(" seconds")
        self.interval_input.setValue(self.initial_settings['auto_reconnect_interval'])
        reconnect_layout.addRow("Check Interval:", self.interval_input)
        
        # Max attempts setting
        self.attempts_input = QSpinBox()
        self.attempts_input.setRange(1, 10)
        self.attempts_input.setValue(self.initial_settings['auto_reconnect_max_attempts'])
        reconnect_layout.addRow("Max Attempts:", self.attempts_input)
        
        # Grace period setting
        self.grace_input = QSpinBox()
        self.grace_input.setRange(5, 60)  # 5 seconds to 1 minute
        self.grace_input.setSuffix(" seconds")
        self.grace_input.setValue(self.initial_settings['grace_period_duration'])
        reconnect_layout.addRow("Grace Period:", self.grace_input)
        
        # Auto-reconnect info label
        reconnect_info_label = QLabel(
            "Auto-reconnect will automatically reconnect devices that become disconnected. "
            "Grace period prevents immediate reconnection attempts."
        )
        reconnect_info_label.setWordWrap(True)
        reconnect_info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
        reconnect_layout.addRow(reconnect_info_label)
        
        main_layout.addWidget(reconnect_group)
        
    def create_auto_refresh_group(self, main_layout):
        """Create the auto-refresh settings group."""
        refresh_group = QGroupBox("Auto-Refresh Settings")
        refresh_layout = QFormLayout(refresh_group)
        
        # Auto-refresh enabled checkbox
        self.refresh_enabled_input = QCheckBox()
        self.refresh_enabled_input.setChecked(self.initial_settings['auto_refresh_enabled'])
        refresh_layout.addRow("Enable Auto-Refresh:", self.refresh_enabled_input)
        
        # Auto-refresh interval setting
        self.refresh_interval_input = QSpinBox()
        self.refresh_interval_input.setRange(30, 600)  # 30 seconds to 10 minutes
        self.refresh_interval_input.setSuffix(" seconds")
        self.refresh_interval_input.setValue(self.initial_settings['auto_refresh_interval'])
        refresh_layout.addRow("Refresh Interval:", self.refresh_interval_input)
        
        # Auto-refresh info label
        refresh_info_label = QLabel(
            "Auto-refresh will periodically refresh both local and SSH device tables "
            "to keep them up-to-date."
        )
        refresh_info_label.setWordWrap(True)
        refresh_info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
        refresh_layout.addRow(refresh_info_label)
        
        main_layout.addWidget(refresh_group)
        
    def create_theme_group(self, main_layout):
        """Create the theme settings group."""
        theme_group = QGroupBox("Theme Settings")
        theme_layout = QFormLayout(theme_group)
        
        # Theme selection combo box
        self.theme_input = QComboBox()
        self.theme_input.addItems(ThemeManager.get_available_themes())
        self.theme_input.setCurrentText(self.initial_settings['theme_setting'])
        theme_layout.addRow("Theme:", self.theme_input)
        
        # Theme info label
        theme_info_label = QLabel(
            "Choose your preferred theme. System Theme follows your OS settings, "
            "while other options force specific themes."
        )
        theme_info_label.setWordWrap(True)
        theme_info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
        theme_layout.addRow(theme_info_label)
        
        main_layout.addWidget(theme_group)
        
    def create_console_group(self, main_layout):
        """Create the console settings group."""
        console_group = QGroupBox("Console Settings")
        console_layout = QFormLayout(console_group)
        
        # Verbose console checkbox
        self.verbose_console_input = QCheckBox()
        self.verbose_console_input.setChecked(self.initial_settings.get('verbose_console', False))
        console_layout.addRow("Verbose Console:", self.verbose_console_input)
        
        # Console info label
        console_info_label = QLabel(
            "Enable to show detailed SSH commands and raw output. "
            "Disable for clean, emoji-enhanced messages only."
        )
        console_info_label.setWordWrap(True)
        console_info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
        console_layout.addRow(console_info_label)
        
        main_layout.addWidget(console_group)
        
    def create_debug_group(self, main_layout):
        """Create the debug settings group."""
        debug_group = QGroupBox("Debug & Development")
        debug_layout = QFormLayout(debug_group)
        
        # Debug mode checkbox
        self.debug_mode_input = QCheckBox()
        self.debug_mode_input.setChecked(self.initial_settings.get('debug_mode', False))
        debug_layout.addRow("Debug Mode:", self.debug_mode_input)
        
        # Debug info label
        debug_info_label = QLabel(
            "Enable to show debug tools like 'Test Colors' button and other development features. "
            "This is intended for testing and development purposes."
        )
        debug_info_label.setWordWrap(True)
        debug_info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
        debug_layout.addRow(debug_info_label)
        
        main_layout.addWidget(debug_group)
        
    def create_buttons(self, main_layout):
        """Create dialog buttons."""
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Apply | 
            QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self.buttons)
        
        # Connect signals
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.ok_clicked)
        self.buttons.rejected.connect(self.reject)
        
    def get_current_settings(self):
        """Get current settings from the form inputs."""
        return {
            'auto_reconnect_enabled': self.reconnect_enabled_input.isChecked(),
            'auto_reconnect_interval': self.interval_input.value(),
            'auto_reconnect_max_attempts': self.attempts_input.value(),
            'grace_period_duration': self.grace_input.value(),
            'auto_refresh_enabled': self.refresh_enabled_input.isChecked(),
            'auto_refresh_interval': self.refresh_interval_input.value(),
            'theme_setting': self.theme_input.currentText(),
            'verbose_console': self.verbose_console_input.isChecked(),
            'debug_mode': self.debug_mode_input.isChecked(),
        }
        
    def apply_settings(self):
        """Apply current settings without closing dialog."""
        new_settings = self.get_current_settings()
        
        # Store old values for comparison
        old_settings = {
            'auto_reconnect_enabled': self.parent_window.auto_reconnect_enabled,
            'auto_reconnect_interval': self.parent_window.auto_reconnect_interval,
            'auto_refresh_enabled': self.parent_window.auto_refresh_enabled,
            'auto_refresh_interval': self.parent_window.auto_refresh_interval,
            'theme_setting': self.parent_window.theme_setting,
            'verbose_console': getattr(self.parent_window, 'verbose_console', False),
            'debug_mode': getattr(self.parent_window, 'debug_mode', False),
        }
        
        # Update parent window settings
        self.parent_window.auto_reconnect_enabled = new_settings['auto_reconnect_enabled']
        self.parent_window.auto_reconnect_interval = new_settings['auto_reconnect_interval']
        self.parent_window.auto_reconnect_max_attempts = new_settings['auto_reconnect_max_attempts']
        self.parent_window.grace_period_duration = new_settings['grace_period_duration']
        self.parent_window.auto_refresh_enabled = new_settings['auto_refresh_enabled']
        self.parent_window.auto_refresh_interval = new_settings['auto_refresh_interval']
        self.parent_window.theme_setting = new_settings['theme_setting']
        
        # Handle verbose console changes
        if old_settings['verbose_console'] != new_settings['verbose_console']:
            self.parent_window.toggle_verbose_console(new_settings['verbose_console'])
            mode = "verbose" if new_settings['verbose_console'] else "simple"
            self.parent_window.append_simple_message(f"🔧 Console mode changed to: {mode}")
        
        # Handle debug mode changes
        old_debug_mode = getattr(self.parent_window, 'debug_mode', False)
        if old_debug_mode != new_settings['debug_mode']:
            self.parent_window.debug_mode = new_settings['debug_mode']
            self.parent_window.apply_debug_mode()
            mode = "enabled" if new_settings['debug_mode'] else "disabled"
            self.parent_window.append_simple_message(f"🐛 Debug mode {mode}")
        
        # Save settings
        self.parent_window.save_auto_reconnect_settings()
        
        # Apply theme if changed
        if old_settings['theme_setting'] != new_settings['theme_setting']:
            self.parent_window.apply_theme()
            self.parent_window.append_simple_message(f"🎨 Theme changed to: {new_settings['theme_setting']}")
            # Update this dialog's theme immediately
            self.refresh_dialog_theme()
        
        # Handle auto-reconnect enable/disable
        if old_settings['auto_reconnect_enabled'] != new_settings['auto_reconnect_enabled']:
            if new_settings['auto_reconnect_enabled']:
                self.parent_window.append_simple_message("▶️ Auto-reconnect enabled")
            else:
                self.parent_window.append_simple_message("⏸️ Auto-reconnect disabled")
        
        # Restart auto-reconnect timer if interval changed
        if old_settings['auto_reconnect_interval'] != new_settings['auto_reconnect_interval']:
            self.parent_window.auto_reconnect_timer.start(new_settings['auto_reconnect_interval'] * 1000)
        
        # Handle auto-refresh timer
        if old_settings['auto_refresh_enabled'] != new_settings['auto_refresh_enabled']:
            if new_settings['auto_refresh_enabled']:
                self.parent_window.auto_refresh_timer.start(new_settings['auto_refresh_interval'] * 1000)
                self.parent_window.console.append("🔄 Auto-refresh enabled")
            else:
                self.parent_window.auto_refresh_timer.stop()
                self.parent_window.console.append("⏸️ Auto-refresh disabled")
        elif (new_settings['auto_refresh_enabled'] and 
              old_settings['auto_refresh_interval'] != new_settings['auto_refresh_interval']):
            self.parent_window.auto_refresh_timer.start(new_settings['auto_refresh_interval'] * 1000)
        
    def ok_clicked(self):
        """Handle OK button click."""
        self.apply_settings()
        self.accept()

    def apply_theme_styling(self):
        """Apply theme styling to the dialog."""
        # For System Theme, clear any custom styling and use system defaults
        if self.parent_window.theme_setting == "System Theme":
            self.setStyleSheet("")  # Clear custom stylesheet to use system defaults
            return
        
        # For custom themes, apply the theme colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.theme_colors['bg_color']};
                color: {self.theme_colors['text_color']};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {self.theme_colors['border_color']};
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QLabel {{
                color: {self.theme_colors['text_color']};
            }}
            QCheckBox {{
                color: {self.theme_colors['text_color']};
            }}
            QSpinBox {{
                background-color: {self.theme_colors['bg_color']};
                color: {self.theme_colors['text_color']};
                border: 1px solid {self.theme_colors['border_color']};
                border-radius: 3px;
                padding: 5px;
            }}
            QComboBox {{
                background-color: {self.theme_colors['bg_color']};
                color: {self.theme_colors['text_color']};
                border: 1px solid {self.theme_colors['border_color']};
                border-radius: 3px;
                padding: 5px;
            }}
        """)

    def refresh_dialog_theme(self):
        """Refresh the dialog's theme colors and re-apply styling."""
        # Get fresh theme colors from parent window
        self.theme_colors = self.parent_window.get_theme_colors()
        # Re-apply the styling with new colors
        self.apply_theme_styling()
