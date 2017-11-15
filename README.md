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
