import os
import time
import threading
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
pygame.display.init()
pygame.joystick.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)

j = pygame.joystick.Joystick(0)

running = True
def poll_loop():
    while running:
        # access from background thread
        btn = j.get_button(0)
        time.sleep(0.01)

t = threading.Thread(target=poll_loop)
t.start()

# pump on main thread
for _ in range(50):
    pygame.event.pump()
    time.sleep(0.01)

running = False
t.join()
print("Success")
