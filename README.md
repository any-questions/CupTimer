# CupTimer
Проект таймера для кубка ртк для Raspberry pi

**Установка simpleaudio (для проигрывания звуков):**  
```$ sudo pip3 install simpleaudio```  
**Установка cobs (для декодирования сообщений):**  
```$ sudo pip3 install cobs```  
**Установка RPi.GPIO (для работы с gpio на raspberry pi)**  
Для ubuntu:  
```$ sudo pip3 install RPi.GPIO```  
Для raspbian также, или:  
```$ sudo apt install python3-rpi.gpio```  
**Установка cairo (для отрисовки графики):**  
```$ sudo apt install python3-cairo python3-gi-cairo```  
**Установка шрифтов:**  
1. Скопировать новый шрифт в формате *.ttf или *.otf в папку /usr/local/share/fonts  
2. Раздать ему права ```$ sudo chmod 644 *имя файла*```  


**Добавление программы с GUI в автозапуск**  
(Подробнее http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/auto-running-programs-gui)  
1. ```$ sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart```
2. Добавить в конец строчку с путем к файлу, например:  
```@/home/pi/CupTimer/TimerCup.py```  
**Чтобы скрыть предупреждение ssh, о том что пароль стоит стандартный**  
Чтобы отключить warning в терминале, когда подключаешься по ssh:  
- удалить файл /etc/profile.d/sshpwd.sh  
Чтобы отключить warning на рабочем столе при загрузке  
- Удалить файл /home/pi/.config/lxsession/LXDE-pi/sshpwd.sh  
файлы можно не удалять, а закоментировать часть отвечающую за вывод)  
**Чтобы отключить выключение экрана с течением времени:**  
1. ```$ sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart```  
2. Добавить строчки  
```
@xset s noblank  
@xset s off  
@xset -dpms
```
