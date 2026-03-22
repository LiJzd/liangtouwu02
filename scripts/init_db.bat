@echo off
set MYSQL_PWD=1234
mysql -u root -e "CREATE DATABASE IF NOT EXISTS liangtowwu;"
mysql -u root liangtowwu < c:\Users\lost\Desktop\两头乌\init_mysql.sql
if %ERRORLEVEL% EQU 0 (
    echo Database initialized successfully.
) else (
    echo Database initialization failed.
)
