; Installer of Shielding of X-ray Rooms (Inno Setup 6).
; Build it with:  venv\Scripts\python.exe installer\build_installer.py
; The script first packs the program with PyInstaller into build\dist, then compiles this file.

#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "build\dist\Shielding of X-ray Rooms"
#endif
#define AppName "Shielding of X-ray Rooms"
#define AppExe "Shielding of X-ray Rooms.exe"
#define ProgId "ShieldingXrayRooms.Project"

[Setup]
; The AppId identifies the program for updates and uninstall: never change it
AppId={{BDC0CCC4-E97E-42D2-893B-A312F2995080}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Stavros Savvakis
AppPublisherURL=https://github.com/Shiramis/Shielding_of_X-Ray_rooms.py
AppSupportURL=https://github.com/Shiramis/Shielding_of_X-Ray_rooms.py
AppComments=Structural shielding design for medical X-ray imaging facilities (NCRP Report No. 147)
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} setup
; For the current user (no administrator rights needed) or, if chosen, for all users
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=Output
OutputBaseFilename=Shielding_of_X-ray_Rooms_Setup_{#AppVersion}
SetupIconFile=..\XRIFSC_code\app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=build\wizard_large.bmp
WizardSmallImageFile=build\wizard_small.bmp
Compression=lzma2/ultra64
SolidCompression=yes
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.FileTypes=File types:
english.Associate=Open project files (.shield) with {#AppName}
english.UserGuide=User Guide

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "association"; Description: "{cm:Associate}"; GroupDescription: "{cm:FileTypes}"

[InstallDelete]
; files of an older version that the new one no longer has
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Examples\*.shield"; DestDir: "{app}\Examples"; Flags: ignoreversion
Source: "..\Examples\NCRP 147\*.shield"; DestDir: "{app}\Examples\NCRP 147"; Flags: ignoreversion
Source: "..\Examples\NCRP 147\*.xlsx"; DestDir: "{app}\Examples\NCRP 147"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autoprograms}\{#AppName}\{cm:UserGuide}"; Filename: "{app}\User Guide.pdf"
Name: "{autoprograms}\{#AppName}\Examples"; Filename: "{app}\Examples"
Name: "{autoprograms}\{#AppName}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; .shield project files open with the program (per user, or for all users when installed for all)
; (uninstall goes through these lines from the bottom up, so the emptied keys are removed too)
Root: HKA; Subkey: "Software\Classes\.shield"; ValueType: string; ValueName: ""; ValueData: "{#ProgId}"; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: association
Root: HKA; Subkey: "Software\Classes\.shield\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: association
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "Shielding project"; Flags: uninsdeletekey; Tasks: association
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: association
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: association
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; Flags: uninsdeletekey; Tasks: association
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".shield"; ValueData: ""; Tasks: association

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
