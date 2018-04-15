## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

!include MUI2.nsh

Name Knossos
Caption "Knossos ${KNOSSOS_VERSION} Setup"
RequestExecutionLevel admin  # We need admin for the "fso:// Support" section
InstallDir "$PROGRAMFILES\Knossos"
InstallDirRegKey HKLM "Software\Knossos" "Install Dir"
SetCompressor /SOLID lzma
OutFile ${KNOSSOS_ROOT}releng\windows\dist\Knossos-${KNOSSOS_VERSION}.exe


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

LangString DESC_desk_icon ${LANG_ENGLISH} "Creates a shortcut icon on your desktop."
LangString DESC_fso_support ${LANG_ENGLISH} "Allows you to open fso:// links with Knossos."
LangString DESC_un_settings ${LANG_ENGLISH} "Removes all settings and cached files which were created by Knossos."

Section
    SetOutPath "$INSTDIR"
    WriteRegStr HKLM "Software\Knossos" "Install Dir" "$INSTDIR"

    File /r ${KNOSSOS_ROOT}releng\windows\dist\Knossos\*

    WriteUninstaller "$INSTDIR\uninstall.exe"

    # http://nsis.sourceforge.net/Docs/AppendixD.html#useful_add_uninst_infos
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayName" "Knossos"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayIcon" "$\"$INSTDIR\Knossos.exe$\",0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "Publisher" "ngld"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "InstallSource" "https://fsnebula.org/knossos/"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "URLInfoAbout" "https://fsnebula.org/knossos/"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayVersion" "${KNOSSOS_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "NoRepair" 1

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        SetShellVarContext all  # Install for all users

        CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Knossos.lnk" "$INSTDIR\Knossos.exe"
        CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section "Desktop icon" desk_icon
    SetShellVarContext all  # Install for all users
    CreateShortcut "$DESKTOP\Knossos.lnk" "$INSTDIR\Knossos.exe"
SectionEnd

Section "fso:// Support" fso_support
    WriteRegStr HKCR "fso" "Default" "URL:Knossos protocol"
    WriteRegStr HKCR "fso" "URL Protocol" ""
    WriteRegStr HKCR "fso\DefaultIcon" "Default" "$\"$INSTDIR\data\hlp.ico$\",1"
    WriteRegStr HKCR "fso\shell\open\command" "Default" "$\"$INSTDIR\Knossos.exe$\" $\"%1$\""
SectionEnd

Section "Uninstall"
    !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
    SetShellVarContext all  # Install for all users

    Delete "$SMPROGRAMS\$StartMenuFolder\Knossos.lnk"
    Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
    RMDir "$SMPROGRAMS\$StartMenuFolder"

    Delete "$DESKTOP\Knossos.lnk"

    RMDir /r "$INSTDIR"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos"
    DeleteRegKey HKLM "Software\Knossos"

    # Only delete the fso:// entry if it was created by us.
    ReadRegStr $0 HKCR "fso" "Default"
    ${If} $0 == "URL:Knossos protocol"
        DeleteRegKey HKCR "fso"
    ${EndIf}
SectionEnd

Section "un.Remove Settings" un_settings
    RMDir /r "$APPDATA\knossos"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${desk_icon} $(DESC_desk_icon)
    !insertmacro MUI_DESCRIPTION_TEXT ${fso_support} $(DESC_fso_support)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

!insertmacro MUI_UNFUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${un_settings} $(DESC_un_settings)
!insertmacro MUI_UNFUNCTION_DESCRIPTION_END
