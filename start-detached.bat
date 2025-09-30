@echo off
echo Starting EasyTips in detached mode...
cd /d D:\Projects\EasyTips
docker-compose down
docker-compose up --build -d
echo Services are starting in the background...
docker-compose ps
pause