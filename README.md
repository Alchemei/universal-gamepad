# 🎮 Universal Gamepad PC Manager

A professional, high-performance gamepad management application designed for PC. This tool allows you to connect multiple controllers (DualSense, DualShock, etc.) and emulate them as **Xbox 360** or **DualShock 4** controllers for maximum compatibility with all PC games.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.14%2B-blue.svg)
![GUI](https://img.shields.io/badge/UI-CustomTkinter-blue.svg)

## ✨ Features

- **Multi-Controller Support:** Connect and manage multiple controllers simultaneously.
- **Advanced Emulation:** Seamlessly emulate controllers as Xbox 360 or PS4 devices using the ViGEmBus driver.
- **Premium GUI:** Sleek, modern interface inspired by PlayStation aesthetics with glassmorphism and smooth animations.
- **Real-time Feedback:** Visualize button presses, analog stick movements, and touchpad activity instantly.
- **Full Localization:** Native support for English and Turkish languages.
- **Settings Persistence:** Remembers your language and preferred gaming modes.
- **Vibration Testing:** Built-in tool to verify haptic feedback functionality.
- **Swap Triggers:** Option to swap L1/R1 with L2/R2 for custom gameplay styles.

## 🚀 Getting Started

### Prerequisites

1. **Python 3.14+**
2. **ViGEmBus Driver:** Required for virtual controller emulation. (Included in the installer)
3. **Dependencies:** Install required Python packages:
   ```bash
   pip install pygame-ce customtkinter vgamepad
   ```

### Installation

You can use the provided professional installer to set up everything on your system:
- Download and run `Universal_Gamepad_Setup.exe`.
- Follow the on-screen instructions to install the application and necessary drivers.

### Running from Source

If you prefer to run the source code directly:
```bash
python main.py
```

## 🛠️ Technology Stack

- **Core:** Python
- **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Engine:** [Pygame-CE](https://github.com/pygame-ce/pygame-ce)
- **Emulation:** [vgamepad](https://github.com/yannbouteiller/vgamepad)
- **Packaging:** PyInstaller & Inno Setup

## 📜 License

This project is licensed under the MIT License.

---
*Created with ❤️ for gamers.*
