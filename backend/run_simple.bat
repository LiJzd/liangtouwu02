cd /d "c:\Users\lost\Desktop\两头乌\两头乌后端"
call mvn install -DskipTests -B
if %ERRORLEVEL% NEQ 0 (
  echo Build Failed!
  exit /b 1
)
cd liangtouwu-app
call mvn spring-boot:run -B
