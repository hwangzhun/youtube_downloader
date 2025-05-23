#define MyAppName "YouTube Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Hwangzhun"
#define MyAppURL "https://github.com/hwangzhun/youtube_downloader"
#define MyAppExeName "YouTube_Downloader.exe"

[Setup]
; 注意: AppId的值为单独标识该应用程序。
; 不要为其他安装程序使用相同的AppId值。
AppId={{A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=YouTube_Downloader_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=resources\icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; 权限设置
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
DirExistsWarning=no
AllowUNCPath=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序文件
Source: "dist\YouTube_Downloader\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\YouTube_Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 资源文件（不包含二进制文件）
Source: "resources\icons\*"; DestDir: "{app}\resources\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; 设置安装目录的权限
Name: "{app}"; Permissions: everyone-full
Name: "{app}\resources"; Permissions: everyone-full
Name: "{app}\resources\binaries"; Permissions: everyone-full
Name: "{app}\resources\binaries\yt-dlp"; Permissions: everyone-full
Name: "{app}\resources\binaries\ffmpeg"; Permissions: everyone-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[Code]
var
  ResultCode: Integer;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 添加管理员权限请求和设置安装目录的权限
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    if not IsAdminLoggedOn then
    begin
      MsgBox('此应用程序需要管理员权限才能正常运行。', mbInformation, MB_OK);
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    // 设置安装目录的完全控制权限
    if not Exec('icacls', '"' + ExpandConstant('{app}') + '" /grant Everyone:(OI)(CI)F /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox('设置目录权限失败。', mbError, MB_OK);
    end;
  end;
end; 