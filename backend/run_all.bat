@echo off
echo [*] Starting Comprehensive Backend Build...
cd /d "c:\Users\lost\Desktop\两头乌\两头乌后端"
echo [+] Installing Common...
cd liangtouwu-common
call mvn install -DskipTests -B
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
cd ..
echo [+] Installing Domain...
cd liangtouwu-domain
call mvn install -DskipTests -B
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
cd ..
echo [+] Installing Business...
cd liangtouwu-business
call mvn install -DskipTests -B
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
cd ..
echo [+] Starting Application...
cd liangtouwu-app
call mvn spring-boot:run -B
