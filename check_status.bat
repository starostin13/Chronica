@echo off
echo Checking bot status on server...
ssh ubuntu@192.168.1.125 "cd /home/ubuntu/chronica && sudo docker-compose ps && echo. && echo === Recent logs === && sudo docker-compose logs --tail=30 chronica-bot"
pause
