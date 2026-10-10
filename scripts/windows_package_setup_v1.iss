#define ReleaseId "@RELEASE@"
[Setup]
AppId={code:GetAppIdentity}
AppName=大A交易
AppVersion=1.0.0
AppVerName=大A交易 {#ReleaseId}
DefaultDirName=@PROGRAM_ROOT@\{#ReleaseId}
DefaultGroupName=大A交易
DisableProgramGroupPage=yes
DisableDirPage=yes
UsePreviousAppDir=no
UsePreviousLanguage=no
UsePreviousTasks=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=@OUTPUT@
OutputBaseFilename=setup-core
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=no
RestartApplications=no
UninstallFilesDir={app}
DisableReadyMemo=no
ChangesAssociations=no
WizardStyle=modern
SetupLogging=yes
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
[Files]
Source: "@PACKAGE@\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "@CONTENT_MANIFEST@"; DestDir: "{app}"; DestName: "PACKAGE_FILES_MANIFEST.json"; Flags: ignoreversion
[Tasks]
Name: "autologin"; Description: "登录Windows后启动（真实采集需要应用、引擎运行且日更未暂停）"; Flags: unchecked
[Code]
var Workspace: String; Lease: TFileStream; RunKey: String;
    LoginDefaultApplied, PreviousLoginEnabled: Boolean;
function GetAppIdentity(Param: String): String;
begin
  Result := '@APP_ID@_'+Copy(GetSHA256OfString(Lowercase(ExpandFileName(ExpandConstant('{param:DIR|@PROGRAM_ROOT@\{#ReleaseId}}')))),1,20);
end;
procedure WriteShortcut(Name, Target, Args: String);
var Shell, Link: Variant;
begin
  Shell := CreateOleObject('WScript.Shell'); Link := Shell.CreateShortcut(Name);
  Link.TargetPath := Target; Link.Arguments := Args;
  Link.WorkingDirectory := ExtractFileDir(Target); Link.Save;
end;
procedure RemoveOwnedShortcut(Name, Target: String);
var Shell, Link: Variant;
begin
  if not FileExists(Name) then exit;
  Shell := CreateOleObject('WScript.Shell'); Link := Shell.CreateShortcut(Name);
  if CompareText(Link.TargetPath,Target)=0 then DeleteFile(Name);
end;
function GPath(P: String): Boolean;
begin Result := (CompareText(Copy(ExpandFileName(P),1,3),'G:\')=0); end;
function Under(P, R: String): Boolean;
begin Result := Pos(Lowercase(AddBackslash(ExpandFileName(R))),Lowercase(AddBackslash(ExpandFileName(P))))=1; end;
function AcquireWorkspace: Boolean;
begin
  Result := False;
  if not GPath(Workspace) or not FileExists(AddBackslash(Workspace)+'runtime\desktop\app.lock') then exit;
  try
    Lease := TFileStream.Create(AddBackslash(Workspace)+'runtime\desktop\app.lock',fmOpenReadWrite or fmShareExclusive);
    Result := True;
  except
    Log('WORKSPACE_ALREADY_OWNED_OR_UNAVAILABLE; use the existing tray to exit safely.');
  end;
end;
function InitializeSetup: Boolean;
begin
  Workspace := ExpandConstant('{param:WORKSPACE|G:\codex work\大A交易}');
  RunKey := '@RUN_KEY@';
  Result := AcquireWorkspace;
  if not Result and not WizardSilent then MsgBox('工作区尚被占用或无法核验。请先从已有托盘安全退出，再安装。',mbError,MB_OK);
end;
procedure InitializeWizard;
var Previous: String;
begin
  PreviousLoginEnabled := RegQueryStringValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey,Previous) and (Previous<>'');
end;
procedure ApplyLoginDefault;
begin
  if LoginDefaultApplied then exit;
  if (ExpandConstant('{param:TASKS|__UNSPECIFIED__}')='__UNSPECIFIED__') and
     (ExpandConstant('{param:MERGETASKS|__UNSPECIFIED__}')='__UNSPECIFIED__') then begin
    if PreviousLoginEnabled then WizardSelectTasks('autologin')
    else WizardSelectTasks('!autologin');
  end;
  LoginDefaultApplied := True;
end;
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID=wpSelectTasks then ApplyLoginDefault;
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
var P: String;
begin
  ApplyLoginDefault;
  Result := ''; P := ExpandConstant('{app}');
  if not GPath(P) or not Under(P,'@PROGRAM_ROOT@') or (CompareText(P,'@PROGRAM_ROOT@')=0)
     or Under(P,Workspace) or Under(Workspace,P) then Result := 'SEPARATE_G_VERSION_DIRECTORY_REQUIRED';
  if FileExists(AddBackslash(P)+'DaAV4.exe') and not FileExists(AddBackslash(P)+'installed-workspace.txt') then
     Result := 'UNOWNED_EXISTING_PROGRAM_DIRECTORY';
end;
@VERIFY_PROGRAM_FILES_CODE@
procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer; Args, Report, OldRun: String; Binding: TArrayOfString;
begin
  if CurStep=ssPostInstall then begin
    VerifyProgramFiles;
    SetArrayLength(Binding,1); Binding[0] := Workspace;
    if not SaveStringsToUTF8File(ExpandConstant('{app}\installed-workspace.txt'),Binding,False) then RaiseException('WORKSPACE_BINDING_WRITE_FAILED');
    Report := ExpandConstant('{tmp}\package-inspection.json');
    Args := '--task inspect-package --report "'+Report+'"';
    if not Exec(ExpandConstant('{app}\DaAV4.exe'),Args,'',SW_HIDE,ewWaitUntilTerminated,Code) or (Code<>0) then
      RaiseException('INSTALLED_PACKAGE_VERIFICATION_FAILED');
    if @WITH_SHORTCUTS@ then begin
      ForceDirectories(ExpandConstant('{userprograms}\大A交易'));
      WriteShortcut(ExpandConstant('{userdesktop}\大A交易.lnk'),ExpandConstant('{app}\DaAV4.exe'),'--workspace "'+Workspace+'"');
      WriteShortcut(ExpandConstant('{userprograms}\大A交易\大A交易.lnk'),ExpandConstant('{app}\DaAV4.exe'),'--workspace "'+Workspace+'"');
      WriteShortcut(ExpandConstant('{userprograms}\大A交易\卸载大A交易.lnk'),ExpandConstant('{uninstallexe}'),'');
    end;
    OldRun := '';
    RegQueryStringValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey,OldRun);
    if WizardIsTaskSelected('autologin') then begin
      if not RegWriteStringValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey,
        '"'+ExpandConstant('{app}\DaAV4.exe')+'" --workspace "'+Workspace+'" --no-browser') then
        RaiseException('LOGIN_SETTING_WRITE_FAILED');
    end else if OldRun<>'' then
      RegDeleteValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey);
  end;
end;
procedure DeinitializeSetup;
begin if Lease<>nil then Lease.Free; end;
function InitializeUninstall: Boolean;
var Binding: TArrayOfString;
begin
  RunKey := '@RUN_KEY@';
  Result := LoadStringsFromFile(ExpandConstant('{app}\installed-workspace.txt'),Binding);
  if Result then Result := GetArrayLength(Binding)=1;
  if Result then Workspace := Binding[0];
  if Result then Result := AcquireWorkspace;
  if not Result and not UninstallSilent then MsgBox('工作区尚被占用。请先从托盘安全退出，再卸载。研究数据将保留。',mbError,MB_OK);
end;
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Current: String;
begin
  if (CurUninstallStep=usUninstall) and @WITH_SHORTCUTS@ then begin
    RemoveOwnedShortcut(ExpandConstant('{userdesktop}\大A交易.lnk'),ExpandConstant('{app}\DaAV4.exe'));
    RemoveOwnedShortcut(ExpandConstant('{userprograms}\大A交易\大A交易.lnk'),ExpandConstant('{app}\DaAV4.exe'));
    RemoveOwnedShortcut(ExpandConstant('{userprograms}\大A交易\卸载大A交易.lnk'),ExpandConstant('{uninstallexe}'));
  end;
  if CurUninstallStep=usUninstall then
    if RegQueryStringValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey,Current) then
      if Pos('"'+ExpandConstant('{app}\DaAV4.exe')+'"',Current)=1 then
        RegDeleteValue(HKCU,'Software\Microsoft\Windows\CurrentVersion\Run',RunKey);
end;
procedure DeinitializeUninstall;
begin if Lease<>nil then Lease.Free; end;
[UninstallDelete]
Type: files; Name: "{app}\installed-workspace.txt"
