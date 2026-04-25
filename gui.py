"""
DualSense Controller Viewer — Premium GUI
Professional CustomTkinter interface with PlayStation button labels and multi-controller support.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser
import json
import os
import sys
import threading
from typing import Optional

from multi_manager import MultiControllerManager, ControllerSlot


# ═══════════════════════════════════════════════════════════
# Color Palette — PlayStation Inspired
# ═══════════════════════════════════════════════════════════
class Colors:
    BG_DARK = "#0a0a12"
    BG_CARD = "#13131f"
    BG_CARD_HOVER = "#1a1a2e"
    BG_INPUT = "#0e0e18"
    BORDER = "#1e1e30"
    BORDER_ACTIVE = "#0072CE"

    TEXT_PRIMARY = "#e0e0f0"
    TEXT_SECONDARY = "#7878a0"
    TEXT_DIM = "#4a4a6a"

    PS_BLUE = "#0072CE"
    PS_BLUE_DARK = "#004A8F"
    PS_ACCENT = "#00D4FF"

    TRIANGLE_GREEN = "#3ddc84"
    CIRCLE_RED = "#ff6b6b"
    CROSS_BLUE = "#69a5ff"
    SQUARE_PINK = "#e879a8"

    TRIANGLE_GREEN_DIM = "#152a1e"
    CIRCLE_RED_DIM = "#2a1616"
    CROSS_BLUE_DIM = "#151d2a"
    SQUARE_PINK_DIM = "#2a1520"

    TRIANGLE_GREEN_BG = "#1a3d28"
    CIRCLE_RED_BG = "#3d1a1a"
    CROSS_BLUE_BG = "#1a253d"
    SQUARE_PINK_BG = "#3d1a2a"

    SUCCESS = "#3ddc84"
    WARNING = "#ffb74d"
    ERROR = "#ff6b6b"


# ═══════════════════════════════════════════════════════════
# Localization
# ═══════════════════════════════════════════════════════════
TRANSLATIONS = {
    "tr": {
        "title": "Universal Gamepad",
        "connect": "Bağlan",
        "disconnect": "Bağlantıyı Kes",
        "status_idle": "Bağlı Değil",
        "status_connected": "Bağlı",
        "status_cleaning": "Temizleniyor...",
        "status_clean": "Sürücü Temiz! Yeniden Başlatılıyor...",
        "status_error": "Hata! (Admin?)",
        "settings": "Ayarlar",
        "language": "Dil Seçimi",
        "driver_reset": "Sürücüyü Resetle",
        "requirements": "Gerekli Uygulamalar",
        "hide_warning": "Sürücü Uyarısını Gizle",
        "show_warning": "Sürücü Uyarısını Göster",
        "vigem_desc": "ViGEmBus Sürücüsü (Gerekli)",
        "download": "İndir",
        "vibration_test": "Titreşim Testi",
        "mode_label": "Emülasyon Modu:",
        "back": "Geri Dön",
        "driver_missing": "Sürücü Eksik veya Hatalı!",
        "settings_desc": "Uygulama tercihlerini ve sürücü ayarlarını buradan yönetebilirsiniz.",
        "connected_count": "Bağlı Kol Sayısı",
        "disconnect_all": "Tüm Bağlantıları Kes",
        "default_mode": "Varsayılan Oyun Modu",
        "detected_controllers": "Bulunan Kollar",
        "connect_desc": "USB / Bluetooth (Max 2)",
        "touchpad": "DOKUNMATİK PANEL",
        "left_analog": "SOL ANALOG",
        "right_analog": "SAĞ ANALOG",
        "action_buttons": "AKSİYON BUTONLARI",
        "swap_triggers": "L1/R1 ile L2/R2 Yer Değiştir",
        "controller_name": "Kol İsmi",
        "controller_prefix": "Kol",
        "controller_mode": "Kontrolcü Modu",
        "last_pressed": "SON BASILANLAR",
        "start_pressing": "Bir butona basarak başlayın...",
        "direct": "Direkt",
        "led_color": "LED Rengi",
        "led_desc": "DualSense ışık çubuğunun rengini değiştirin.",
    },
    "en": {
        "title": "Universal Gamepad",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "status_idle": "Idle",
        "status_connected": "Connected",
        "status_cleaning": "Cleaning...",
        "status_clean": "Driver Cleaned! Restarting...",
        "status_error": "Error! (Admin?)",
        "settings": "Settings",
        "language": "Language",
        "driver_reset": "Reset Driver",
        "requirements": "Required Drivers",
        "hide_warning": "Hide Driver Warning",
        "show_warning": "Show Driver Warning",
        "vigem_desc": "ViGEmBus Driver (Required)",
        "download": "Download",
        "vibration_test": "Vibration Test",
        "mode_label": "Emulation Mode:",
        "back": "Go Back",
        "driver_missing": "Driver Missing or Error!",
        "settings_desc": "Manage application preferences and driver settings here.",
        "connected_count": "Connected Controllers",
        "disconnect_all": "Disconnect All",
        "default_mode": "Default Gaming Mode",
        "detected_controllers": "Detected Controllers",
        "connect_desc": "USB / Bluetooth (Max 2)",
        "touchpad": "TOUCHPAD PANEL",
        "left_analog": "LEFT ANALOG",
        "right_analog": "RIGHT ANALOG",
        "action_buttons": "ACTION BUTTONS",
        "swap_triggers": "Swap L1/R1 with L2/R2",
        "controller_name": "Controller Name",
        "controller_prefix": "Slot",
        "controller_mode": "Controller Mode",
        "last_pressed": "LAST PRESSED",
        "start_pressing": "Press a button to start...",
        "direct": "Direct",
        "led_color": "LED Color",
        "led_desc": "Change the DualSense lightbar color.",
    }
}

# ═══════════════════════════════════════════════════════════
# Main Application GUI
# ═══════════════════════════════════════════════════════════
class DualSenseGUI(ctk.CTk):
    # Fix: Save settings next to the EXE, not in a temp folder
    _script_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    SETTINGS_PATH = os.path.join(_script_dir, "app_settings.json")
    
    MODE_VALUES = {
        "Direct": 0,
        "Direkt": 0,
        "PS4": 1,
        "Xbox": 2,
    }

    def __init__(self):
        super().__init__()

        # Multi-Controller Manager
        self.manager = MultiControllerManager()
        self.manager.set_on_state_change(self._on_state_update)
        self.manager.set_on_connection_change(self._on_connection_change)

        # Window Setup
        self.title("Gamepad PC Manager — Multi-Controller")
        self.geometry("1080x760")
        self.minsize(960, 680)
        self.configure(fg_color=Colors.BG_DARK)

        # CustomTkinter Theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # State
        self._gui_update_pending = False
        self._slot_indicators = {}  # slot_idx -> dict of widgets
        self._log_items = {}        # slot_idx -> list
        self._prev_log_state = {}   # slot_idx -> dict
        
        self._selected_mode = "Xbox"
        self._connect_in_progress = False
        self._lang = "en"
        self._show_warning_panel = True
        self._in_settings = False
        self._led_color = "#0072CE" # Default PS Blue
        self._load_settings()

        # Build UI
        self._build_header()
        self._build_main_content()
        self._build_footer()

        # Protocol for close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Resize debouncing state
        self._resize_timer = None
        self._is_resizing = False
        self.bind("<Configure>", self._on_configure)

        # Auto-connect attempt
        self.after(500, self._try_auto_connect)
        
        # Start Pygame SDL event pump on main thread (8ms = 125Hz)
        self._pump_pygame()

        # Check for ViGEmBus driver
        self.after(1000, self._check_driver_requirement)

    def _check_driver_requirement(self):
        import driver_setup
        if not driver_setup.check_vigembus():
            # Show the warning button in the header (visible even after auto-connect)
            if hasattr(self, "_req_warning_btn_header") and self._req_warning_btn_header.winfo_exists():
                self._req_warning_btn_header.pack(side="right", padx=(15, 0))

    def _on_reset_driver_click(self):
        import subprocess
        try:
            self._status_label.configure(text="Baglantilar Kesiliyor...")
            self.manager.disconnect_all() # Important: release handles before reset
            
            self._status_label.configure(text="Temizleniyor...")
            cmd = 'powershell -Command "Get-PnpDevice -FriendlyName \'*Nefarius Virtual Gamepad Emulation Bus*\' | Disable-PnpDevice -Confirm:$false; Start-Sleep -s 1; Get-PnpDevice -FriendlyName \'*Nefarius Virtual Gamepad Emulation Bus*\' | Enable-PnpDevice -Confirm:$false"'
            subprocess.run(cmd, shell=True, check=True)
            self._status_label.configure(text="Sürücü Temiz! Yeniden Baslatiliyor...")
            
            # Auto-restart the app to pick up the clean state
            self.after(1500, self._restart_app)
        except Exception as e:
            print(f"Reset error: {e}")
            self._status_label.configure(text="Hata! (Admin?)")

    def _restart_app(self):
        import sys
        import os
        try:
            # Re-run the current script
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception:
            sys.exit(0)

    def _t(self, key):
        """Translation helper."""
        return TRANSLATIONS[self._lang].get(key, key)

    def _on_lang_change(self, lang):
        self._lang = lang
        self._save_settings()
        # Rebuild EVERYTHING to update all labels
        self._build_header()
        self._build_main_content()
        self._build_footer()
        self._update_status_label()

    def _toggle_settings(self):
        self._in_settings = not self._in_settings
        self._build_main_content()

    def _toggle_warning_setting(self):
        self._show_warning_panel = not self._show_warning_panel
        self._build_main_content()

    def _show_requirements_popup(self):
        import webbrowser
        import customtkinter as ctk
        
        # Create a small custom popup
        pop = ctk.CTkToplevel(self)
        pop.title("Gerekli Bileşenler")
        pop.geometry("400x250")
        pop.attributes("-topmost", True)
        pop.grab_set() # Modal
        
        ctk.CTkLabel(pop, text="⚠️ Eksik Sistem Bileşenleri", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        ctk.CTkLabel(pop, text="Uygulamanın çalışması için aşağıdaki sürücü şarttır:", font=ctk.CTkFont(size=12)).pack(pady=(0, 10))
        
        # Link label style
        link = ctk.CTkLabel(
            pop, text="• ViGEmBus Sürücüsü (İndirmek için Tıkla)", 
            font=ctk.CTkFont(size=13, underline=True),
            text_color=Colors.PS_BLUE, cursor="hand2"
        )
        link.pack(pady=10)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/ViGEm/ViGEmBus/releases/latest"))
        
        ctk.CTkButton(pop, text="Kapat", width=100, command=pop.destroy).pack(pady=20)

    def _start_driver_install(self):
        import driver_setup
        import threading
        
        # Simple loading overlay or just a status message
        self._status_label.configure(text="Sürücü indiriliyor... Lütfen bekleyin.", text_color="#FFCC00")
        
        def run():
            success, message = driver_setup.install_logic()
            self.after(0, lambda: self._on_driver_install_done(success, message))
        
        threading.Thread(target=run, daemon=True).start()

    def _on_driver_install_done(self, success, message):
        from tkinter import messagebox
        if success:
            if hasattr(self, "_req_warning_btn"):
                self._req_warning_btn.pack_forget()
            messagebox.showinfo("Başarılı", "Sürücü başarıyla indirildi. Lütfen az önce açılan yükleme penceresindeki adımları tamamlayın ve bilgisayarınızı yeniden başlatın.")
            self._status_label.configure(text="Sürücü indirildi. Lütfen kurun ve yeniden başlatın.", text_color="#00FF00")
        else:
            messagebox.showerror("Hata", f"Sürücü indirilemedi: {message}")
            self._status_label.configure(text="Sürücü hatası! Manuel kurulum gerekebilir.", text_color="#FF0000")

    def _on_configure(self, event):
        # Only care about main window configure, not inner widgets
        if event.widget == self:
            self._is_resizing = True
            self.manager.paused = True # Pause background thread during resize/drag
            if self._resize_timer is not None:
                try:
                    self.after_cancel(self._resize_timer)
                except:
                    pass
            self._resize_timer = self.after(300, self._end_resize)

    def _end_resize(self):
        self._is_resizing = False
        self.manager.paused = False # Resume background thread
        self._resize_timer = None

    def _pump_pygame(self):
        # Pause pump during resize to prevent Windows modal loop crashes
        if not self._is_resizing:
            self.manager.pump_events()
        self.after(10, self._pump_pygame)

    def _build_header(self):
        if hasattr(self, "_header_frame"):
            self._header_frame.destroy()
            
        self._header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0, height=60)
        self._header_frame.pack(fill="x", padx=0, pady=0, side="top")
        self._header_frame.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self._header_frame, fg_color="transparent")
        logo_frame.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(logo_frame, text="🎮", font=ctk.CTkFont(size=24), width=40).pack(side="left", padx=(0, 10))

        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(title_frame, text=self._t("title"), font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="PC CONTROLLER MANAGER", font=ctk.CTkFont(family="Inter", size=9), text_color=Colors.TEXT_DIM).pack(anchor="w")

        # Settings Button - High visibility
        self._settings_btn = ctk.CTkButton(
            self._header_frame, text="⚙️ " + self._t("settings"), font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=Colors.BG_CARD_HOVER, hover_color=Colors.PS_BLUE, corner_radius=8, height=32, width=100,
            command=self._toggle_settings
        )
        self._settings_btn.pack(side="right", padx=20)

        status_frame = ctk.CTkFrame(self._header_frame, fg_color="transparent")
        status_frame.pack(side="right", padx=10)

        self._status_dot = ctk.CTkLabel(status_frame, text="●", font=ctk.CTkFont(size=12), text_color=Colors.ERROR, width=20)
        self._status_dot.pack(side="left", padx=(0, 6))

        self._status_label = ctk.CTkLabel(status_frame, text=self._t("status_idle"), font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=Colors.TEXT_SECONDARY)
        self._status_label.pack(side="left")
        
        # FIX: Check current connection state and update status labels immediately
        if self.manager.connected_count > 0:
            self._status_dot.configure(text_color=Colors.SUCCESS)
            status_text = (f"Connected ({self.manager.connected_count})" if self._lang == "en" else f"Bağlı ({self.manager.connected_count})")
            self._status_label.configure(text=status_text, text_color=Colors.SUCCESS)

    def _build_main_content(self):
        if hasattr(self, "_main_container"):
            self._main_container.destroy()

        self._main_container = ctk.CTkFrame(self, fg_color="transparent")
        self._main_container.pack(fill="both", expand=True, padx=16, pady=12)
        
        if self._in_settings:
            self._build_settings_view()
        elif not self.manager.is_driver_installed() and self._show_warning_panel:
            self._build_requirements_panel()
        elif not self.manager.slots:
            self._build_connect_screen()
        else:
            self._build_multi_controller_view()

    def _build_connect_screen(self):
        for widget in self._main_container.winfo_children():
            widget.destroy()

        self._connect_frame = ctk.CTkFrame(self._main_container, fg_color="transparent")
        self._connect_frame.pack(fill="both", expand=True)

        card = ctk.CTkFrame(self._connect_frame, fg_color=Colors.BG_CARD, corner_radius=16, border_width=1, border_color=Colors.BORDER)
        card.place(relx=0.5, rely=0.45, anchor="center")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=60, pady=50)

        ctk.CTkLabel(inner, text="🎮", font=ctk.CTkFont(size=64)).pack(pady=(0, 16))
        ctk.CTkLabel(inner, text=self._t("connect"), font=ctk.CTkFont(family="Inter", size=22, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(pady=(0, 8))
        ctk.CTkLabel(inner, text=self._t("connect_desc"), font=ctk.CTkFont(family="Inter", size=13), text_color=Colors.TEXT_SECONDARY).pack(pady=(0, 24))

        ctk.CTkLabel(inner, text=self._t("default_mode"), font=ctk.CTkFont(family="Inter", size=11, weight="bold"), text_color=Colors.TEXT_SECONDARY).pack(pady=(0, 8))

        self._connect_mode_selector = ctk.CTkSegmentedButton(
            inner, values=[self._t("direct"), "PS4", "Xbox"], command=self._on_preferred_mode_selected,
            selected_color=Colors.PS_BLUE_DARK, selected_hover_color=Colors.PS_BLUE,
            unselected_color=Colors.BG_INPUT, unselected_hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_PRIMARY, width=320
        )
        self._connect_mode_selector.pack(pady=(0, 12))
        self._connect_mode_selector.set(self._selected_mode)

        self._connect_btn = ctk.CTkButton(
            inner, text="🔌  " + self._t("connect"), font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            fg_color=Colors.PS_BLUE, hover_color=Colors.PS_BLUE_DARK, corner_radius=12, height=48, width=250,
            command=self._on_connect_click
        )
        self._connect_btn.pack(pady=(0, 20))

        self._connect_msg = ctk.CTkLabel(inner, text="", font=ctk.CTkFont(family="Inter", size=11), text_color=Colors.TEXT_DIM, wraplength=350)
        self._connect_msg.pack()

        # Requirements Warning Button (Only shows if missing)
        self._req_warning_btn = ctk.CTkButton(
            inner, text="⚠️ GEREKLİ BİLEŞENLER EKSİK", font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color="#CC3300", hover_color="#992200", corner_radius=8, height=32,
            command=self._show_requirements_popup
        )
        # We'll pack it conditionally in _check_driver_requirement

        # Show detected controllers
        detected = self.manager.scan()
        if detected:
            det_frame = ctk.CTkFrame(inner, fg_color="transparent")
            det_frame.pack(pady=(15, 0))
            ctk.CTkLabel(det_frame, text=f"{self._t('detected_controllers')} ({len(detected)}):", font=ctk.CTkFont(size=11, weight="bold"), text_color=Colors.SUCCESS).pack()
            for d in detected[:2]:
                ctk.CTkLabel(det_frame, text=f"• {d['name']}", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_PRIMARY).pack()

        req_frame = ctk.CTkFrame(inner, fg_color="transparent")
        req_frame.pack(pady=(20, 0))
        deps = [("vgamepad (Sanal Kol Sürücüsü)", self.manager.has_vgamepad)]
        for name, installed in deps:
            dep_row = ctk.CTkFrame(req_frame, fg_color="transparent")
            dep_row.pack(anchor="w", pady=2)
            status_icon = "✅" if installed else "❌"
            color = Colors.SUCCESS if installed else Colors.ERROR
            ctk.CTkLabel(dep_row, text=f"{status_icon} {name}", font=ctk.CTkFont(family="Inter", size=11), text_color=color).pack(side="left")

    def _load_settings(self):
        try:
            with open(self.SETTINGS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                self._lang = data.get("lang", "en")
                self._show_warning_panel = data.get("show_warning", True)
                self._selected_mode = data.get("preferred_mode", "Xbox")
                self._led_color = data.get("led_color", "#0072CE")
                
                # Apply to manager
                self._apply_led_color()
        except Exception:
            pass

    def _save_settings(self):
        try:
            data = {
                "preferred_mode": self._selected_mode,
                "lang": self._lang,
                "show_warning": self._show_warning_panel,
                "led_color": self._led_color
            }
            with open(self.SETTINGS_PATH, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_color_light(self, hex_color):
        """Returns True if the color is light (for text contrast)."""
        try:
            hex_c = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
            # Perceptual brightness formula
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness > 128
        except: return False

    def _apply_led_color(self):
        """Converts the stored hex color to RGB and applies it to all controller slots."""
        try:
            hex_c = self._led_color.lstrip('#')
            r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
            for slot in self.manager.slots:
                slot.set_led_color(r, g, b)
        except Exception as e:
            print(f"[DEBUG] Error applying LED color: {e}")

    def _open_color_picker(self):
        """Opens the system color picker dialog."""
        color = colorchooser.askcolor(initialcolor=self._led_color, title=self._t("led_color"))
        if color[1]:
            self._on_led_color_change(color[1])

    def _on_led_color_change(self, color_hex):
        """Handler for LED color selection."""
        self._led_color = color_hex
        self._save_settings()
        self._apply_led_color()
        # Refresh the view to update sliders and indicators
        self._build_main_content()

    def _build_settings_view(self):
        # Header for settings
        header = ctk.CTkFrame(self._main_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        back_btn = ctk.CTkButton(
            header, text="← " + self._t("back"), font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=Colors.BG_CARD_HOVER, hover_color=Colors.PS_BLUE, corner_radius=10, width=120, height=36,
            command=self._toggle_settings
        )
        back_btn.pack(side="left")

        title = ctk.CTkLabel(header, text=self._t("settings"), font=ctk.CTkFont(family="Inter", size=24, weight="bold"), text_color=Colors.TEXT_PRIMARY)
        title.pack(side="left", padx=20)

        # Content area (no scroll for better visibility)
        content_scroll = ctk.CTkFrame(self._main_container, fg_color="transparent")
        content_scroll.pack(fill="both", expand=True)

        # Language Section
        lang_frame = self._build_settings_card(content_scroll, self._t("language"), "🌐")
        btn_tr = ctk.CTkButton(
            lang_frame, text="Türkçe 🇹🇷", font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=Colors.PS_BLUE if self._lang == "tr" else Colors.BG_DARK,
            hover_color=Colors.PS_BLUE_DARK, corner_radius=8, width=120, height=36,
            command=lambda: self._on_lang_change("tr")
        )
        btn_tr.pack(side="left", padx=10, pady=10)

        btn_en = ctk.CTkButton(
            lang_frame, text="English 🇺🇸", font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=Colors.PS_BLUE if self._lang == "en" else Colors.BG_DARK,
            hover_color=Colors.PS_BLUE_DARK, corner_radius=8, width=120, height=36,
            command=lambda: self._on_lang_change("en")
        )
        btn_en.pack(side="left", padx=10, pady=10)

        # LED Color Section
        led_frame = self._build_settings_card(content_scroll, self._t("led_color"), "🌈")
        ctk.CTkLabel(led_frame, text=self._t("led_desc"), font=ctk.CTkFont(family="Inter", size=11), text_color=Colors.TEXT_DIM).pack(padx=10, anchor="w")
        
        main_led_row = ctk.CTkFrame(led_frame, fg_color="transparent")
        main_led_row.pack(fill="x", padx=10, pady=15)

        # Left: Presets
        presets_frame = ctk.CTkFrame(main_led_row, fg_color="transparent")
        presets_frame.pack(side="left")
        
        presets = [("#0072CE", "B"), ("#FF3333", "R"), ("#33FF33", "G"), ("#FF33FF", "P"), ("#FFFFFF", "W")]
        for hex_code, _ in presets:
            btn = ctk.CTkButton(
                presets_frame, text="", fg_color=hex_code, hover_color=hex_code, 
                width=30, height=30, corner_radius=15, 
                border_width=2 if self._led_color.lower() == hex_code.lower() else 0,
                border_color=Colors.TEXT_PRIMARY,
                command=lambda h=hex_code: self._on_led_color_change(h)
            )
            btn.pack(side="left", padx=4)

        # Right: Custom Picker Button
        ctk.CTkLabel(main_led_row, text="  |  ", text_color=Colors.BORDER).pack(side="left")
        
        custom_btn = ctk.CTkButton(
            main_led_row, text="🎨 " + ("Custom" if self._lang == "en" else "Özel Renk"), 
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self._led_color, text_color="#000000" if self._is_color_light(self._led_color) else "#FFFFFF",
            hover_color=Colors.PS_BLUE, corner_radius=8, height=36, width=140,
            command=self._open_color_picker
        )
        custom_btn.pack(side="left", padx=10)

        # Driver Management
        driver_frame = self._build_settings_card(content_scroll, self._t("driver_reset"), "🛠️")
        reset_btn = ctk.CTkButton(
            driver_frame, text=self._t("driver_reset"), font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=Colors.ERROR, hover_color="#992200", corner_radius=8, width=160, height=36,
            command=self._on_reset_driver_click
        )
        reset_btn.pack(side="left", padx=10, pady=10)
        
        # Warning Toggle
        warn_text = self._t("hide_warning") if self._show_warning_panel else self._t("show_warning")
        warn_btn = ctk.CTkButton(
            driver_frame, text=warn_text, font=ctk.CTkFont(family="Inter", size=13),
            fg_color=Colors.BG_DARK, hover_color=Colors.BG_CARD_HOVER, corner_radius=8, width=180, height=36,
            command=self._toggle_warning_setting
        )
        warn_btn.pack(side="left", padx=10, pady=10)

        # Requirements
        req_frame = self._build_settings_card(content_scroll, self._t("requirements"), "📦")
        vigem_label = ctk.CTkLabel(req_frame, text=self._t("vigem_desc"), font=ctk.CTkFont(family="Inter", size=14), text_color=Colors.TEXT_PRIMARY)
        vigem_label.pack(side="left", padx=15, pady=15)
        
        dl_btn = ctk.CTkButton(
            req_frame, text=self._t("download"), font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            fg_color=Colors.SUCCESS, hover_color="#2da864", corner_radius=8, height=32, width=100,
            command=lambda: self._show_requirements_popup()
        )
        dl_btn.pack(side="right", padx=15, pady=15)

    def _build_settings_card(self, parent, title, icon):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=10)
        lbl = ctk.CTkLabel(card, text=f"{icon} {title}", font=ctk.CTkFont(family="Inter", size=15, weight="bold"), text_color=Colors.PS_ACCENT)
        lbl.pack(anchor="w", padx=20, pady=(15, 5))
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=(0, 10))
        return content

    def _build_requirements_panel(self):
        container = ctk.CTkFrame(self._main_container, fg_color=Colors.BG_CARD, corner_radius=15, border_width=1, border_color=Colors.ERROR)
        container.pack(fill="both", expand=True)
        lbl_err = ctk.CTkLabel(container, text="⚠️ " + self._t("driver_missing"), font=ctk.CTkFont(family="Inter", size=18, weight="bold"), text_color=Colors.ERROR)
        lbl_err.pack(pady=(30, 10))
        lbl_msg = ctk.CTkLabel(container, text=self._t("vigem_desc"), font=ctk.CTkFont(family="Inter", size=13), text_color=Colors.TEXT_SECONDARY)
        lbl_msg.pack(pady=5)
        dl_btn = ctk.CTkButton(
            container, text=self._t("download"), font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            fg_color=Colors.SUCCESS, hover_color="#2da864", corner_radius=10, height=40, width=180,
            command=lambda: self._show_requirements_popup()
        )
        dl_btn.pack(pady=20)
        hide_btn = ctk.CTkButton(
            container, text=self._t("hide_warning"), font=ctk.CTkFont(family="Inter", size=11),
            fg_color="transparent", text_color=Colors.TEXT_DIM, hover_color=Colors.BG_CARD_HOVER,
            command=self._toggle_warning_setting
        )
        hide_btn.pack(pady=5)

    def _mode_label_to_value(self, label: str) -> int:
        return self.MODE_VALUES.get(label, 0)

    def _on_preferred_mode_selected(self, mode_str: str):
        self._selected_mode = mode_str
        self._save_settings()

    def _build_multi_controller_view(self):
        for widget in self._main_container.winfo_children():
            widget.destroy()

        self._slot_indicators.clear()
        self._log_items.clear()
        self._prev_log_state.clear()

        # Top Info Bar (Disconnect all)
        bar = ctk.CTkFrame(self._main_container, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER, height=56)
        bar.pack(fill="x", pady=(0, 8))
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        status_text = f"{self._t('connected_count')}: {self.manager.connected_count}"
        ctk.CTkLabel(inner, text=status_text, font=ctk.CTkFont(size=14, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(
            inner, text="⏏ " + self._t("disconnect_all"), font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Colors.BG_CARD_HOVER, hover_color=Colors.ERROR, border_width=1, border_color=Colors.BORDER,
            corner_radius=8, height=32, width=150, command=self._on_disconnect_click
        ).pack(side="right")

        slots = self.manager.slots
        if len(slots) == 1:
            frame = ctk.CTkFrame(self._main_container, fg_color="transparent")
            frame.pack(fill="both", expand=True)
            self._build_single_controller_ui(frame, slots[0])
        elif len(slots) > 1:
            tabview = ctk.CTkTabview(self._main_container, fg_color=Colors.BG_CARD, segmented_button_fg_color=Colors.BG_INPUT, segmented_button_selected_color=Colors.PS_BLUE)
            tabview.pack(fill="both", expand=True)
            for i, slot in enumerate(slots):
                tab_name = f"{self._t('controller_prefix')} {i+1}: {slot.name}"
                tabview.add(tab_name)
                self._build_single_controller_ui(tabview.tab(tab_name), slot)

    def _build_single_controller_ui(self, parent, slot: ControllerSlot):
        idx = slot.index
        self._slot_indicators[idx] = {}
        self._log_items[idx] = []
        self._prev_log_state[idx] = {}

        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, pady=(4, 0))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, weight=1)
        content.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_left_column(left, idx)

        center = ctk.CTkFrame(content, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=6)
        self._build_center_column(center, slot)

        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self._build_right_column(right, idx)

        self._build_button_log(parent, idx)

    def _build_left_column(self, parent, idx):
        self._create_trigger_card(parent, "L2", idx).pack(fill="x", pady=(0, 6))
        self._create_button_indicator(parent, "L1", idx).pack(fill="x", pady=(0, 6))
        
        dpad_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        dpad_card.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(dpad_card, text="D-PAD", font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=12, pady=(10, 4), anchor="w")
        
        grid = ctk.CTkFrame(dpad_card, fg_color="transparent")
        grid.pack(padx=12, pady=(0, 12))
        for i in range(3):
            grid.columnconfigure(i, weight=1, minsize=42)
            grid.rowconfigure(i, weight=1, minsize=42)
            
        self._create_dpad_btn(grid, "▲", idx, "dpad_up", 0, 1)
        self._create_dpad_btn(grid, "◀", idx, "dpad_left", 1, 0)
        self._create_dpad_btn(grid, "▶", idx, "dpad_right", 1, 2)
        self._create_dpad_btn(grid, "▼", idx, "dpad_down", 2, 1)

        self._build_stick_display(parent, self._t("left_analog"), "left", idx)

    def _build_center_column(self, parent, slot: ControllerSlot):
        idx = slot.index
        center_btns = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        center_btns.pack(fill="x", pady=(0, 6))
        
        row = ctk.CTkFrame(center_btns, fg_color="transparent")
        row.pack(padx=8, pady=10)
        self._create_small_button(row, "Create", "≡", idx).pack(side="left", padx=4)
        self._create_small_button(row, "PS", "ℙ", idx).pack(side="left", padx=4)
        self._create_small_button(row, "Options", "☰", idx).pack(side="left", padx=4)

        tp = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER, height=40)
        tp.pack(fill="x", pady=(0, 6))
        tp.pack_propagate(False)
        ctk.CTkLabel(tp, text=self._t("touchpad"), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).place(relx=0.5, rely=0.5, anchor="center")
        self._slot_indicators[idx]["touchpad"] = tp

        self._create_button_indicator(parent, "🎤 Mute", idx, key_override="mute").pack(fill="x", pady=(0, 6))

        # Settings Card
        sc = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        sc.pack(fill="x", pady=(0, 6), expand=True)
        ctk.CTkLabel(sc, text=self._t("settings").upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=12, pady=(10, 6), anchor="w")

        # 1. Mode Selection
        emu_sel = ctk.CTkSegmentedButton(
            sc, values=[self._t("direct"), "PS4", "Xbox"], 
            command=lambda v, s=idx: self._on_emulation_change(s, v),
            selected_color=Colors.PS_BLUE_DARK, selected_hover_color=Colors.PS_BLUE,
            unselected_color=Colors.BG_INPUT, unselected_hover_color=Colors.BG_CARD_HOVER
        )
        emu_sel.pack(fill="x", padx=12, pady=(4, 8))
        reverse_modes = {0: self._t("direct"), 1: "PS4", 2: "Xbox"}
        emu_sel.set(reverse_modes.get(slot.emulation_mode, self._t("direct")))

        # 2. Real-time LED Control
        ctk.CTkLabel(sc, text=self._t("led_color").upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=12, pady=(4, 2), anchor="w")
        led_row = ctk.CTkFrame(sc, fg_color="transparent")
        led_row.pack(fill="x", padx=8, pady=(0, 8))

        hex_c = self._led_color.lstrip('#')
        cr, cg, cb = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))

        def _update_led(_):
            r, g, b = int(sr.get()), int(sg.get()), int(sb.get())
            nh = f"#{r:02x}{g:02x}{b:02x}"; self._led_color = nh
            self._apply_led_color(); preview.configure(fg_color=nh)

        sliders = ctk.CTkFrame(led_row, fg_color="transparent")
        sliders.pack(side="left", fill="x", expand=True)
        sr = ctk.CTkSlider(sliders, from_=0, to=255, height=14, command=_update_led, button_color="#FF4444"); sr.pack(fill="x", pady=1); sr.set(cr)
        sg = ctk.CTkSlider(sliders, from_=0, to=255, height=14, command=_update_led, button_color="#44FF44"); sg.pack(fill="x", pady=1); sg.set(cg)
        sb = ctk.CTkSlider(sliders, from_=0, to=255, height=14, command=_update_led, button_color="#4444FF"); sb.pack(fill="x", pady=1); sb.set(cb)
        sr.bind("<ButtonRelease-1>", lambda e: self._save_settings())
        sg.bind("<ButtonRelease-1>", lambda e: self._save_settings())
        sb.bind("<ButtonRelease-1>", lambda e: self._save_settings())

        # Preview Button: Clicking this opens the full color picker
        preview = ctk.CTkButton(
            led_row, text="", width=30, height=46, fg_color=self._led_color, 
            hover_color=self._led_color, corner_radius=6, border_width=1, 
            border_color=Colors.BORDER, command=self._open_color_picker
        )
        preview.pack(side="right", padx=(10, 5))

        # 3. Vibration Test
        vib_btn = ctk.CTkButton(
            sc, text="📳 " + self._t("vibration_test"), font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Colors.BG_INPUT, hover_color=Colors.BG_CARD_HOVER, border_width=1, border_color=Colors.BORDER,
            corner_radius=8, height=32, command=lambda s=idx: self.manager.test_rumble(s)
        )
        vib_btn.pack(fill="x", padx=12, pady=(0, 8))

        # 4. Swap Triggers
        swap_cb = ctk.CTkCheckBox(
            sc, text=self._t("swap_triggers"), font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY, fg_color=Colors.PS_BLUE,
            command=lambda s=idx: self._on_swap_triggers_change(s)
        )
        swap_cb.pack(fill="x", padx=12, pady=(0, 10))
        self._slot_indicators[idx]["swap_cb"] = swap_cb

        # Rumble Test Button
        vib_btn = ctk.CTkButton(
            sc, text="📳 " + self._t("vibration_test"), 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Colors.BG_INPUT,
            hover_color=Colors.BG_CARD_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            height=32,
            command=lambda s=idx: self.manager.test_rumble(s)
        )
        vib_btn.pack(fill="x", padx=12, pady=(0, 10))

        # Info
        ctk.CTkLabel(sc, text=f"{self._t('controller_name')}: {slot.name}", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_DIM).pack(fill="x", padx=12, pady=(4, 8))

    def _build_right_column(self, parent, idx):
        self._create_trigger_card(parent, "R2", idx).pack(fill="x", pady=(0, 6))
        self._create_button_indicator(parent, "R1", idx).pack(fill="x", pady=(0, 6))

        face_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        face_card.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(face_card, text=self._t("action_buttons"), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=12, pady=(10, 4), anchor="w")

        grid = ctk.CTkFrame(face_card, fg_color="transparent")
        grid.pack(padx=12, pady=(0, 12))
        for i in range(3):
            grid.columnconfigure(i, weight=1, minsize=46)
            grid.rowconfigure(i, weight=1, minsize=46)

        self._create_face_btn(grid, "△", Colors.TRIANGLE_GREEN, idx, "triangle", 0, 1)
        self._create_face_btn(grid, "○", Colors.CIRCLE_RED, idx, "circle", 1, 2)
        self._create_face_btn(grid, "✕", Colors.CROSS_BLUE, idx, "cross", 2, 1)
        self._create_face_btn(grid, "□", Colors.SQUARE_PINK, idx, "square", 1, 0)

        self._build_stick_display(parent, self._t("right_analog"), "right", idx)

    def _build_button_log(self, parent, idx):
        log_card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER, height=40)
        log_card.pack(fill="x", pady=(6, 0))
        log_card.pack_propagate(False)

        inner = ctk.CTkFrame(log_card, fg_color="transparent")
        inner.pack(fill="both", padx=12, pady=6)

        ctk.CTkLabel(inner, text=self._t("last_pressed"), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(side="left", padx=(0, 12))
        lbl = ctk.CTkLabel(inner, text=self._t("start_pressing"), font=ctk.CTkFont(family="Inter", size=11), text_color=Colors.TEXT_DIM)
        lbl.pack(side="left")
        self._slot_indicators[idx]["log_label"] = lbl

    # ═══════════════════════════════════════════════════════
    # Component Builders
    # ═══════════════════════════════════════════════════════
    def _create_trigger_card(self, parent, label, idx):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_DIM).pack(side="left")
        value_label = ctk.CTkLabel(header, text="0%", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_SECONDARY)
        value_label.pack(side="right")
        progress = ctk.CTkProgressBar(inner, fg_color=Colors.BG_INPUT, progress_color=Colors.PS_BLUE, corner_radius=4, height=8)
        progress.set(0)
        progress.pack(fill="x", pady=(6, 0))

        key = label.lower()
        self._slot_indicators[idx][f"{key}_progress"] = progress
        self._slot_indicators[idx][f"{key}_value"] = value_label
        return card

    def _create_button_indicator(self, parent, label, idx, key_override=None):
        frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER, height=40)
        frame.pack_propagate(False)
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=Colors.TEXT_SECONDARY).place(relx=0.5, rely=0.5, anchor="center")
        key = key_override or label.lower()
        self._slot_indicators[idx][key] = frame
        return frame

    def _create_dpad_btn(self, parent, symbol, idx, key, row, col):
        btn = ctk.CTkFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=6, border_width=1, border_color=Colors.BORDER, width=38, height=38)
        btn.grid(row=row, column=col, padx=2, pady=2)
        btn.grid_propagate(False)
        ctk.CTkLabel(btn, text=symbol, font=ctk.CTkFont(size=11), text_color=Colors.TEXT_DIM).place(relx=0.5, rely=0.5, anchor="center")
        self._slot_indicators[idx][key] = btn
        return btn

    def _create_face_btn(self, parent, symbol, color, idx, key, row, col):
        btn = ctk.CTkFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=20, border_width=2, border_color=Colors.BORDER, width=42, height=42)
        btn.grid(row=row, column=col, padx=3, pady=3)
        btn.grid_propagate(False)
        ctk.CTkLabel(btn, text=symbol, font=ctk.CTkFont(size=16, weight="bold"), text_color=color).place(relx=0.5, rely=0.5, anchor="center")
        self._slot_indicators[idx][key] = btn
        self._slot_indicators[idx][f"{key}_color"] = color
        return btn

    def _create_small_button(self, parent, label, icon, idx):
        btn = ctk.CTkFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=8, border_width=1, border_color=Colors.BORDER, width=80, height=48)
        btn.pack_propagate(False)
        ctk.CTkLabel(btn, text=icon, font=ctk.CTkFont(size=14), text_color=Colors.TEXT_SECONDARY).pack(pady=(6, 0))
        ctk.CTkLabel(btn, text=label, font=ctk.CTkFont(size=8), text_color=Colors.TEXT_DIM).pack()
        self._slot_indicators[idx][label.lower()] = btn
        return btn

    def _build_stick_display(self, parent, label, side, idx):
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=10, border_width=1, border_color=Colors.BORDER)
        card.pack(fill="x", pady=(0, 6), expand=True)
        ctk.CTkLabel(card, text=label.upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=12, pady=(10, 4), anchor="w")

        cs = 110
        canvas = tk.Canvas(card, width=cs, height=cs, bg=Colors.BG_DARK, highlightthickness=0, bd=0)
        canvas.pack(padx=12, pady=(0, 4))
        pad = 10; center = cs // 2; dot_r = 8
        canvas.create_oval(pad, pad, cs - pad, cs - pad, outline=Colors.BORDER, width=1)
        canvas.create_line(pad, center, cs - pad, center, fill=Colors.BORDER, width=1)
        canvas.create_line(center, pad, center, cs - pad, fill=Colors.BORDER, width=1)
        dot = canvas.create_oval(center - dot_r, center - dot_r, center + dot_r, center + dot_r, fill=Colors.PS_ACCENT, outline="")

        stick_btn_name = "L3" if side == "left" else "R3"
        stick_btn = ctk.CTkFrame(card, fg_color=Colors.BG_INPUT, corner_radius=12, border_width=1, border_color=Colors.BORDER, height=24)
        stick_btn.pack(padx=30, pady=(0, 10))
        ctk.CTkLabel(stick_btn, text=stick_btn_name, font=ctk.CTkFont(size=9, weight="bold"), text_color=Colors.TEXT_DIM).pack(padx=16, pady=2)

        self._slot_indicators[idx][f"{side}_canvas"] = canvas
        self._slot_indicators[idx][f"{side}_dot"] = dot
        self._slot_indicators[idx][stick_btn_name.lower()] = stick_btn

    def _build_footer(self):
        if hasattr(self, "_footer_frame"):
            self._footer_frame.destroy()
            
        self._footer_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=0, height=32)
        self._footer_frame.pack(fill="x", side="bottom")
        self._footer_frame.pack_propagate(False)
        
        footer_text = "Universal Controller Manager © 2026  •  " + ("Works with PlayStation buttons" if self._lang == "en" else "PlayStation butonları ile çalışır")
        ctk.CTkLabel(self._footer_frame, text=footer_text, font=ctk.CTkFont(family="Inter", size=9), text_color=Colors.TEXT_DIM).pack(expand=True)

    # ═══════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════
    def _try_auto_connect(self):
        self._start_connect(auto=True)

    def _on_connect_click(self):
        self._start_connect(auto=False)

    def _start_connect(self, auto: bool):
        if self._connect_in_progress or self.manager.connected_count > 0:
            return

        self._connect_in_progress = True
        self._save_settings()

        if hasattr(self, "_connect_btn"):
            self._connect_btn.configure(text=("Connecting..." if self._lang == "en" else "Bağlanıyor..."), state="disabled")
        if hasattr(self, "_connect_msg"):
            initial_text = (("Searching for controller..." if self._lang == "en" else "Kontrolcü aranıyor...") if auto else "")
            self._connect_msg.configure(text=initial_text, text_color=Colors.TEXT_DIM)

        def _do_connect():
            success, msg = self.manager.connect_all(self._mode_label_to_value(self._selected_mode))
            self.after(0, lambda: self._handle_connect_result(success, msg, auto))

        threading.Thread(target=_do_connect, daemon=True).start()

    def _handle_connect_result(self, success, msg, auto: bool = False):
        self._connect_in_progress = False
        if success:
            self._apply_led_color()
            self._build_multi_controller_view()
            return

        if hasattr(self, "_connect_btn"):
            self._connect_btn.configure(text="🔌  " + self._t("connect"), state="normal")

        if hasattr(self, "_connect_msg"):
            color = Colors.TEXT_DIM if auto else Colors.ERROR
            self._connect_msg.configure(text=msg, text_color=color)

    def _on_disconnect_click(self):
        self.manager.disconnect_all()
        self._build_connect_screen()

    def _on_connection_change(self, connected: bool):
        def _update():
            if connected:
                self._status_dot.configure(text_color=Colors.SUCCESS)
                status_text = (f"Connected ({self.manager.connected_count})" if self._lang == "en" else f"Bağlı ({self.manager.connected_count})")
                self._status_label.configure(text=status_text, text_color=Colors.SUCCESS)
            else:
                self._status_dot.configure(text_color=Colors.ERROR)
                self._status_label.configure(text=self._t("status_idle"), text_color=Colors.TEXT_SECONDARY)
                if self.manager.connected_count == 0:
                    self._build_connect_screen()
        self.after(0, _update)

    def _on_emulation_change(self, slot_idx, mode_str):
        self.manager.set_slot_emulation(slot_idx, self._mode_label_to_value(mode_str))

    def _on_swap_triggers_change(self, slot_idx):
        if 0 <= slot_idx < len(self.manager.slots):
            slot = self.manager.slots[slot_idx]
            cb = self._slot_indicators.get(slot_idx, {}).get("swap_cb")
            if cb:
                slot.reader.swap_triggers = bool(cb.get())

    # ═══════════════════════════════════════════════════════
    # GUI Update (called at ~30fps)
    # ═══════════════════════════════════════════════════════
    def _on_state_update(self):
        if self._is_resizing:
            return
        if not self._gui_update_pending:
            self._gui_update_pending = True
            self.after(32, self._update_gui)

    def _update_gui(self):
        self._gui_update_pending = False
        if self._is_resizing:
            return
        
        for slot in self.manager.slots:
            idx = slot.index
            state = slot.state
            if idx not in self._slot_indicators:
                continue

            try:
                self._update_trigger("l2", state.l2, idx)
                self._update_trigger("r2", state.r2, idx)

                self._set_btn_active("l1", state.l1, idx)
                self._set_btn_active("r1", state.r1, idx)

                self._set_face_active("cross", state.cross, idx)
                self._set_face_active("circle", state.circle, idx)
                self._set_face_active("square", state.square, idx)
                self._set_face_active("triangle", state.triangle, idx)

                self._set_dpad_active("dpad_up", state.dpad_up, idx)
                self._set_dpad_active("dpad_down", state.dpad_down, idx)
                self._set_dpad_active("dpad_left", state.dpad_left, idx)
                self._set_dpad_active("dpad_right", state.dpad_right, idx)

                self._set_btn_active("create", state.create, idx)
                self._set_btn_active("ps", state.ps_button, idx)
                self._set_btn_active("options", state.options, idx)
                self._set_btn_active("touchpad", state.touchpad, idx)
                self._set_btn_active("mute", state.mute, idx)
                self._set_btn_active("l3", state.l3, idx)
                self._set_btn_active("r3", state.r3, idx)

                self._update_stick("left", state.left_stick_x, state.left_stick_y, idx)
                self._update_stick("right", state.right_stick_x, state.right_stick_y, idx)

                self._update_log(state, idx)
            except Exception:
                pass

    def _update_trigger(self, key, value, idx):
        progress = self._slot_indicators[idx].get(f"{key}_progress")
        val_label = self._slot_indicators[idx].get(f"{key}_value")
        if progress and val_label:
            pct = value / 255.0
            progress.set(pct)
            val_label.configure(text=f"{int(pct * 100)}%")
            progress.configure(progress_color=Colors.PS_ACCENT if pct > 0.05 else Colors.PS_BLUE)

    def _set_btn_active(self, key, active, idx):
        frame = self._slot_indicators[idx].get(key)
        if frame:
            if active:
                frame.configure(fg_color=Colors.PS_BLUE_DARK, border_color=Colors.PS_ACCENT)
            else:
                frame.configure(fg_color=Colors.BG_CARD if key in ("l1", "r1", "mute", "touchpad") else Colors.BG_INPUT, border_color=Colors.BORDER)

    def _set_face_active(self, key, active, idx):
        widget = self._slot_indicators[idx].get(key)
        color = self._slot_indicators[idx].get(f"{key}_color", Colors.BORDER)
        if widget:
            if active:
                widget.configure(fg_color=Colors.BG_CARD_HOVER, border_color=color)
            else:
                widget.configure(fg_color=Colors.BG_INPUT, border_color=Colors.BORDER)

    def _set_dpad_active(self, key, active, idx):
        widget = self._slot_indicators[idx].get(key)
        if widget:
            widget.configure(fg_color=Colors.PS_BLUE_DARK if active else Colors.BG_INPUT, border_color=Colors.PS_ACCENT if active else Colors.BORDER)

    def _update_stick(self, side, raw_x, raw_y, idx):
        canvas = self._slot_indicators[idx].get(f"{side}_canvas")
        dot = self._slot_indicators[idx].get(f"{side}_dot")
        if canvas and dot:
            nx = max(-1, min(1, raw_x / 128.0))
            ny = max(-1, min(1, raw_y / 128.0))
            center = 55; dot_r = 8; radius = 45
            px = center + nx * radius
            py = center + ny * radius
            canvas.coords(dot, px - dot_r, py - dot_r, px + dot_r, py + dot_r)

    def _update_log(self, state, idx):
        buttons = {
            "✕": state.cross, "○": state.circle, "□": state.square, "△": state.triangle,
            "L1": state.l1, "R1": state.r1, "L3": state.l3, "R3": state.r3,
            "▲": state.dpad_up, "▼": state.dpad_down, "◀": state.dpad_left, "▶": state.dpad_right,
            "Create": state.create, "Options": state.options, "PS": state.ps_button,
            "TP": state.touchpad, "Mute": state.mute,
            "L2": state.l2 > 30, "R2": state.r2 > 30
        }

        changed = False
        prev = self._prev_log_state[idx]
        log_list = self._log_items[idx]

        for name, pressed in buttons.items():
            if pressed and not prev.get(name, False):
                log_list.insert(0, name)
                if len(log_list) > 10:
                    log_list.pop()
                changed = True
            prev[name] = pressed

        if changed:
            lbl = self._slot_indicators[idx].get("log_label")
            if lbl:
                lbl.configure(text="  →  ".join(log_list), text_color=Colors.PS_ACCENT)

    def _on_close(self):
        self.manager.disconnect_all()
        self.destroy()
