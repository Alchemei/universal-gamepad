"""
Multi-Controller Manager
Coordinates up to 2 gamepads (any type) using pygame + optional pydualsense.
"""
import gc, threading, time, ctypes
from dataclasses import dataclass, field
from typing import Callable, Optional
from gamepad import GamepadReader, GamepadState, scan_gamepads, create_reader, init_pygame
import pygame

# Windows Mouse Constants
MOUSEEVENTF_MOVE = 0x0001
def move_mouse(dx, dy):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)

try:
    import vgamepad as vg
    HAS_VGAMEPAD = True
    try:
        from vgamepad.win import vigem_client as vc
    except Exception:
        vc = None
except ImportError:
    HAS_VGAMEPAD = False
    vc = None

try:
    from pydualsense import pydualsense
    HAS_PYDUALSENSE = True
except ImportError:
    HAS_PYDUALSENSE = False

MAX_CONTROLLERS = 2

EMULATION_LABELS = {0: "Direkt", 1: "PS4", 2: "Xbox"}


def _force_remove(device):
    if not device:
        return
    try:
        device.reset(); device.update()
    except Exception:
        pass
    if vc and getattr(device, "_busp", None) and getattr(device, "_devicep", None):
        try: device.unregister_notification()
        except Exception: pass
        try: vc.vigem_target_remove(device._busp, device._devicep)
        except Exception: pass
        try: vc.vigem_target_free(device._devicep)
        except Exception: pass
        try: device._devicep = None
        except Exception: pass


class ControllerSlot:
    """One connected controller slot."""

    def __init__(self, index: int, reader: GamepadReader):
        self.index = index
        self.reader = reader
        self.state = reader.state
        self.emulation_mode = 0
        self._vpad = None
        self._xbox = None
        self._deadzone = 10
        # DualSense-specific
        self._ds = None
        self._is_dualsense = False
        self._last_vibration = (0, 0) # (large, small)
        self._last_touch = None
        self._mouse_sensitivity = 0.15
        self._mouse_filter_x = 0
        self._mouse_filter_y = 0
        self._led_color = (0, 114, 206) # Default PlayStation Blue

        # Detection & Initialization for DualSense Haptics
        name_lower = self.reader.name.lower()
        if "dualsense" in name_lower or "ps5" in name_lower or "wireless controller" in name_lower:
            self._is_dualsense = True
            if HAS_PYDUALSENSE:
                try:
                    # We try to initialize pydualsense for this slot to handle haptic feedback.
                    # If it fails (e.g. handle busy), we fall back to generic pygame rumble.
                    self._ds = pydualsense()
                    self._ds.init()
                    # Apply initial LED color
                    self._ds.light.TouchpadColor = self._led_color
                    print(f"[INFO] DualSense haptics driver linked for: {self.reader.name}")
                except Exception as e:
                    print(f"[DEBUG] DualSense haptics init skipped: {e}")
                    self._ds = None

    @property
    def name(self):
        return self.reader.name

    def set_led_color(self, r, g, b):
        """Sets the LED color of the DualSense controller."""
        self._led_color = (r, g, b)
        if self._ds:
            try:
                self._ds.light.TouchpadColor = (r, g, b)
            except Exception as e:
                print(f"[DEBUG] Failed to set LED color: {e}")

    def set_emulation(self, mode: int):
        self.emulation_mode = mode
        self._destroy_virtual()
        if mode == 1 and HAS_VGAMEPAD:
            try:
                self._vpad = vg.VDS4Gamepad()
                self._vpad.register_notification(callback_function=self._vibration_callback)
                self._vpad.update()
            except Exception as e:
                print(f"[WARN] DS4 olusturulamadi: {e}")
                self._vpad = None
        elif mode == 2 and HAS_VGAMEPAD:
            try:
                self._xbox = vg.VX360Gamepad()
                self._xbox.register_notification(callback_function=self._vibration_callback)
                self._xbox.update()
            except Exception as e:
                print(f"[WARN] Xbox olusturulamadi: {e}")
                self._xbox = None
        time.sleep(0.2)

    def update_virtual(self):
        s = self.state
        
        # DualSense specific: sync touchpad/ps state from pydualsense if available
        # because SDL (reader.poll) often misses them or uses different button IDs.
        if self._ds:
            try:
                s.touchpad = bool(self._ds.state.touchBtn)
                s.ps_button = bool(self._ds.state.ps)
                
                # --- Touchpad Mouse Emulation ---
                t0 = self._ds.state.trackPadTouch0
                if t0.isActive:
                    curr_x, curr_y = t0.X, t0.Y
                    if self._last_touch:
                        dx = (curr_x - self._last_touch[0])
                        dy = (curr_y - self._last_touch[1])
                        
                        # Non-linear acceleration: Mag^1.2
                        mag = (dx*dx + dy*dy)**0.5
                        if mag > 0:
                            # Small movements are slowed, fast movements are boosted
                            accel_scale = (mag ** 0.15) * self._mouse_sensitivity
                            dx *= accel_scale
                            dy *= accel_scale
                        
                        # Limit movement per frame
                        dx = max(-35, min(35, dx))
                        dy = max(-35, min(35, dy))
                        
                        # Exponential Moving Average (EMA) for Smoothing
                        # 60% new value, 40% old value
                        self._mouse_filter_x = self._mouse_filter_x * 0.4 + dx * 0.6
                        self._mouse_filter_y = self._mouse_filter_y * 0.4 + dy * 0.6
                        
                        if abs(self._mouse_filter_x) > 0.1 or abs(self._mouse_filter_y) > 0.1:
                            move_mouse(self._mouse_filter_x, self._mouse_filter_y)
                            
                    self._last_touch = (curr_x, curr_y)
                    s.touchpad = True
                else:
                    self._last_touch = None
                    self._mouse_filter_x = 0
                    self._mouse_filter_y = 0
                # --------------------------------
            except Exception:
                pass

        if self.emulation_mode == 2 and self._xbox:
            self._map_xbox(s)
        elif self.emulation_mode == 1 and self._vpad:
            self._map_ds4(s)

    def _map_xbox(self, s):
        x = self._xbox
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_A) if s.cross else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_B) if s.circle else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_X) if s.square else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_Y) if s.triangle else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER) if s.l1 else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER) if s.r1 else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        x.left_trigger_float(value_float=s.l2 / 255.0)
        x.right_trigger_float(value_float=s.r2 / 255.0)
        lx = max(-1.0, min(1.0, s.left_stick_x / 128.0))
        ly = -max(-1.0, min(1.0, s.left_stick_y / 128.0))
        rx = max(-1.0, min(1.0, s.right_stick_x / 128.0))
        ry = -max(-1.0, min(1.0, s.right_stick_y / 128.0))
        x.left_joystick_float(x_value_float=lx, y_value_float=ly)
        x.right_joystick_float(x_value_float=rx, y_value_float=ry)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB) if s.l3 else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB) if s.r3 else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP) if s.dpad_up else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN) if s.dpad_down else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT) if s.dpad_left else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT) if s.dpad_right else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_START) if s.options else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK) if s.create else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
        
        # Guide/PS Button
        x.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE) if s.ps_button else x.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE)
        
        x.update()

    def _map_ds4(self, s):
        v = self._vpad
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_CROSS) if s.cross else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE) if s.circle else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_SQUARE) if s.square else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE) if s.triangle else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT) if s.l1 else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT) if s.r1 else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
        v.left_trigger_float(value_float=s.l2 / 255.0)
        v.right_trigger_float(value_float=s.r2 / 255.0)
        lx = max(-1.0, min(1.0, s.left_stick_x / 128.0))
        ly = max(-1.0, min(1.0, s.left_stick_y / 128.0))
        rx = max(-1.0, min(1.0, s.right_stick_x / 128.0))
        ry = max(-1.0, min(1.0, s.right_stick_y / 128.0))
        v.left_joystick_float(x_value_float=lx, y_value_float=ly)
        v.right_joystick_float(x_value_float=rx, y_value_float=ry)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT) if s.l3 else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT) if s.r3 else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
        up, dn, lt, rt = s.dpad_up, s.dpad_down, s.dpad_left, s.dpad_right
        d = vg.DS4_DPAD_DIRECTIONS
        dp = d.DS4_BUTTON_DPAD_NONE
        if up and rt: dp = d.DS4_BUTTON_DPAD_NORTHEAST
        elif up and lt: dp = d.DS4_BUTTON_DPAD_NORTHWEST
        elif dn and rt: dp = d.DS4_BUTTON_DPAD_SOUTHEAST
        elif dn and lt: dp = d.DS4_BUTTON_DPAD_SOUTHWEST
        elif up: dp = d.DS4_BUTTON_DPAD_NORTH
        elif dn: dp = d.DS4_BUTTON_DPAD_SOUTH
        elif lt: dp = d.DS4_BUTTON_DPAD_WEST
        elif rt: dp = d.DS4_BUTTON_DPAD_EAST
        v.directional_pad(direction=dp)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS) if s.options else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
        v.press_button(vg.DS4_BUTTONS.DS4_BUTTON_SHARE) if s.create else v.release_button(vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
        
        # PS and Touchpad (Special buttons in vgamepad)
        v.press_special_button(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS) if s.ps_button else v.release_special_button(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
        v.press_special_button(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD) if s.touchpad else v.release_special_button(vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_TOUCHPAD)
        
        v.update()
    def _vibration_callback(self, client, target, large_motor, small_motor, led_number, user_data):
        """Called by ViGEmBus when the game sends vibration data."""
        # Convert 0..255 to 0.0..1.0 for generic, and 0..255 for DualSense
        low = large_motor / 255.0
        high = small_motor / 255.0
        
        # Apply to physical controller
        if self._ds:
            try:
                # pydualsense uses 0-255 range for motors
                self._ds.setLeftMotor(large_motor)
                self._ds.setRightMotor(small_motor)
            except Exception as e:
                print(f"[DEBUG] DualSense motor error: {e}")
                # Fallback to pygame rumble if pydualsense fails
                self.reader.rumble(low, high, 1000)
        else:
            self.reader.rumble(low, high, 1000)
            
        self._last_vibration = (low, high)

    def rumble(self, low: float, high: float, duration_ms: int):
        """Unified rumble method for both DualSense and standard controllers."""
        if self._ds:
            try:
                # Convert 0.0-1.0 to 0-255
                self._ds.setLeftMotor(int(low * 255))
                self._ds.setRightMotor(int(high * 255))
                
                # Start a timer to stop motors after duration_ms
                def stop():
                    time.sleep(duration_ms / 1000.0)
                    if self._ds:
                        try:
                            self._ds.setLeftMotor(0)
                            self._ds.setRightMotor(0)
                        except: pass
                threading.Thread(target=stop, daemon=True).start()
                return
            except Exception as e:
                print(f"[DEBUG] DualSense test rumble error: {e}")
        
        # Fallback to generic pygame rumble
        self.reader.rumble(low, high, duration_ms)

    def _destroy_virtual(self):
        for dev in (self._vpad, self._xbox):
            _force_remove(dev)
        self._vpad = None
        self._xbox = None
        gc.collect()

    def destroy(self):
        self._destroy_virtual()
        if self._ds:
            try:
                self._ds.close()
            except:
                pass
            self._ds = None
        self.state.connected = False


class MultiControllerManager:
    """Manages up to 2 gamepads of any type."""

    def __init__(self):
        self.slots: list[ControllerSlot] = []
        self._running = False
        self._thread = None
        self._poll_rate = 0.004
        self._on_state_change = None
        self._on_connection_change = None
        self.paused = False
        self._prev_states = {} # slot_idx -> last known state bits

    @property
    def has_vgamepad(self):
        return HAS_VGAMEPAD

    @property
    def connected_count(self):
        return len(self.slots)

    def set_on_state_change(self, cb):
        self._on_state_change = cb

    def set_on_connection_change(self, cb):
        self._on_connection_change = cb

    def scan(self) -> list[dict]:
        return scan_gamepads()

    def is_driver_installed(self) -> bool:
        """Checks if ViGEmBus driver is installed via Registry."""
        import os
        if os.name != "nt": return False
        try:
            import winreg
            path = r"SYSTEM\CurrentControlSet\Services\ViGEmBus"
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            return True
        except:
            return False

    def connect_all(self, default_mode=2) -> tuple[bool, str]:
        """Connect all detected gamepads (max 2)."""
        found = scan_gamepads()
        if not found:
            return False, "Hicbir kol bulunamadi! USB ile baglayin."

        # Step 1: Bind to all physical controllers first
        temp_slots = []
        for info in found[:MAX_CONTROLLERS]:
            try:
                reader = create_reader(info["index"])
                slot = ControllerSlot(info["index"], reader)
                temp_slots.append(slot)
                print(f"[INFO] Fiziksel baglanti kuruldu: {info['name']}")
            except Exception as e:
                print(f"[ERROR] Kol baglanamadi: {e}")

        if not temp_slots:
            return False, "Kollara baglanilamadi."

        # Step 2: Start emulation for each ONLY after all physical handles are secured
        for slot in temp_slots:
            slot.set_emulation(default_mode)
            self.slots.append(slot)
            
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        if self._on_connection_change:
            self._on_connection_change(True)

        names = ", ".join(s.name for s in self.slots)
        return True, f"{len(self.slots)} kol baglandi: {names}"

    def disconnect_all(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        for slot in self.slots:
            slot.destroy()
        self.slots.clear()
        if self._on_connection_change:
            self._on_connection_change(False)

    def set_slot_emulation(self, slot_idx: int, mode: int):
        if 0 <= slot_idx < len(self.slots):
            self.slots[slot_idx].set_emulation(mode)

    def pump_events(self):
        from gamepad import SDL_LOCK
        try:
            with SDL_LOCK:
                pygame.event.pump()
        except Exception:
            pass

    def test_rumble(self, slot_idx: int):
        """Triggers a short vibration test on the specified controller slot."""
        if 0 <= slot_idx < len(self.slots):
            print(f"[DEBUG] Titresim testi baslatiliyor: Slot {slot_idx}")
            self.slots[slot_idx].rumble(1.0, 1.0, 1000)

    def _poll_loop(self):
        while self._running:
            if self.paused:
                time.sleep(0.05)
                continue
                
            try:
                any_changed = False
                for slot in self.slots:
                    slot.reader.poll()
                    
                    # Basic change detection to reduce GUI stress
                    current_bits = hash(str(slot.state.__dict__) if hasattr(slot.state, "__dict__") else str(id(slot.state)))
                    # Actually, a better way is to compare important fields
                    s = slot.state
                    state_sum = (s.cross, s.circle, s.square, s.triangle, s.l1, s.r1, s.l2, s.r2, 
                                 s.left_stick_x, s.left_stick_y, s.right_stick_x, s.right_stick_y,
                                 s.dpad_up, s.dpad_down, s.dpad_left, s.dpad_right,
                                 s.ps_button, s.touchpad, s.options, s.create, s.mute,
                                 s.l3, s.r3)
                    
                    if self._prev_states.get(slot.index) != state_sum:
                        self._prev_states[slot.index] = state_sum
                        any_changed = True
                    
                    slot.update_virtual()
                    
                if any_changed and self._on_state_change:
                    self._on_state_change()
                    
            except Exception as e:
                print(f"[ERROR] Poll: {e}")
            time.sleep(self._poll_rate)
