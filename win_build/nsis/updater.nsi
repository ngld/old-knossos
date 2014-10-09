!include MUI2.nsh
!include nsProcess.nsh

Name Knossos
InstallDir "$PROGRAMFILES\Knossos"
InstallDirRegKey HKLM "Software\Knossos" "Install Dir"
RequestExecutionLevel admin  # We need admin for the "fso:// Support" section
SetCompressor /SOLID lzma
OutFile updater.exe

!define MUI_ICON ${KNOSSOS_ROOT}hlp.ico
!define MUI_INSTFILESPAGE_HEADER_SUBTEXT

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

LangString MUI_TEXT_INSTALLING_SUBTITLE 0 "Please wait while $(^NameDA) is being updated."

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
    ExecShell "open" '"$INSTDIR\Knossos.exe"' '--finish-update "$EXEPATH"'
    SetAutoClose true
SectionEnd
