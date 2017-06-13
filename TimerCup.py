#!/usr/bin/env python3
import time         # для таймеров
import threading    # для тредов
import gi           # для gui
import serial       # для uart
import simpleaudio as sa  # для аудио
import cairo        # для визуальных эффектов
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
        #self.set_size_request(800,600)
        self.fullscreen()   # растягиваем на весь экран
        self.connect("destroy", CloseProgram)    # связываем закрытие окна с функцией заверщеия программы

        self.drawArea = Gtk.DrawingArea()   # создаем drawing area на которой будем рисовать приложение
        self.drawArea.connect("draw",self.expose)   # связываем событие с функцией перерисовки содержимого
        self.add(self.drawArea) # добавляем drawing area в окно приложения
        self.isRunning = True   # флаг что программа работает
        self.alpha = 0    # начальное значение прозрачности (альфа канал, 0 - полностью прозрачен)
        GLib.timeout_add(20, self.on_timer) # таймер по которому каждые 20 мс будем перерисовывать содержимое
        self.prevTime = 5
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
        cr.select_font_face("Ds-Digital",cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL) # выставляем параметры шрифта

        if(mainTimer.finalCountdown == True):   # если тикают последние 5 секунд главного таймера
            self.alpha += 0.05  # постепенно увеличиваем непрозрачность чтобы числа постепенно появлялись
            self.size = self.size + 20 # постепенно увеличиваем размер
            if(mainTimer.currentTime[1] == self.prevTime - 1):  # если значение секунды сменилось
                self.prevTime = mainTimer.currentTime[1]    # фиксируем новое значение времени
                self.size = self.height/100 # возвращаем значения прозрачности и размера шрифта
                self.alpha = 0.0            # чтобы все менялось красиво и циклично
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("0") # смотрим какую ширину/высоту будет занимать указанный текст
            if(self.size >= self.height/2): self.size = self.height/2
            cr.set_font_size(self.size)   # задаем размер текста
            cr.move_to(self.width/2 - textWidth/2, self.height/2) # перемещаем курсор туда где будем рисовать
            cr.set_source_rgb(1,1,1)    # задаем цвет текста
            cr.text_path(str(mainTimer.currentTime[1]))  # сам текст
            cr.clip()   # фиксируем зону где рисуем
            cr.fill()   # заливаем текст
            cr.paint_with_alpha(self.alpha) # рисуем с указанным значением прозрачности

        else:   # если не идет обратный отсчет последних 5 секунд - рисуем все три таймера
            self.size = self.height/5   # высота строки = 1/5 высоты экрана
            cr.set_font_size(self.size) # задаем размер строки
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("00:00") # смотрим какую ширину/высоту будет занимать указанный текст

            cr.set_source_rgb(1,0,0)    # цвет текста - красный
            cr.move_to(self.width/4 - textWidth/2, self.height/3)   # перемещаем курсор туда где будем рисовать
            cr.text_path(redTimer.timeString)   # задаем текст
            cr.fill()   # рисуем
        
            cr.move_to(self.width*3/4 - textWidth/2, self.height/3) # аналогично предыдущему
            cr.set_source_rgb(0,1,0)
            cr.text_path(greenTimer.timeString)
            cr.fill()
 
            cr.set_font_size(self.size*2)   # аналогично, но у главного таймера текст в два раза больше
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("00:00") # смотрим какую ширину/высоту будет занимать указанный текст
            cr.move_to(self.width/2 - textWidth/2, self.height*2/3)
            cr.set_source_rgb(1,1,1)
            cr.text_path(mainTimer.timeString)
            cr.clip()
            cr.fill()
            cr.paint()  #выводим все на экран
            self.size = self.height/100

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
        while(self.isRunning):  #работает только когда таймер запущен
            if(self.isPaused == False):
                self.currentTime[1] -= 1    # вычитаем 1 секунду
                if(self.currentTime[1] < 0):    # если секунды кончились
                    self.currentTime[1] = 59    # переписываем секунды
                    self.currentTime[0] -= 1    # вычитаем минуту
                if(self.currentTime[1] <= 5 and self.currentTime[0] == 0):
                    self.finalCountdown = True
                if(self.currentTime[1] == 0 and self.currentTime[0] == 0):  # если дотикали до 0 - останавливаем таймер
                    self.isRunning = False
                    if(self.timer == 'main'):   # если остановился главный таймер
                        eventLowBeep.set()  # пищим другим тоном

                self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])   # записываем время в паттерн
                if(self.timer=='main'): # в зависимости от того, с каким таймером работаем (тут главный таймер)
                    eventHighBeep.set() # пищание одним тоном (дебагово)
                #TODO: дописать вызов аудио
                #print(self.timer + " " + self.timeString)   # дебаговый вывод
                
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
        timeString = pattern.format(self.currentTime[0], self.currentTime[1]) # обновляем текст на экране
        if (self.timer == 'main'):
            win.mainTimerText.set_markup(timeString)
        elif (self.timer == 'red'):
            win.redTimerText.set_markup(timeString)
        elif (self.timer == 'green'):
            win.greenTimerText.set_markup(timeString)

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
                # print("Long Beep ") # пищим нужным тоном
            elif (eventShortBeep.isSet()):  # аналогично, короткий писк
                eventShortBeep.clear()
                # print("Short Beep ")
            elif (eventHighBeep.isSet()):   # высокий писк
                eventHighBeep.clear()
                # print("High Beep ")
            elif (eventLowBeep.isSet()):    # низкий писк
                eventLowBeep.clear()
                # print("Low Beep ")
            elif (eventAirHorn.isSet()):    # стартовый горн
                eventAirHorn.clear()
                # print("Air Horn ")

def CloseProgram(w): # при закрытии программы останавливаем таймеры и закрываем окно
    mainTimer.isRunning = False
    redTimer.isRunning = False
    greenTimer.isRunning = False
    player.isRunning = False
    eventShortBeep.clear()
    eventLongBeep.clear()
    eventHighBeep.clear()
    eventLowBeep.clear()
    eventAirHorn.clear()
    pult.close()
    Gtk.main_quit()
    print("WINDOW CLOSED")


class GtkRunner(threading.Thread):
    def __init__(self):   #запуск гтк в отдельном треде
        threading.Thread.__init__(self)
    def run(self):
        Gtk.main()

class PultHandler(threading.Thread):    # класс обработки сообщений с пульта
    def __init__(self):
        try:
            self.port = serial.Serial(  #открываем порт
                                        port='/dev/ttyAMA0',    # параметры порта (USB0 для пк, AMA0 для родного uart малины)
                                        baudrate=9600,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS)  # открытие порта
            threading.Thread.__init__(self,daemon=True)  # наследование функций треда
        except serial.SerialException:
            print("Error opening port, please try again.")
        
    def __del__(self):
        print("closing port")
        self.port.close()   # закрытие портая 
    def close(self):
        self.port.close()
        print("port closed")
    def run(self):
        print("Reading port")
        self.ReadPort()
    def ReadPort(self): # функция читающая порт
        while(self.port.isOpen):
            self.line = self.port.readline()    # получаем строку
            print(self.line)    # дебагово выводим ее на экран
            #self.port.write(self.line)  # дебагово отправляем ее обратно в порт
            if(self.line.decode("utf-8") == 'q\n'):
                print("Goodbye")
                CloseProgram(0)

player = PlayMusic()    # создаем объект класса проигрывания музыки

# создаем таймеры, минуты, секунды, какой таймер
redTimer = TimerClass(2, 0, 'red')  # тут красный
greenTimer = TimerClass(2, 0, 'green')  # тут зеленый
mainTimer = TimerClass(0, 10, 'main')   # тут главный
MainWindow()  # создаем объект класса главного окна
gtkRunner = GtkRunner()

pult = PultHandler()    # создаем обработчик пульта

player.start()  # запускаем проигрыватель музыки
mainTimer.start()   #запускаем таймеры
redTimer.start()
greenTimer.start()
gtkRunner.start()   # запускаем гтк
pult.start()    #запускаем обработчик пульта

mainTimer.join()    # цепляем треды к основному потоку
redTimer.join()
greenTimer.join()
gtkRunner.join()
pult.join()