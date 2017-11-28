# CupTimer
Проект таймера для кубка ртк для Raspberry pi

Установка simpleaudio (для проигрывания звуков):

$ sudo pip3 install simpleaudio

Установка cobs (для декодирования сообщений):

$ sudo pip3 install cobs

Установка RPi.GPIO (для работы с gpio на raspberry pi)
Для ubuntu:

$ sudo pip3 install RPi.GPIO
Для raspbian также, или:

$ sudo apt install python3-rpi.gpio

Установка cairo (для отрисовки графики):

$ sudo apt install python3-cairo python3-gi-cairo


Установка шрифтов:
Скопировать новый шрифт в формате *.ttf или *.otf в папку /usr/local/share/fonts,
раздать ему права 

$ sudo chmod 644 *имя файла*

Добавление программы в автозапуск (Подробнее http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/auto-running-programs-gui)

$ sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart

Добавить в конец строчку с путем к файлу, например

@/home/pi/CupTimer/TimerCup.py

Чтобы скрыть предупреждение ssh, о том что пароль стоит стандартный,

удалить файл /etc/profile.d/sshpwd.sh - чтобы warning не появлялся в терминале, когда логинишься

удалить файл /home/pi/.config/lxsession/LXDE-pi/sshpwd.sh - чтобы не появлялся warning на рабочем столе при загрузке

(можно не удалять, а закоментировать часть отвечающую за вывод)

Чтобы отключить выключение экрана с течением времени:

$ sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart

Добавить строчки

@xset s noblank

@xset s off

@xset -dpms 
