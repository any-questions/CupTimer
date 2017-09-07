#!/usr/bin/env python3
import time         # для таймеров
import threading    # для тредов
import gi           # для gui
import serial       # для uart
import simpleaudio as sa  # для аудио
import cairo        # для визуальных эффектов
import cobs         # для декодирования сообщений из uart
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GLib

pattern = '{0:02d}:{1:02d}' # формат вывода строки

eventShortBeep = threading.Event()  #события, которыми будем вызывать проигрывание аудио
eventLongBeep = threading.Event()
eventHighBeep = threading.Event()
eventLowBeep = threading.Event()
eventAirHorn = threading.Event()

class MainWindow(Gtk.Window): # класс основного окна с тремя таймерами
    def __init__(self):
        super(MainWindow,self).__init__() # переопределяем init
        
        self.set_title("Timer") # заголовок окна
        self.set_size_request(800,600)
        #self.fullscreen()   # растягиваем на весь экран
        self.connect("destroy", CloseProgram)    # связываем закрытие окна с функцией заверщеия программы

        self.drawArea = Gtk.DrawingArea()   # создаем drawing area на которой будем рисовать приложение
        self.drawArea.connect("draw",self.expose)   # связываем событие с функцией перерисовки содержимого
        self.add(self.drawArea) # добавляем drawing area в окно приложения
        self.isRunning = True   # флаг что программа работает
        self.alpha = 0    # начальное значение прозрачности (альфа канал, 0 - полностью прозрачен)
        GLib.timeout_add(100, self.on_timer) # таймер по которому каждые 100 мс будем перерисовывать содержимое
        self.prevTime = 5   # значение с которого будем рисовать красивый обратный отсчет
        self.show_all() # отображаем окно

    
    def on_timer(self):
        if not self.isRunning: return False
        
        self.drawArea.queue_draw()    # по таймеру дергаем событие на перерисовку
        return True

    def expose(self,widget,cr):
        self.width = self.get_size()[0] #получаем значения ширины и высоты
        self.height = self.get_size()[1]
        cr.set_source_rgb(0,0,0)    # фон красим в черный
        cr.paint()  # заливаем фон
        # cr.select_font_face("DejaVu Sans",cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD) # выставляем параметры шрифта
        cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)  # выставляем параметры шрифта

        if(mainTimer.finalCountdown == True):   # если тикают последние 5 секунд главного таймера
            self.size = self.size + (self.height/20) # постепенно увеличиваем размер
            if(mainTimer.currentTime[1] == self.prevTime - 1):  # если значение секунды сменилось
                self.prevTime = mainTimer.currentTime[1]    # фиксируем новое значение времени
                self.size = self.height/50 # возвращаем значения прозрачности и размера шрифта
            if(self.size >= self.height/3): self.size = self.height/3
            cr.set_font_size(self.size)   # задаем размер текста
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("0") # смотрим какую ширину/высоту будет занимать указанный текст
            cr.move_to(self.width/2 - textWidth/2, self.height/2+textHeight/4) # перемещаем курсор туда где будем рисовать
            cr.set_source_rgb(1,1,1)    # задаем цвет текста
            cr.show_text(str(mainTimer.currentTime[1]))  # сам текст

        else:   # если не идет обратный отсчет последних 5 секунд - рисуем все три таймера
            self.size = self.height/6   # высота строки = 1/5 высоты экрана
            cr.set_font_size(self.size) # задаем размер строки
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("00:00") # смотрим какую ширину/высоту будет занимать указанный текст

            cr.set_source_rgb(1,0,0)    # цвет текста - красный
            cr.move_to(self.width/4 - textWidth/2, self.height/3)   # перемещаем курсор туда где будем рисовать
            cr.show_text(redTimer.timeString)  # задаем текст

            cr.move_to(self.width*3/4 - textWidth/2, self.height/3) # аналогично предыдущему
            cr.set_source_rgb(0,1,0)    # цвет текста - зеленый
            cr.show_text(greenTimer.timeString)

            cr.set_font_size(self.size*2)   # аналогично, но у главного таймера текст в два раза больше
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("00:00") # смотрим какую ширину/высоту будет занимать указанный текст
            cr.move_to(self.width/2 - textWidth/2, self.height*2/3)
            cr.set_source_rgb(1,1,1)    # цвет текста - белый
            cr.show_text(mainTimer.timeString)
            self.size = self.height/6

        self.infoSize = self.height/60  #вывод сервисной информации от пультов, высота строки совсем маленькая
        cr.set_font_size(self.infoSize)
        (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("P1: None;")
        cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)  # выставляем параметры шрифта
        cr.set_source_rgb(1,1,1)
        for i in range(3):  #в цикле выводим статичную часть надписи
            cr.move_to(self.width/100+textWidth*1.5*i, self.height*59/60)
            cr.show_text("P"+str(i+1)+": ")
        for i in range(3):  #в цикле же выводим информацию от пультов
            cr.move_to(self.width/100+textWidth*1.5*i+textWidth*4/9,self.height*59/60)
            if(pult.status[i] == 'None'):   # разным цветом,в зависимости от информации
                cr.set_source_rgb(1,0,0)    # красным, если пульта нет, или заряд слишком маленький
            elif (pult.status[i] >= 5):
                cr.set_source_rgb(0,1,0)    # зеленым, если все хорошо
            elif (pult.status[i] < 3):
                cr.set_source_rgb(1,0,0)
            else:
                cr.set_source_rgb(1,1,0)    # желтым если начало садиится
            cr.show_text(str(pult.status[i]))

class TimerClass(threading.Thread): # класс для таймера
    global eventHighBeep,eventAirHorn,eventLowBeep,eventLongBeep,eventShortBeep
    def __init__(self, min, sec, timer):    # при инициализации передаем минуты и секунды, а так же какой таймер будем менять
        self.timer = timer  # переменная куда записывается какой таймер меняем
        self.isRunning = False  # флаг работы таймера
        self.isPaused = False   # флаг паузы таймера
        self.finalCountdown = False # флаг того, что идет отсчет последних 5 секунд
        self.currentTime = [min, sec]   # массив с текущим временем таймера
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        threading.Thread.__init__(self,daemon=True)  # наследование функций треда

    def update(self):   # функция обновляющая текст таймера
        while(self.isRunning):  # работает только когда таймер запущен
            if(self.isPaused == False): # и не на паузе
                self.currentTime[1] -= 1    # вычитаем 1 секунду
                if(self.currentTime[1] < 0):    # если секунды кончились
                    self.currentTime[1] = 59    # переписываем секунды
                    self.currentTime[0] -= 1    # вычитаем минуту

                if(self.currentTime[1] == 0 and self.currentTime[0] == 0):  # если дотикали до 0 - останавливаем таймер
                    self.isRunning = False
                    if(self.timer == 'main'):   # если остановился главный таймер
                        eventAirHorn.set()  # пищим одним тоном
                    else:                   # если любой другой таймер
                        eventHighBeep.set() # пищим другим тоном
                else:
                    if(self.currentTime[1] <= 5 and self.currentTime[0] == 0):  # если осталось тикать 5 секунд
                        self.finalCountdown = True  # поднимаем флаг, чтобы окно перерисовывалось по другому
                        if(self.timer == 'main'):   # если отсчет у главного таймера
                            eventLowBeep.set()      # пищим одним тоном
                        else:                       # если у других таймеров
                            eventShortBeep.set()    # другим тоном


                self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])   # записываем время в паттерн
                time.sleep(1)   #останавливаем тред на секунду

    def __del__(self):  # деструктор класса - останавливает таймер
        self.isRunning = False

    def run(self):  # функция запускающая таймер
        self.isRunning = True   # поднимаем флаг чтобы таймер работал
        if(self.timer == 'main'):
            eventAirHorn.set()
        self.update()   # запускаем функцию обновления таймера

    def setTime(self,min,sec):  # функция установки начального времени таймера
        self.isRunning = False  #приостанавливаем таймер на всякий случай
        self.finalCountdown = False
        self.currentTime = [min,sec]    # записываем новое текущее время

    def pause(self):    # функция постановки таймера на паузу
        self.isPaused = True

    def resume(self):   # снятие с паузы
        self.isPaused = False

class PlayMusic(threading.Thread):  # класс для воспроизведения мелодий
    def __init__(self):
        self.short_beep = sa.WaveObject.from_wave_file("sounds/short_beep.wav")
        self.long_beep = sa.WaveObject.from_wave_file("sounds/long_beep.wav")
        self.low_beep = sa.WaveObject.from_wave_file("sounds/low_beep.wav")
        self.high_beep = sa.WaveObject.from_wave_file("sounds/high_beep.wav")
        self.horn = sa.WaveObject.from_wave_file("sounds/airhorn.wav")
        threading.Thread.__init__(self) # наследование функций треда

    def __del__(self):  # деструктор останавливает флаг
        self.isRunning = False

    def run(self):  # запуск обработчика событий
        self.isRunning = True
        self.Handler()

    def Handler(self):  # обработчик событий
        while(self.isRunning == True):  # работает пока поднят флаг
            if(eventLongBeep.isSet()):  # проверяется установлено ли событие, длинный писк
                eventLongBeep.clear()   # если да - сбрасываем событие
                self.long_beep.play()   # пищим нужным тоном
            elif (eventShortBeep.isSet()):  # аналогично, короткий писк
                eventShortBeep.clear()
                self.short_beep.play()
            elif (eventHighBeep.isSet()):   # высокий писк
                eventHighBeep.clear()
                self.high_beep.play()
            elif (eventLowBeep.isSet()):    # низкий писк
                eventLowBeep.clear()
                self.low_beep.play()
            elif (eventAirHorn.isSet()):    # стартовый горн
                eventAirHorn.clear()
                self.horn.play()

def CloseProgram(w): # при закрытии программы останавливаем таймеры и закрываем окно
    print("Stopping timers...")
    mainTimer.isRunning = False
    redTimer.isRunning = False
    greenTimer.isRunning = False
    print("Stopping music...")
    player.isRunning = False
    eventShortBeep.clear()
    eventLongBeep.clear()
    eventHighBeep.clear()
    eventLowBeep.clear()
    eventAirHorn.clear()
    print("Closing pult...")
    pult.close()
    print("Closing window...")
    Gtk.main_quit()
    print("Program closed.")


class GtkRunner(threading.Thread):
    def __init__(self):   #запуск гтк в отдельном треде
        threading.Thread.__init__(self)

    def run(self):
        Gtk.main()

class PultHandler(threading.Thread):    # класс обработки сообщений с пульта
    def __init__(self):
        try:
            print("Opening UART port...")
            self.port = serial.Serial(  #открываем порт
                                        port='/dev/ttyUSB0',    # параметры порта (USB0 для пк, AMA0 для родного uart малины)
                                        baudrate=9600,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS)  # открытие порта
        except serial.SerialException:
            print("ERROR: failed to open UART")
        self.status = [5.5,4.3,2.1]    #список содержащий статус для каждого из пультов (None - пульт не найден, напряжение - пульт на месте)
        self.receivedMessage = ''   #полученное сообщение
        threading.Thread.__init__(self, daemon=True)  # наследование функций треда

    def __del__(self):
        print("Closing port...")
        self.isRunning = False
        try:
            self.port.close()   # закрытие порта
        except AttributeError:  # сообщение об ошибке, если не вышло
            print("Closing ERROR, no port was created.")

    def close(self):
        print("Closing port...")
        self.isRunning = False
        try:
            self.port.close()   # закрытие порта
        except AttributeError:  # сообщение об ошибке, если не вышло
            print("Closing ERROR, no port was created.")

    def run(self):
        print("Reading port...")
        try:
            self.isRunning = True
            self.ReadPort() # получение сообщений из порта
        except:
            print("Reading ERROR, no port was created.")    #сообщение об ошибке, если не вышло


    def ReadPort(self): # функция читающая порт
        while(self.isRunning == True):
            if(self.port.isOpen):   # проверяем открыт ли uart
                self.line = self.port.read()    # поочереди выхватываем байты посылки
                print(hex(ord(self.line)))
                if(self.line.decode("utf-8") == 'q'):
                    print("Goodbye")
                    self.port.close()
                    CloseProgram(0)
            else:
                print("Port is not opened")
        print("Reading stopped")



MainWindow()  # создаем объект класса главного окна
gtkRunner = GtkRunner()

# создаем таймеры, минуты, секунды, какой таймер
redTimer = TimerClass(3, 0, 'red')  # тут красный
greenTimer = TimerClass(3, 0, 'green')  # тут зеленый
mainTimer = TimerClass(0, 10, 'main')   # тут главный

player = PlayMusic()    # создаем объект класса проигрывания музыки

pult = PultHandler()    # создаем обработчик пульта

gtkRunner.start()   # запускаем гтк
mainTimer.start()   #запускаем таймеры
player.start()  # запускаем проигрыватель музыки
redTimer.start()
greenTimer.start()
pult.start()    #запускаем обработчик пульта

gtkRunner.join()    # цепляем треды к основному потоку
mainTimer.join()
redTimer.join()
greenTimer.join()