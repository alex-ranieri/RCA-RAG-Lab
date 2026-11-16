#ifndef PayloadDir
  #error Informe /DPayloadDir=caminho para o pacote preparado
#endif

[Setup]
AppId={{E9C20D44-10D3-466B-A122-D026CE149634}
AppName=RCA-RAG Lab
AppVersion=0.3.3.2026.11.16
AppPublisher=RCA
DefaultDirName={localappdata}\Programs\RCA-RAG Lab
DefaultGroupName=RCA-RAG Lab
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir=..\distribuicao
OutputBaseFilename=Instalar_RCA_RAG_2026.11.16_v4_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=RCA-RAG Lab
UninstallDisplayIcon={app}\runtime\python.exe
InfoBeforeFile={#PayloadDir}\LEIA-ME.txt
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\RCA-RAG Lab\Abrir RCA-RAG Lab"; Filename: "{app}\runtime\python.exe"; Parameters: """{app}\app\packaging_rag\installed_main.py"""; WorkingDir: "{app}"
Name: "{userprograms}\RCA-RAG Lab\Diagnosticar RCA-RAG Lab"; Filename: "{app}\Diagnosticar_RAG.cmd"; WorkingDir: "{app}"
Name: "{userprograms}\RCA-RAG Lab\Instruções"; Filename: "{app}\LEIA-ME.txt"
Name: "{userprograms}\RCA-RAG Lab\Dados e documentos"; Filename: "{localappdata}\RCA-RAG Lab"
Name: "{userdesktop}\RCA-RAG Lab"; Filename: "{app}\runtime\python.exe"; Parameters: """{app}\app\packaging_rag\installed_main.py"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\python.exe"; Parameters: """{app}\app\packaging_rag\installed_main.py"""; Description: "Abrir RCA-RAG Lab"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if not Exec(ExpandConstant('{app}\runtime\python.exe'),
      '"' + ExpandConstant('{app}\app\packaging_rag\installed_main.py') + '" --verificar --no-browser',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Não foi possível iniciar o Python incluído. Verifique as políticas de execução deste computador.');
    if ResultCode <> 0 then
      RaiseException('A verificação da ferramenta falhou. Consulte %LOCALAPPDATA%\RCA-RAG Lab\falha_inicializacao.log.');
  end;
end;
