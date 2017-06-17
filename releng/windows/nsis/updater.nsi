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

!addincludedir "${KNOSSOS_ROOT}releng\windows\support\NSIS"
!addplugindir "${KNOSSOS_ROOT}releng\windows\support\NSIS"

!include MUI2.nsh
!include nsProcess.nsh

Name Knossos
InstallDir "$PROGRAMFILES\Knossos"
InstallDirRegKey HKLM "Software\Knossos" "Install Dir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
OutFile ${KNOSSOS_ROOT}releng\windows\dist\update-${KNOSSOS_VERSION}.exe

!define MUI_ICON ${KNOSSOS_ROOT}knossos\data\hlp.ico
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

    # Remove all obsolete files
    Delete "$INSTDIR\hlp.png"
    Delete "$INSTDIR\SDL.dll"
    Delete "$INSTDIR\version"
    Delete "$INSTDIR\*.dll"
    Delete "$INSTDIR\*.pyd"

    SetOverwrite on
    File /r ${KNOSSOS_ROOT}releng\windows\dist\Knossos\*

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Knossos" "DisplayVersion" "${KNOSSOS_VERSION}"

    DetailPrint "Launching Knossos..."
    ExecShell "open" '"$INSTDIR\Knossos.exe"' '--finish-update "$EXEPATH"'
    SetAutoClose true
SectionEnd
