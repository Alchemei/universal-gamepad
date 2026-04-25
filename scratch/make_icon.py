from PIL import Image
import os

def convert_to_ico():
    input_path = 'dist/logo.png'
    output_path = 'logo.ico'
    
    if not os.path.exists(input_path):
        print(f"Hata: {input_path} bulunamadi!")
        return
        
    img = Image.open(input_path)
    # Standard sizes for Windows icons
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, sizes=icon_sizes)
    print(f"Basarili: {output_path} olusturuldu.")

if __name__ == "__main__":
    convert_to_ico()
