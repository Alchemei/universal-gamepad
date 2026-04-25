"""
DualSense Controller Manager
Reads DualSense input via HID (pydualsense) and maps it to a virtual Xbox 360 controller (vgamepad/ViGEmBus).
"""

import gc
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any

try:
    from pydualsense import pydualsense
    HAS_PYDUALSENSE = True
except ImportError:
    HAS_PYDUALSENSE = False

try:
    import vgamepad as vg
    HAS_VGAMEPAD = True
    try:
        from vgamepad.win import vigem_client as vg_vigem_client
    except Exception:
        vg_vigem_client = None
except ImportError:
    HAS_VGAMEPAD = False
    vg_vigem_client = None


@dataclass
class ControllerState:
    """Current state of all DualSense inputs — uses PlayStation names."""
    # Face Buttons (PlayStation names!)
    cross: bool = False       # ✕
    circle: bool = False      # ○
    square: bool = False      # □
    triangle: bool = False    # △

    # Bumpers
    l1: bool = False
    r1: bool = False

    # Triggers (analog 0-255)
    l2: int = 0
    r2: int = 0

    # Sticks (centered at 0, range ~ -128..127)
    left_stick_x: int = 0
    left_stick_y: int = 0
    right_stick_x: int = 0
    right_stick_y: int = 0

    # Stick clicks
    l3: bool = False
    r3: bool = False

    # D-Pad
    dpad_up: bool = False
    dpad_down: bool = False
    dpad_left: bool = False
    dpad_right: bool = False

    # Special buttons
    options: bool = False
    create: bool = False
    ps_button: bool = False
    touchpad: bool = False
    mute: bool = False

    # Connection info
    connected: bool = False
    battery_level: int = 0
    connection_type: str = "—"


class ControllerManager:
    """
    Manages DualSense reading and Xbox 360 virtual controller emulation.
    Runs input polling on a separate thread to avoid blocking the GUI.
    """

    def __init__(self):
        self.state = ControllerState()
        self._ds: Optional[pydualsense] = None
        self._vpad: Optional[vg.VDS4Gamepad] = None
        self._xbox: Optional[vg.VX360Gamepad] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._poll_rate = 0.004  # ~250Hz polling
        self._deadzone = 10  # stick deadzone (0-128 range)
        # Emulasyon modu: 0 = Direkt, 1 = PS4, 2 = Xbox 360
        self._emulation_mode = 0 
        self._on_state_change: Optional[Callable] = None
        self._on_connection_change: Optional[Callable] = None
        self._lock = threading.Lock()
        self._debug_counter = 0
        self._current_trigger_profile = "off"
        self._mode_switch_delay = 0.35
        
        # State for trigger monkey-patching
        self._trigger_left = {"mode": 0x00, "params": [0]*9}
        self._trigger_right = {"mode": 0x00, "params": [0]*9}

    # ═══════════════════════════════════════════════════════
    # Adaptive Trigger Profiles
    # DualSense USB Output Report (64 bytes, Report ID 0x02)
    #   Byte 1: Valid flag 0 (0xFF = enable all)
    #   Byte 2: Valid flag 1 (0x01=motor, 0x04=right trigger, 0x08=left trigger)
    #   Right trigger effect: bytes 11-20
    #   Left trigger effect: bytes 22-31
    #   Byte 11/22: Effect mode
    #   Byte 12-20 / 23-31: Parameters
    # ═══════════════════════════════════════════════════════
    TRIGGER_PROFILES: Dict[str, Dict[str, Any]] = {
        "off": {
            "name": "Kapalı",
            "icon": "⭕",
            "desc": "Normal tetik — direnç yok",
            "right": {"mode": 0x00, "params": [0]*9},
            "left":  {"mode": 0x00, "params": [0]*9},
        },
        "weapon": {
            "name": "Silah",
            "icon": "🔫",
            "desc": "Tetik yarıda sert direnir — FPS oyunları",
            # Mode 0x02 = Weapon: startPos, endPos, strength, 0,0,0,0,0,0
            "right": {"mode": 0x02, "params": [40, 140, 255, 0, 0, 0, 0, 0, 0]},
            "left":  {"mode": 0x02, "params": [40, 140, 200, 0, 0, 0, 0, 0, 0]},
        },
        "bow": {
            "name": "Yay",
            "icon": "🏹",
            "desc": "Giderek artan direnç — RPG/aksiyon",
            # Mode 0x01 = Feedback: positions bitmask (zones 0-9), strengths
            "right": {"mode": 0x01, "params": [0x00, 0x03, 20, 60, 100, 140, 180, 220, 255]},
            "left":  {"mode": 0x01, "params": [0x00, 0x03, 20, 60, 100, 140, 180, 220, 255]},
        },
        "racing": {
            "name": "Yarış",
            "icon": "🏎️",
            "desc": "Gaz/fren hissi — yarış oyunları",
            # Right (gaz): hafif direnç
            "right": {"mode": 0x02, "params": [70, 160, 120, 0, 0, 0, 0, 0, 0]},
            # Left (fren): sert direnç
            "left":  {"mode": 0x02, "params": [30, 150, 255, 0, 0, 0, 0, 0, 0]},
        },
        "rigid": {
            "name": "Sert",
            "icon": "🧱",
            "desc": "Tam direnç — tetik zor basılır",
            "right": {"mode": 0x02, "params": [10, 255, 255, 0, 0, 0, 0, 0, 0]},
            "left":  {"mode": 0x02, "params": [10, 255, 255, 0, 0, 0, 0, 0, 0]},
        },
        "vibration": {
            "name": "Titreşim",
            "icon": "📳",
            "desc": "Tetik titrer — özel his",
            # Mode 0x06 = Vibration with parameters
            "right": {"mode": 0x06, "params": [15, 200, 255, 0, 0, 0, 0, 0, 0]},
            "left":  {"mode": 0x06, "params": [15, 200, 255, 0, 0, 0, 0, 0, 0]},
        },
    }
    EMULATION_MODE_LABELS = {
        0: "Direkt",
        1: "PS4",
        2: "Xbox",
    }

    @staticmethod
    def _force_remove_vigem_target(device):
        """Disconnect a vgamepad target immediately instead of waiting for GC."""
        if not device:
            return

        try:
            device.reset()
            device.update()
        except Exception:
            pass

        if vg_vigem_client and getattr(device, "_busp", None) and getattr(device, "_devicep", None):
            try:
                device.unregister_notification()
            except Exception:
                pass
            try:
                vg_vigem_client.vigem_target_remove(device._busp, device._devicep)
            except Exception:
                pass
            try:
                vg_vigem_client.vigem_target_free(device._devicep)
            except Exception:
                pass
            try:
                device._devicep = None
            except Exception:
                pass
        else:
            try:
                device.__del__()
            except Exception:
                pass

    @property
    def has_pydualsense(self):
        return HAS_PYDUALSENSE

    @property
    def has_vgamepad(self):
        return HAS_VGAMEPAD

    @property
    def is_connected(self):
        return self.state.connected

    @property
    def emulation_mode(self):
        return self._emulation_mode

    @emulation_mode.setter
    def emulation_mode(self, mode: int):
        self._emulation_mode = mode
        self._apply_emulation_mode()

    @property
    def deadzone(self):
        return self._deadzone

    @deadzone.setter
    def deadzone(self, value: int):
        self._deadzone = max(0, min(50, value))

    def set_on_state_change(self, callback: Callable):
        self._on_state_change = callback

    def set_on_connection_change(self, callback: Callable):
        self._on_connection_change = callback

    def get_emulation_mode_label(self) -> str:
        return self.EMULATION_MODE_LABELS.get(self._emulation_mode, "Direkt")

    def refresh_virtual_controller(self) -> bool:
        """Recreate the active virtual controller so games can re-detect it."""
        if not self.state.connected or self._emulation_mode == 0:
            return False
        self._apply_emulation_mode()
        return True

    def connect(self) -> tuple[bool, str]:
        """Try to connect to DualSense controller."""
        if not HAS_PYDUALSENSE:
            return False, "pydualsense kütüphanesi bulunamadı!\npip install pydualsense"

        try:
            self._ds = pydualsense()
            self._ds.init()
            self.state.connected = True
            
            # Bağlantı tipini pydualsense'den al
            if hasattr(self._ds, "conType") and self._ds.conType is not None:
                self.state.connection_type = self._ds.conType.name
            else:
                self.state.connection_type = "USB"

            # Hook into pydualsense's background write thread
            self._orig_prepare_report = self._ds.prepareReport
            self._ds.prepareReport = self._patched_prepare_report
            self._apply_emulation_mode()

            # Mod değişimi mantığına göre initialize et
            # Start polling thread
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

            if self._on_connection_change:
                self._on_connection_change(True)
            return True, f"DualSense baglandi! Mod: {self.get_emulation_mode_label()}"

            return True, "DualSense bağlandı! (Direkt Mod)"

        except Exception as e:
            self.state.connected = False
            error_msg = str(e)
            if "No device found" in error_msg or "could not open" in error_msg.lower():
                return False, "DualSense bulunamadı!\nKontrolcüyü USB ile bağlayın."
            return False, f"Bağlantı hatası: {error_msg}"

    def _apply_emulation_mode(self):
        """Destroy and recreate the selected virtual controller."""
        self._destroy_vpad_controller()
        self._destroy_xbox_controller()

        if not self.state.connected:
            return

        if self._emulation_mode != 0:
            time.sleep(self._mode_switch_delay)

        if self._emulation_mode == 1:
            self._create_vpad_controller()
        elif self._emulation_mode == 2:
            self._create_xbox_controller()

        self._settle_virtual_controller()

    def _settle_virtual_controller(self):
        """Give Windows a short moment to enumerate the virtual pad cleanly."""
        if not (self._vpad or self._xbox):
            return

        time.sleep(self._mode_switch_delay)
        self._reset_vpad()
        self._reset_xbox()
        time.sleep(self._mode_switch_delay)

    def _create_vpad_controller(self):
        """Create virtual DualShock 4 controller so games see a PlayStation pad."""
        if not HAS_VGAMEPAD:
            print("[WARN] vgamepad/ViGEmBus yüklü değil — DS4 emülasyonu kullanılamaz")
            return
        if self._vpad:
            return
        try:
            self._vpad = vg.VDS4Gamepad()
            self._vpad.update()
            print("[INFO] Sanal DualShock 4 (PS4) kontrolcü oluşturuldu")
        except Exception as e:
            print(f"[WARN] ViGEmBus sanal kontrolcü oluşturulamadı: {e}")
            self._vpad = None

    def _destroy_vpad_controller(self):
        """Remove virtual DualShock 4 controller."""
        vpad = self._vpad
        self._vpad = None
        if not vpad:
            return
        self._force_remove_vigem_target(vpad)
        del vpad
        gc.collect()
        print("[INFO] Sanal PS4 kontrolcü kaldırıldı")
        return
        if self._vpad:
            try:
                self._reset_vpad()
                del self._vpad
                gc.collect()
            except:
                pass
            self._vpad = None
            print("[INFO] Sanal PS4 kontrolcü kaldırıldı")

    def _create_xbox_controller(self):
        """Create virtual Xbox 360 controller."""
        if not HAS_VGAMEPAD:
            print("[WARN] vgamepad/ViGEmBus yüklü değil — Xbox emülasyonu kullanılamaz")
            return
        if self._xbox:
            return
        try:
            self._xbox = vg.VX360Gamepad()
            self._xbox.update()
            print("[INFO] Sanal Xbox 360 kontrolcü oluşturuldu")
        except Exception as e:
            print(f"[WARN] ViGEmBus sanal kontrolcü oluşturulamadı: {e}")
            self._xbox = None

    def _destroy_xbox_controller(self):
        xbox = self._xbox
        self._xbox = None
        if not xbox:
            return
        self._force_remove_vigem_target(xbox)
        del xbox
        gc.collect()
        print("[INFO] Sanal Xbox 360 kontrolcü kaldırıldı")
        return
        if self._xbox:
            try:
                self._reset_xbox()
                del self._xbox
                gc.collect()
            except:
                pass
            self._xbox = None
            print("[INFO] Sanal Xbox 360 kontrolcü kaldırıldı")

    def disconnect(self):
        """Disconnect controller and clean up."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self._destroy_vpad_controller()
        self._destroy_xbox_controller()

        if self._ds:
            try:
                self._ds.close()
            except:
                pass
            self._ds = None

        self.state = ControllerState()

        if self._on_connection_change:
            self._on_connection_change(False)

    def _poll_loop(self):
        """Main polling loop running on separate thread."""
        while self._running and self._ds:
            try:
                self._read_dualsense()
                if self._emulation_mode == 1 and self._vpad:
                    self._update_vpad()
                elif self._emulation_mode == 2 and self._xbox:
                    self._update_xbox()
                if self._on_state_change:
                    self._on_state_change()

                # Debug: print raw values every ~1 second
                self._debug_counter += 1
                if self._debug_counter % 250 == 0:
                    ds = self._ds
                    if ds:
                        print(f"[DEBUG] L1={ds.state.L1} (type={type(ds.state.L1).__name__}) | "
                              f"L2={ds.state.L2} (type={type(ds.state.L2).__name__}) | "
                              f"R1={ds.state.R1} | R2={ds.state.R2} | "
                              f"LX={ds.state.LX} LY={ds.state.LY}")

            except Exception as e:
                print(f"[ERROR] Polling error: {e}")
                # Controller might have disconnected
                if "device" in str(e).lower() or "hid" in str(e).lower():
                    self.state.connected = False
                    if self._on_connection_change:
                        self._on_connection_change(False)
                    break

            time.sleep(self._poll_rate)

    @staticmethod
    def _normalize_trigger(raw_value) -> int:
        """Normalize trigger value to 0-255 regardless of pydualsense version.
        Some versions return float 0.0-1.0, others return int 0-255."""
        if isinstance(raw_value, float):
            if raw_value <= 1.0:
                return int(raw_value * 255)
            return int(raw_value)
        val = int(raw_value)
        return max(0, min(255, val))

    @staticmethod
    def _normalize_button(raw_value) -> bool:
        """Normalize button to bool regardless of type."""
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, (int, float)):
            return raw_value > 0
        return bool(raw_value)

    def _read_dualsense(self):
        """Read current DualSense state via pydualsense."""
        ds = self._ds
        if not ds:
            return

        with self._lock:
            state = self.state

            # Face buttons
            state.cross = self._normalize_button(ds.state.cross)
            state.circle = self._normalize_button(ds.state.circle)
            state.square = self._normalize_button(ds.state.square)
            state.triangle = self._normalize_button(ds.state.triangle)

            # Bumpers
            state.l1 = self._normalize_button(ds.state.L1)
            state.r1 = self._normalize_button(ds.state.R1)

            # Triggers (analog) — L2_value/R2_value hold 0-255 pressure
            # (L2/R2 are just bool button states in pydualsense)
            state.l2 = self._normalize_trigger(ds.state.L2_value)
            state.r2 = self._normalize_trigger(ds.state.R2_value)

            # Sticks
            state.left_stick_x = ds.state.LX
            state.left_stick_y = ds.state.LY
            state.right_stick_x = ds.state.RX
            state.right_stick_y = ds.state.RY

            # Stick clicks
            state.l3 = self._normalize_button(ds.state.L3)
            state.r3 = self._normalize_button(ds.state.R3)

            # D-Pad
            state.dpad_up = self._normalize_button(ds.state.DpadUp)
            state.dpad_down = self._normalize_button(ds.state.DpadDown)
            state.dpad_left = self._normalize_button(ds.state.DpadLeft)
            state.dpad_right = self._normalize_button(ds.state.DpadRight)

            # Special
            state.options = self._normalize_button(ds.state.options)
            state.create = self._normalize_button(ds.state.share)
            state.ps_button = self._normalize_button(ds.state.ps)
            state.touchpad = self._normalize_button(ds.state.touchBtn)

            # Mute — check if the attribute exists (newer firmware/library)
            if hasattr(ds.state, 'micBtn'):
                state.mute = self._normalize_button(ds.state.micBtn)

    def _apply_deadzone(self, value: int, center: int = 0) -> int:
        """Apply stick deadzone. Center is 0 for pydualsense."""
        diff = value - center
        if abs(diff) < self._deadzone:
            return center
        return value

    def _stick_to_vpad(self, value: int) -> float:
        """Convert pydualsense stick value (center=0, range~-128..127) to -1.0..1.0 VPad range."""
        centered = self._apply_deadzone(value)
        if centered == 0:
            return 0.0
        # Scale to -1.0..1.0
        return max(-1.0, min(1.0, centered / 128.0))

    def _trigger_to_vpad(self, value: int) -> int:
        """Convert 0-255 trigger to 0-255 VPad range."""
        return max(0, min(255, value))

    def _update_vpad(self):
        """Map DualSense inputs to virtual DualShock 4 controller."""
        vpad = self._vpad
        if not vpad:
            return

        state = self.state

        # Face Buttons: PS → PS mapping
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS) if state.cross else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE) if state.circle else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE) if state.square else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE) if state.triangle else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)

        # Bumpers
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT) if state.l1 else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT) if state.r1 else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)

        # Triggers (analog)
        vpad.left_trigger_float(value_float=self._trigger_to_vpad(state.l2))
        vpad.right_trigger_float(value_float=self._trigger_to_vpad(state.r2))

        # Sticks
        lx = self._stick_to_vpad(state.left_stick_x)
        ly = self._stick_to_vpad(state.left_stick_y)  # DO NOT invert Y axis for PS4
        rx = self._stick_to_vpad(state.right_stick_x)
        ry = self._stick_to_vpad(state.right_stick_y)  # DO NOT invert Y axis for PS4

        vpad.left_joystick_float(x_value_float=lx, y_value_float=ly)
        vpad.right_joystick_float(x_value_float=rx, y_value_float=ry)

        # Stick clicks
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT) if state.l3 else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT) if state.r3 else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)

        # D-Pad
        # vgamepad DS4 uses directional_pad property with 8-way enums, but creating a simplified version:
        up = state.dpad_up
        down = state.dpad_down
        left = state.dpad_left
        right = state.dpad_right

        dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
        if up and right: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
        elif up and left: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
        elif down and right: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
        elif down and left: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
        elif up: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
        elif down: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
        elif left: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
        elif right: dir_pad = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
        vpad.directional_pad(direction=dir_pad)

        # Special Buttons
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS) if state.options else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
        vpad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE) if state.create else vpad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
        
        # PS and Touchpad use special button methods in vgamepad
        vpad.press_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS) if state.ps_button else vpad.release_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
        vpad.press_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD) if state.touchpad else vpad.release_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)

        # Send update
        vpad.update()

    def _update_xbox(self):
        """Map DualSense inputs to virtual Xbox 360 controller."""
        xbox = self._xbox
        if not xbox:
            return

        state = self.state

        # Face Buttons: PS → Xbox mapping
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A) if state.cross else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B) if state.circle else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X) if state.square else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y) if state.triangle else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)

        # Bumpers
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER) if state.l1 else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER) if state.r1 else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)

        # Triggers
        xbox.left_trigger_float(value_float=self._trigger_to_vpad(state.l2))
        xbox.right_trigger_float(value_float=self._trigger_to_vpad(state.r2))

        # Sticks
        lx = self._stick_to_vpad(state.left_stick_x)
        ly = -self._stick_to_vpad(state.left_stick_y)
        rx = self._stick_to_vpad(state.right_stick_x)
        ry = -self._stick_to_vpad(state.right_stick_y)

        xbox.left_joystick_float(x_value_float=lx, y_value_float=ly)
        xbox.right_joystick_float(x_value_float=rx, y_value_float=ry)

        # Stick clicks
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB) if state.l3 else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB) if state.r3 else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)

        # D-Pad
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP) if state.dpad_up else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN) if state.dpad_down else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT) if state.dpad_left else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT) if state.dpad_right else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        # Special Buttons
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START) if state.options else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK) if state.create else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        xbox.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE) if state.ps_button else xbox.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)

        # Send update
        xbox.update()

    def _reset_vpad(self):
        """Reset all virtual controller inputs to neutral."""
        if not self._vpad:
            return
        try:
            self._vpad.reset()
            self._vpad.update()
        except:
            pass

    def _reset_xbox(self):
        """Reset all virtual controller inputs to neutral."""
        if not self._xbox:
            return
        try:
            self._xbox.reset()
            self._xbox.update()
        except:
            pass

    def test_vibration(self, intensity: int = 200, duration: float = 0.5):
        """Test DualSense haptic feedback."""
        if not self._ds or not self.state.connected:
            return

        def _vibrate():
            try:
                self._ds.setLeftMotor(intensity)
                self._ds.setRightMotor(intensity)
                time.sleep(duration)
                self._ds.setLeftMotor(0)
                self._ds.setRightMotor(0)
            except Exception as e:
                print(f"[ERROR] Titreşim hatası: {e}")

        threading.Thread(target=_vibrate, daemon=True).start()

    def set_led_color(self, r: int, g: int, b: int):
        """Set DualSense LED color."""
        if not self._ds or not self.state.connected:
            return
        try:
            self._ds.light.setColorI(r, g, b)
        except Exception as e:
            print(f"[ERROR] LED hatası: {e}")

    def set_trigger_profile(self, profile_key: str):
        """Apply an adaptive trigger profile."""
        if profile_key not in self.TRIGGER_PROFILES:
            print(f"[ERROR] Bilinmeyen profil: {profile_key}")
            return

        if not self._ds or not self.state.connected:
            print("[WARN] Kontrolcü bağlı değil")
            return

        self._current_trigger_profile = profile_key
        profile = self.TRIGGER_PROFILES[profile_key]

        try:
            self._apply_trigger_effect(
                right_mode=profile["right"]["mode"],
                right_params=profile["right"]["params"],
                left_mode=profile["left"]["mode"],
                left_params=profile["left"]["params"],
            )
            print(f"[INFO] Tetik profili uygulandı: {profile['name']}")
        except Exception as e:
            print(f"[ERROR] Tetik profili hatası: {e}")

    def _patched_prepare_report(self):
        """Monkey-patch for pydualsense to persist our trigger effects.
        Pydualsense continuously writes reports in a bg thread, so we must 
        inject our bytes directly into its loop before it sends."""
        report = self._orig_prepare_report()
        
        # Determine if we have any active effects
        right_mode = self._trigger_right["mode"]
        left_mode = self._trigger_left["mode"]
        
        if right_mode != 0 or left_mode != 0:
            # Check connection type to determine byte offsets
            is_bt = (report[0] == 49) # 0x31 is Bluetooth report ID
            
            flag_byte = 3 if is_bt else 2
            right_offset = 12 if is_bt else 11
            left_offset = 23 if is_bt else 22
            
            # Set valid flags to enable trigger control
            report[1] = 0xFF if not is_bt else 0x02
            report[flag_byte] |= 0x04 | 0x08
            
            # Right trigger effect
            report[right_offset] = right_mode
            for i, val in enumerate(self._trigger_right["params"]):
                report[right_offset + 1 + i] = val & 0xFF
                
            # Left trigger effect
            report[left_offset] = left_mode
            for i, val in enumerate(self._trigger_left["params"]):
                report[left_offset + 1 + i] = val & 0xFF
                
        return report

    def _apply_trigger_effect(self, right_mode: int, right_params: list,
                               left_mode: int, left_params: list):
        """Update adaptive trigger effects.
        Instead of writing the report directly (which gets overwritten by pydualsense),
        we save the state and our monkey-patched prepareReport applies them."""
        self._trigger_right["mode"] = right_mode
        self._trigger_right["params"] = right_params[:9]
        self._trigger_left["mode"] = left_mode
        self._trigger_left["params"] = left_params[:9]
        
        # Trigger an immediate report write to apply instantly
        if self._ds:
            try:
                report = self._ds.prepareReport()
                self._ds.writeReport(report)
            except:
                pass
        
        print(f"[DEBUG] Trigger updated: mode R={right_mode:#x} L={left_mode:#x}")

    @property
    def current_trigger_profile(self):
        return self._current_trigger_profile

    def get_trigger_profiles(self) -> Dict[str, Dict]:
        return self.TRIGGER_PROFILES
