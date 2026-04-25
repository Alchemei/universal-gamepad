import os, threading
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
import pygame._sdl2.controller as sdl_controller

# Fallback generic mapping for unrecognized gamepads (not in SDL DB)
GENERIC_12BTN = {
    "buttons": {0: "triangle", 1: "circle", 2: "cross", 3: "square",
                4: "l2_btn", 5: "r2_btn", 6: "l1", 7: "r1",
                8: "create", 9: "options", 10: "l3", 11: "r3"},
    "axes": {0: "left_stick_x", 1: "left_stick_y", 2: "right_stick_x", 3: "right_stick_y"},
    "hat_dpad": True,
    "triggers_analog": False,
}

class GamepadState:
    __slots__ = (
        "cross", "circle", "square", "triangle",
        "l1", "r1", "l2", "r2",
        "left_stick_x", "left_stick_y", "right_stick_x", "right_stick_y",
        "l3", "r3",
        "dpad_up", "dpad_down", "dpad_left", "dpad_right",
        "options", "create", "ps_button", "touchpad", "mute",
        "connected", "battery_level", "connection_type",
        "controller_name", "controller_index",
    )

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, False)
        self.l2 = 0
        self.r2 = 0
        self.left_stick_x = 0
        self.left_stick_y = 0
        self.right_stick_x = 0
        self.right_stick_y = 0
        self.battery_level = 0
        self.connection_type = "—"
        self.controller_name = ""
        self.controller_index = -1

class GamepadReader:
    def __init__(self, index: int):
        self.index = index
        self.is_sdl_controller = sdl_controller.is_controller(index)
        
        if self.is_sdl_controller:
            self.device = sdl_controller.Controller(index)
            self.device.init()
            self.name = self.device.name
            self.num_buttons = 15 # Standard SDL
            self.num_axes = 6
        else:
            self.device = pygame.joystick.Joystick(index)
            self.device.init()
            self.name = self.device.get_name()
            self.num_buttons = self.device.get_numbuttons()
            self.num_axes = self.device.get_numaxes()

        self.state = GamepadState()
        self.state.controller_name = self.name
        self.state.controller_index = index
        self.state.connection_type = "USB"
        self.state.connected = True
        self._deadzone = 0.08
        self.swap_triggers = False

    def poll(self):
        s = self.state
        dev = self.device
        
        if self.is_sdl_controller:
            with SDL_LOCK:
                s.cross = bool(dev.get_button(0))
                s.circle = bool(dev.get_button(1))
                s.square = bool(dev.get_button(2))
                s.triangle = bool(dev.get_button(3))
                s.create = bool(dev.get_button(4))
                s.ps_button = bool(dev.get_button(5))
                s.options = bool(dev.get_button(6))
                s.l3 = bool(dev.get_button(7))
                s.r3 = bool(dev.get_button(8))
                s.l1 = bool(dev.get_button(9))
                s.r1 = bool(dev.get_button(10))
                s.dpad_up = bool(dev.get_button(11))
                s.dpad_down = bool(dev.get_button(12))
                s.dpad_left = bool(dev.get_button(13))
                s.dpad_right = bool(dev.get_button(14))
                
                try: s.touchpad = bool(dev.get_button(20))
                except: s.touchpad = False

                lx = dev.get_axis(0) / 32768.0
                ly = dev.get_axis(1) / 32768.0
                rx = dev.get_axis(2) / 32768.0
                ry = dev.get_axis(3) / 32768.0
                l2_raw = dev.get_axis(4)
                r2_raw = dev.get_axis(5)

            s.l2 = int((l2_raw / 32767.0) * 255) if l2_raw > 0 else 0
            s.r2 = int((r2_raw / 32767.0) * 255) if r2_raw > 0 else 0
            s.left_stick_x = int(lx * 128) if abs(lx) > self._deadzone else 0
            s.left_stick_y = int(ly * 128) if abs(ly) > self._deadzone else 0
            s.right_stick_x = int(rx * 128) if abs(rx) > self._deadzone else 0
            s.right_stick_y = int(ry * 128) if abs(ry) > self._deadzone else 0
        else:
            # Fallback for unrecognized generic gamepads using raw Joystick API
            with SDL_LOCK:
                btn_map = GENERIC_12BTN["buttons"]
                for idx, field in btn_map.items():
                    if idx < self.num_buttons:
                        val = bool(dev.get_button(idx))
                        if field == "l2_btn":
                            s.l2 = 255 if val else 0
                        elif field == "r2_btn":
                            s.r2 = 255 if val else 0
                        else:
                            setattr(s, field, val)
                            
                axes_map = GENERIC_12BTN["axes"]
                for idx, field in axes_map.items():
                    if idx < self.num_axes:
                        raw = dev.get_axis(idx)
                        if abs(raw) < self._deadzone:
                            raw = 0.0
                        setattr(s, field, int(raw * 128))
                        
                if dev.get_numhats() > 0:
                    hx, hy = dev.get_hat(0)
                    s.dpad_left = hx < 0
                    s.dpad_right = hx > 0
                    s.dpad_up = hy > 0
                    s.dpad_down = hy < 0

        # Post-process: Swap triggers if requested
        if self.swap_triggers:
            l1_val, r1_val = s.l1, s.r1
            s.l1 = s.l2 > 127
            s.r1 = s.r2 > 127
            s.l2 = 255 if l1_val else 0
            s.r2 = 255 if r1_val else 0

    def rumble(self, low_freq: float, high_freq: float, duration_ms: int):
        """Trigger physical vibration on the controller."""
        from gamepad import SDL_LOCK
        with SDL_LOCK:
            try:
                # Use the raw Joystick object for rumble as it's often more reliable
                joy = None
                if hasattr(self.device, "as_joystick"):
                    joy = self.device.as_joystick()
                else:
                    joy = self.device
                
                if joy:
                    # Double-tap the rumble to ensure it wakes up
                    joy.rumble(low_freq, high_freq, duration_ms)
                    # For some controllers, we also try setting the frequency directly if supported
                    try: joy.rumble(1.0, 1.0, 500) if low_freq > 0 else None
                    except: pass
            except Exception as e:
                print(f"[DEBUG] Rumble Error: {e}")

_pygame_inited = False
_pygame_lock = threading.Lock()
SDL_LOCK = threading.Lock() # Global lock for all SDL calls (pump, get_button, etc.)

def init_pygame():
    global _pygame_inited
    with _pygame_lock:
        if not _pygame_inited:
            pygame.display.init()
            pygame.joystick.init()
            sdl_controller.init()
            _pygame_inited = True

def scan_gamepads() -> list[dict]:
    init_pygame()
    from gamepad import SDL_LOCK
    with SDL_LOCK:
        pygame.event.pump()
    result = []
    for i in range(pygame.joystick.get_count()):
        j_temp = pygame.joystick.Joystick(i)
        try:
            name = j_temp.get_name()
            # Log all found devices for debugging
            print(f"[DEBUG] Tarama: Slot {i} -> {name}")
            
            # Aggressive filter: Skip anything that looks like a virtual controller
            # unless it's the ONLY thing connected.
            name_lower = name.lower()
            is_virtual = any(vn in name_lower for vn in ("xbox 360", "dualshock 4", "vigem", "virtual"))
            
            if is_virtual and pygame.joystick.get_count() > 1:
                print(f"[DEBUG] Sanal/Hayalet kol elendi: {name} (Slot {i})")
                continue

            is_ctrl = sdl_controller.is_controller(i)
            if is_ctrl:
                c = sdl_controller.Controller(i)
                result.append({
                    "index": i,
                    "name": c.name,
                    "guid": "SDL_Standard",
                    "buttons": 15,
                    "axes": 6,
                    "hats": 0,
                })
                c.quit()
            else:
                result.append({
                    "index": i,
                    "name": name,
                    "guid": j_temp.get_guid(),
                    "buttons": j_temp.get_numbuttons(),
                    "axes": j_temp.get_numaxes(),
                    "hats": j_temp.get_numhats(),
                })
        finally:
            j_temp.quit()
    return result

def create_reader(index: int) -> GamepadReader:
    init_pygame()
    return GamepadReader(index)
