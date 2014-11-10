!include MUI2.nsh

Name Knossos
InstallDir "$PROGRAMFILES\Knossos"
InstallDirRegKey HKLM "Software\Knossos" "Install Dir"
RequestExecutionLevel admin  # We need admin for the "fso:// Support" section
SetCompressor lzma
OutFile dist\installer.exe


!define MUI_ICON ${KNOSSOS_ROOT}knossos\data\hlp.ico

Var StartMenuFolder
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\Knossos"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

!define MUI_FINISHPAGE_RUN "$INSTDIR\Knossos.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Knossos"
!define MUI_FINISHPAGE_CANCEL_ENABLED
!define MUI_FINISHPAGE_NOREBOOTSUPPORT

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ${KNOSSOS_ROOT}LICENSE
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU "Application" $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"


Section
    SetOutPath "$INSTDIR"
    WriteRegStr HKLM "Software\Knossos" "Install Dir" "$INSTDIR"

    File /r /x *.h dist\Knossos\*

    WriteUninstaller "$INSTDIR\uninstall.exe"

    # http://nsis.sourceforge.net/Add_uninstall_information_to_Add/Remove_Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayName" "Knossos"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayIcon" "$\"$INSTDIR\Knossos.exe$\",0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "NoRepair" 1

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application

        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Knossos.lnk" "$INSTDIR\Knossos.exe"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Launch FSO.lnk" "$INSTDIR\Knossos.exe" "fso://run"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section "Desktop icon"
    CreateShortcut "$DESKTOP\Knossos.lnk" "$INSTDIR\Knossos.exe"
SectionEnd

Section "fso:// Support"
    ExecWait '"$INSTDIR\Knossos.exe" --install-scheme --silent'
SectionEnd

Section "Uninstall"
    # Should we also uninstall the fso:// registry keys?
    
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder

    Delete "$SMPROGRAMS\$StartMenuFolder\Knossos.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Launch FSO.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"

    Delete "$DESKTOP\Knossos.lnk"

    RMDir /r "$INSTDIR"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos"
    DeleteRegKey HKLM "Software\Knossos"
SectionEnd
