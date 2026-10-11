; Script generated for Inno Setup Installer Generator
; KURO 2.0 Console Application Setup

#define MyAppName "KURO"
#define MyAppVersion "2.0"
#define MyAppPublisher "Akira Omran"
#define MyAppURL "https://github.com/Abdo-omran2206/KuroAgent"

[Setup]
AppId={{D37F89B2-4E21-4F25-8B9A-0A77121E90F4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=KURO_v2_Setup
SetupIconFile=..\assets\kuro_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcuts"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\KuroConsole\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\KURO Console"; Filename: "{app}\KuroConsole.exe"; WorkingDir: "{app}"; IconFilename: "{app}\KuroConsole.exe"
Name: "{autodesktop}\KURO Console"; Filename: "{app}\KuroConsole.exe"; WorkingDir: "{app}"; IconFilename: "{app}\KuroConsole.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KuroConsole.exe"; WorkingDir: "{app}"; Description: "Launch KURO Console"; Flags: nowait postinstall skipifsilent

