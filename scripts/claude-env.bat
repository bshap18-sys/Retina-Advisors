@echo off
REM Loads .env into the environment, then launches Claude Code.
REM
REM Usage from project root:
REM   scripts\claude-env.bat           start a claude session
REM   scripts\claude-env.bat <args>    pass args through to claude
REM
REM .env format is one KEY=VALUE per line. Lines starting with # are
REM treated as comments and skipped. .env is gitignored.
REM
REM Bash equivalent: source .env && claude

if not exist .env (
  echo ERROR: no .env file found at %CD%\.env
  echo Copy .env.example to .env and fill in your API keys.
  exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (`findstr /v /b /c:"#" .env`) do (
  if not "%%A"=="" set "%%A=%%B"
)

claude %*
