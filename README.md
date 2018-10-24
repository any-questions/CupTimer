# CupTimer
Проект таймера на кубок РТК для Raspberry Pi.  
Подключение кнопок:  
- GPIO4 - Start  
- GPIO3 - Pause  
- GPIO2 - Reset  
- GPIO17 - Select  
- GPIO23 - Shutdown  
- GPIO27 - Канал энкодера А  
- GPIO22 - Канал энкодера B  

### Обязательные модули  
**Установка RPi.GPIO (для работы с gpio на raspberry pi)**  
Для ubuntu:  
`sudo pip3 install RPi.GPIO`  
Для raspbian также, или:  
`sudo apt install python3-rpi.gpio`  

**Установка cairo (для отрисовки графики):**  
`sudo apt install python3-cairo python3-gi-cairo`

**Установка simpleaudio (для проигрывания звуков):**  
1. `sudo apt install libasound2-dev`
2. `sudo pip3 install simpleaudio`  

**Установка pynput (для того чтобы слушать клавиатуру)**  
`sudo pip3 install pynput` 

**Установка шрифтов:**  
1. Скопировать новый шрифт в формате *.ttf или *.otf в папку `/usr/local/share/fonts`  
2. Раздать ему права `$ sudo chmod 644 *имя файла*`  


**Добавление программы с GUI в автозапуск** ([подробнее](http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/auto-running-programs-gui))  
1. `sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart`
2. Добавить в конец строчку с путем к файлу, например:  
`@/home/pi/CupTimer/TimerCup.py`  

**Чтобы скрыть предупреждение ssh, о том что пароль стоит стандартный**  
Чтобы отключить warning в терминале, когда подключаешься по ssh:  
- удалить файл `/etc/profile.d/sshpwd.sh`  
Чтобы отключить warning на рабочем столе при загрузке  
- Удалить файл `/home/pi/.config/lxsession/LXDE-pi/sshpwd.sh`  
(возможно он лежит тут: `/etc/xdg/lxsession/LXDE-pi/sshpwd.sh`)

Файлы можно не удалять, а закоментировать часть отвечающую за вывод)  

**Чтобы отключить выключение экрана с течением времени:**  
1. `sudo nano /home/pi/.config/lxsession/LXDE-pi/autostart`  
2. Добавить строчки  
`@xset s noblank`  
`@xset s off`  
`@xset -dpms`  

**Чтобы настроить HDMI выход** ([подробнее](http://wikihandbk.com/wiki/Raspberry_Pi:%D0%9D%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0/config.txt#HDMI_DRIVE))  
1. `sudo nano /boot/config.txt`  
2. Раскомментировать (или дописать) следующие строчки:  
`hdmi_force_hotplug=1` - видео будет отправляться в HDMI, даже если монитор еще не подключен  
`hdmi_drive=2` - звук также отправляется в HDMI  
`hdmi_group=1` - подключаемся к телевизору (0 - автоопределение, 2 - к монитору)  
`hdmi_mode=4` - 720p 60 fps  

**Чтобы отключить черную рамку по краям экрана**  
1. `sudo nano /boot/config.txt`  
2. Раскомментировать (или дописать) следующие строчки:  
`disable_overscan=1` - overscan определяет черную рамку по краям экрана (можно включить и настроить по пикселям с каждой из четырех сторон)  
