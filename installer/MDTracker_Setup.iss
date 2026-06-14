; ============================================================
; MDTracker - Inno Setup 인스톨러 스크립트
; 빌드: ISCC installer\MDTracker_Setup.iss
; 출력: installer\Output\MDTracker_Setup_v*.exe
;
; 전제 조건:
;   - PyInstaller 빌드 완료 → dist\MDTracker\ 존재
;   - Tesseract가 dist\MDTracker\tesseract\ 에 번들됨
; ============================================================

#define AppName      "MDTracker"
#define AppVersion   "0.2.0"
#define AppPublisher "MDTracker"
#define AppURL       "https://github.com/maroofloor/mdtracker"
#define AppExeName   "MDTracker.exe"
#define SourceDir    "..\dist\MDTracker"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; 이전 버전 자동 언인스톨 (같은 AppId 사용)
CloseApplications=yes
CloseApplicationsFilter=MDTracker.exe
RestartApplications=no
OutputDir=Output
OutputBaseFilename=MDTracker_Setup_v{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest          ; 관리자 권한 불필요 (사용자 AppData 설치)
PrivilegesRequiredOverridesAllowed=dialog

; 아이콘 (빌드 전 .ico 파일로 변환 권장)
; SetupIconFile=..\assets\icon.ico

; 버전 정보
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "korean";  MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked

[Files]
; 빌드된 앱 전체 복사
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 설정 예시 파일 → AppData에 복사 (덮어쓰지 않음)
Source: "..\ocr_config.example.json"; DestDir: "{userappdata}\{#AppName}"; \
  DestName: "ocr_config.json"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} 언인스톨"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; 설치 완료 후 바로 실행 옵션
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 언인스톨 시 앱이 생성한 캐시/로그 정리 (DB는 보존)
Type: filesandordirs; Name: "{userappdata}\{#AppName}\__pycache__"

[Code]
// ────────────────────────────────────────────────────────────────────────────
// 이전 버전 감지 및 자동 언인스톨
// ────────────────────────────────────────────────────────────────────────────
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','',
            SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) then begin
    if (IsUpgrade()) then
      UnInstallOldVersion();
  end;
end;
