import os
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
pygame.joystick.init()
pygame.event.pump()
print("Count:", pygame.joystick.get_count())
