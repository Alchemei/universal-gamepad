"""Scan all connected gamepads using pygame."""
import os
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
import pygame
pygame.display.init()
pygame.joystick.init()
screen = pygame.display.set_mode((1, 1))

count = pygame.joystick.get_count()
print(f"Bulunan kol sayisi: {count}")
for i in range(count):
    j = pygame.joystick.Joystick(i)
    j.init()
    print(f"\n--- Kol {i} ---")
    print(f"  Isim: {j.get_name()}")
    print(f"  GUID: {j.get_guid()}")
    print(f"  Buton: {j.get_numbuttons()}")
    print(f"  Eksen: {j.get_numaxes()}")
    print(f"  Hat:   {j.get_numhats()}")

if count == 0:
    print("Hicbir kol bulunamadi! Kolu USB ile baglayin.")

pygame.quit()
