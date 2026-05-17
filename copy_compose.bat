@echo off
echo Copying docker-compose.yml to server...
scp docker-compose.yml ubuntu@192.168.1.125:/home/ubuntu/chronica/

echo.
echo Checking directory contents on server...
ssh ubuntu@192.168.1.125 "ls -la /home/ubuntu/chronica/"

pause
