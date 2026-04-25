import os
import sys
import subprocess
import urllib.request
import ctypes
import platform

VIGEM_URL = "https://github.com/ViGEm/ViGEmBus/releases/download/v1.17.333.0/ViGEmBus_Setup_1.17.333.0.exe"
# Use absolute path to avoid confusion
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALLER_NAME = os.path.join(BASE_DIR, "ViGEmBus_Setup.exe")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_vigembus():
    """Checks if ViGEmBus is installed by looking at the Windows Registry."""
    if platform.system() != "Windows":
        return False
        
    try:
        import winreg
        # ViGEmBus installation usually creates this service key
        key_path = r"SYSTEM\CurrentControlSet\Services\ViGEmBus"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                return True
        except FileNotFoundError:
            # Try an alternative check: is the DLL/client reachable?
            import vgamepad as vg
            return True # If vgamepad is imported, the library is there
    except Exception as e:
        print(f"[DEBUG] ViGEmBus Registry Check Error: {e}")
        return False

def download_installer(progress_callback=None):
    """Downloads the ViGEmBus installer using a browser-like User-Agent."""
    print(f"[INFO] Indirme basliyor: {VIGEM_URL}")
    try:
        req = urllib.request.Request(VIGEM_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.info().get('Content-Length', 0))
            print(f"[INFO] Dosya boyutu: {total_size} bytes")
            
            with open(INSTALLER_NAME, 'wb') as out_file:
                downloaded = 0
                block_size = 16384
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if progress_callback and total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        progress_callback(percent)
        
        print(f"[INFO] Indirme tamamlandi: {INSTALLER_NAME}")
        return True
    except Exception as e:
        print(f"[ERROR] Indirme hatasi: {e}")
        return False

def run_installer():
    """Runs the installer normally so the user can see the progress."""
    if not os.path.exists(INSTALLER_NAME):
        return False
    
    try:
        # Run it non-silently so user sees the UAC and installation wizard
        os.startfile(INSTALLER_NAME)
        return True
    except Exception as e:
        print(f"Run error: {e}")
        return False

def install_logic(progress_callback=None):
    """Full installation flow."""
    if check_vigembus():
        return True, "Zaten yuklu."
    
    if progress_callback: progress_callback(10)
    if not download_installer(progress_callback):
        return False, "Indirme basarisiz oldu."
    
    if progress_callback: progress_callback(90)
    if not run_installer():
        return False, "Kurulum baslatilamadi."
    
    return True, "Kurulum tamamlandi. Lutfen bilgisayarinizi yeniden baslatin."
