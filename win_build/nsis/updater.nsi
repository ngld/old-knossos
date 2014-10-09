!include MUI2.nsh
!include nsProcess.nsh

Name Knossos
InstallDir "$PROGRAMFILES\Knossos"
InstallDirRegKey HKLM "Software\Knossos" "Install Dir"
RequestExecutionLevel admin  # We need admin for the "fso:// Support" section
SetCompressor /SOLID lzma
OutFile updater.exe

!define MUI_ICON ${KNOSSOS_ROOT}hlp.ico

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"


Section
    SetOutPath "$INSTDIR"
    WriteRegStr HKLM "Software\Knossos" "Install Dir" "$INSTDIR"

    DetailPrint "Waiting for Knossos to quit..."

    ${nsProcess::FindProcess} "Knossos.exe" $R0
    ${While} $R0 = 0
        Sleep 300
        ${nsProcess::FindProcess} "Knossos.exe" $R0
    ${EndWhile}

    ${nsProcess::Unload}

    ${If} $R0 != 603
        DetailPrint "Um... we got an error here! ($R0)"
    ${EndIf}

    DetailPrint "Starting Update..." 
    
    File /r /x *.h dist\Knossos\*

    DetailPrint "Launching Knossos..."
    Exec '"$INSTDIR\Knossos.exe"'
    SetAutoClose true
SectionEnd
