; -- Universal Gamepad Setup Script --

[Setup]
AppName=Universal Gamepad
AppVersion=1.0
DefaultDirName={autopf}\Universal Gamepad
DefaultGroupName=Universal Gamepad
UninstallDisplayIcon={app}\Universal Gamepad.exe
Compression=lzma2
SolidCompression=yes
OutputDir=userdocs:Inno Setup Outputs
OutputBaseFilename=Universal_Gamepad_Setup
SetupIconFile=C:\apps\dualsense\logo.ico
PrivilegesRequired=admin

[Files]
Source: "C:\apps\dualsense\dist\Universal Gamepad.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Universal Gamepad"; Filename: "{app}\Universal Gamepad.exe"
Name: "{commondesktop}\Universal Gamepad"; Filename: "{app}\Universal Gamepad.exe"; IconFilename: "{app}\Universal Gamepad.exe"

[Run]
Filename: "{app}\Universal Gamepad.exe"; Description: "Uygulamayi Baslat"; Flags: nowait postinstall skipifsilent
