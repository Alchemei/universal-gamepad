import pygame
import pygame._sdl2.controller as sdl_controller
import time
import os

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

def test():
    pygame.init()
    pygame.joystick.init()
    sdl_controller.init()
    
    count = pygame.joystick.get_count()
    print(f"Sistemde {count} adet kol bulundu.")
    
    if count == 0:
        print("Hata: Kol bulunamadi!")
        return

    for i in range(count):
        print(f"\n--- Deneniyor: Kol {i} ---")
        try:
            # Method 1: Joystick API
            j = pygame.joystick.Joystick(i)
            j.init()
            print(f"Isim: {j.get_name()}")
            print("Joystick API ile titretiliyor...")
            j.rumble(1.0, 1.0, 1000)
            time.sleep(1.2)
            
            # Method 2: Controller API
            if sdl_controller.is_controller(i):
                c = sdl_controller.Controller(i)
                c.init()
                print("Controller API ile titretiliyor...")
                c.rumble(1.0, 1.0, 1000)
                time.sleep(1.2)
        except Exception as e:
            print(f"Hata olustu: {e}")

    print("\nTest bitti. Eger kolunuz titremediyse donanimsal veya surucu kaynakli bir kisitlama olabilir.")
    pygame.quit()

if __name__ == "__main__":
    test()
