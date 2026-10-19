: << 'CMDBLOCK'
@echo off
setlocal
if "%~1"=="" (
  1>&2 echo run-hook.cmd: missing hook script name
  exit /b 1
)
set "HOOK_DIR=%~dp0"
set "HOOK_BASH="
set "HOOK_GIT="
rem Git Bash from its install folders, or beside the git.exe on PATH. Never a bare "bash",
rem nor the PATH modifier of a for variable: both try the current folder first, where anyone
rem could have put a bash.exe. Each PATH folder is checked by name instead. No labels: goto
rem can miss a label in a file with LF line breaks.
if defined ProgramFiles if exist "%ProgramFiles%\Git\bin\bash.exe" set "HOOK_BASH=%ProgramFiles%\Git\bin\bash.exe"
if not defined HOOK_BASH if defined ProgramFiles(x86) if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "HOOK_BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined HOOK_BASH if defined LOCALAPPDATA if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "HOOK_BASH=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not defined HOOK_BASH if defined PATH for %%P in ("%PATH:;=" "%") do if not defined HOOK_GIT if not "%%~P"=="" if exist "%%~P\git.exe" set "HOOK_GIT=%%~P\git.exe"
if defined HOOK_GIT for %%D in ("%HOOK_GIT%\..\..") do if exist "%%~fD\bin\bash.exe" set "HOOK_BASH=%%~fD\bin\bash.exe"
if not defined HOOK_BASH if defined PATH for %%P in ("%PATH:;=" "%") do if not defined HOOK_BASH if not "%%~P"=="" if exist "%%~P\bash.exe" set "HOOK_BASH=%%~P\bash.exe"
rem Without bash, exit 1 as session-start does when it cannot add the bootstrap: the client
rem reports a hook error that blocks nothing, and the session goes on.
if not defined HOOK_BASH (
  1>&2 echo nobrainer-tech-flow: the session hook needs Git Bash, which was not found. Install Git for Windows from https://git-scm.com/download/win. This session continues without the Flow bootstrap.
  exit /b 1
)
"%HOOK_BASH%" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
rem On a line of its own: inside a parenthesised block ERRORLEVEL is read before bash runs.
exit /b %ERRORLEVEL%
CMDBLOCK

set -e
script_dir="$(cd "$(dirname "$0")" && pwd)"
script_name="${1:?missing hook script name}"
shift
exec bash "${script_dir}/${script_name}" "$@"
