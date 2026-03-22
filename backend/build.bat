@echo off
chcp 65001
echo Start Building...
mvn clean install -DskipTests -B
echo Build Finished.
