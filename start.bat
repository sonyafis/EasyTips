@echo off
echo Starting EasyTips with .env configuration...
cd /d D:\Projects\EasyTips
docker-compose down
docker-compose up --build
pause