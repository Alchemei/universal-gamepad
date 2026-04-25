import os
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
pygame.display.init()
pygame.joystick.init()
pygame.event.pump()
print("Success pump without set_mode")
