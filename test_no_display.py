import pygame
import pygame._sdl2.controller as sdl_controller
import os

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

# NO pygame.display.init()
pygame.joystick.init()
try:
    sdl_controller.init()
    pygame.event.pump()
    print("SUCCESS: Pumped without display.init()")
except Exception as e:
    print(f"FAILED: {e}")
