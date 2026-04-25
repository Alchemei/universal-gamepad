import pygame
import time

def test_all_vibration():
    pygame.init()
    pygame.joystick.init()
    
    count = pygame.joystick.get_count()
    print(f"Sistemde {count} kol bulundu.")
    
    for i in range(count):
        joy = pygame.joystick.Joystick(i)
        joy.init()
        print(f"Deneniyor: {joy.get_name()} (Slot {i})")
        
        # Test 1: Standard Rumble
        print("  - Standart Titresim komutu gonderiliyor...")
        res = joy.rumble(1.0, 1.0, 2000)
        print(f"  - Komut sonucu: {res} (True ise kol destekliyor demektir)")
        
        time.sleep(2.5)
        joy.quit()

if __name__ == "__main__":
    test_all_vibration()
