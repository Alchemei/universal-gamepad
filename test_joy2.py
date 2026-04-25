import os
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
pygame.joystick.init()
count = pygame.joystick.get_count()
print("Count:", count)
if count > 0:
    j = pygame.joystick.Joystick(0)
    print("Name:", j.get_name())
    pygame.joystick.quit()
