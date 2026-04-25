import os
import sys

# Mock pygame.joystick
class MockJoystick:
    def __init__(self, index):
        self.index = index
    def get_name(self): return f"Mock Pad {self.index}"
    def get_guid(self): return "0000"
    def get_numbuttons(self): return 12
    def get_numaxes(self): return 4
    def get_numhats(self): return 1
    def get_instance_id(self): return self.index
    def get_button(self, i): return 0
    def get_axis(self, i): return 0.0
    def get_hat(self, i): return (0, 0)
    def init(self): pass

import pygame
pygame.joystick = type('Mock', (), {})()
pygame.joystick.get_count = lambda: 2
pygame.joystick.Joystick = MockJoystick
pygame.joystick.init = lambda: None
pygame.joystick.quit = lambda: None
pygame.display = type('Mock', (), {})()
pygame.display.init = lambda: None
pygame.display.set_mode = lambda *args, **kwargs: None
pygame.event = type('Mock', (), {})()
pygame.event.pump = lambda: None
pygame.NOFRAME = 0

# Also mock vgamepad to avoid ViGEmBus requirements during test
import vgamepad
vgamepad.VX360Gamepad = type('MockX', (), {'update': lambda s: None, 'reset': lambda s: None})
vgamepad.VDS4Gamepad = type('MockD', (), {'update': lambda s: None, 'reset': lambda s: None})

sys.modules['pygame'] = pygame

# Import gui and test
from gui import DualSenseGUI
app = DualSenseGUI()
print("GUI Init OK")
app.after(1000, app.destroy)
app.mainloop()
