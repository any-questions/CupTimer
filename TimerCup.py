#!/usr/bin/env python3
import time         # для таймеров
import threading    # для тредов
import gi           # для gui
import serial       # для uart
import simpleaudio as sa  # для аудио
import cairo        # для визуальных эффектов
import cobs         # для декодирования сообщений из uart
import os           # чтобы иметь возможность слать команды os
try:
    import RPi.GPIO as GPIO # для работы с GPIO
    gpio = True
except:
    print("Error importing RPi.GPIO!")
    gpio = False
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GLib, Gdk

###################################################################################
'''
Принцип работы таймера:
Используется кнопка Select для выбора режима работы таймера;
Кнопка Start - запускай таймер;
Кнопка Pause - ставит/снимает таймер с паузы;
Кнопка Reset - сбрасывает таймер к 10 мин 00 сек;
Кнопка Выкл - выключает компьютер полностью;
Поворотная ручка используется для задания времени таймера.
Таймер может работать в трех режимах: искатель, экстремал, просто обратный отсчет.

В режиме ИСКАТЕЛЬ, при нажатии на кнопку Start - начинается обратный отсчет 3 минуты на подготовку,
потом сразу начинается попытка - 10 минут.
Повторное нажатие на кнопку Start до окончания времени на подготовку сразу запускает попытку на 10 минут.

В режиме ЭКСТРЕМАЛ, при нажатии на кнопку Start - начинается обраатный отсчет 7 минут на подготовку,
потом сразу начинается попытка - 10 минут.
Повторное нажатие на кнопку Start до окончания времени на подготовку сразу запускает попытку на 10 минут.

В режиме ОБРАТНОГО ОТСЧЕТА время задается при помощи поворотной ручки с шагом в минуту, после чего при нажати на кнопку
Start начинается обратный отсчет до нуля. Повторное нажатие на кнопку Start эффекта не имеет.

При изменении режима работы таймера - отсчет останавливается в любом случае.
'''
####################################################################################
mode = 2


pattern = '{0:02d}:{1:02d}' # формат вывода строки

eventShortBeep = threading.Event()  #события, которыми будем вызывать проигрывание аудио
eventLongBeep = threading.Event()
eventHighBeep = threading.Event()
eventLowBeep = threading.Event()
eventAirHorn = threading.Event()

class MainWindow(Gtk.Window): # класс основного окна с тремя таймерами
    global mode
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
        cursor = Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)    #скрываем курсор
        self.get_window().set_cursor(cursor)
    
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
            if((mainTimer.currentTime[1] == self.prevTime - 1)):  # если значение секунды сменилось
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
            cr.set_source_rgb(1,1,1)
            # cr.move_to(self.width)
            cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_NORMAL)  # выставляем параметры шрифта
            if(mode == 1):  # если режим ИСКАТЕЛЬ
                (x, y, textWidth, textHeight, dx, dy) = cr.text_extents("Искатель")  # смотрим какую ширину/высоту будет занимать указанный текст
                cr.move_to(self.width/2-textWidth/2,self.height/5)
                cr.show_text("Искатель")
            elif(mode == 2):    # если режим ЭКСТРЕМАЛ
                (x, y, textWidth, textHeight, dx, dy) = cr.text_extents("Экстремал")  # смотрим какую ширину/высоту будет занимать указанный текст
                cr.move_to(self.width/2-textWidth/2,self.height/5)
                cr.show_text("Экстремал")
            cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_NORMAL)  # выставляем параметры шрифта

            # cr.set_source_rgb(1,0,0)    # цвет текста - красный
            # cr.move_to(self.width/4 - textWidth/2, self.height/3)   # перемещаем курсор туда где будем рисовать
            # cr.show_text(redTimer.timeString)  # задаем текст
            #
            # cr.move_to(self.width*3/4 - textWidth/2, self.height/3) # аналогично предыдущему
            # cr.set_source_rgb(0,1,0)    # цвет текста - зеленый
            # cr.show_text(greenTimer.timeString)

            cr.set_font_size(self.size*2)   # аналогично, но у главного таймера текст в два раза больше
            (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("00:00") # смотрим какую ширину/высоту будет занимать указанный текст
            cr.move_to(self.width/2 - textWidth/2, self.height*2/3)
            cr.set_source_rgb(1,1,1)    # цвет текста - белый
            cr.show_text(mainTimer.timeString)
            self.size = self.height/6

        # self.infoSize = self.height/60  #вывод сервисной информации от пультов, высота строки совсем маленькая
        # cr.set_font_size(self.infoSize)
        # (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("P1: None;")
        # cr.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)  # выставляем параметры шрифта
        # cr.set_source_rgb(1,1,1)
        # for i in range(3):  #в цикле выводим статичную часть надписи
        #     cr.move_to(self.width/100+textWidth*1.5*i, self.height*59/60)
        #     cr.show_text("P"+str(i+1)+": ")
        # for i in range(3):  #в цикле же выводим информацию от пультов
        #     cr.move_to(self.width/100+textWidth*1.5*i+textWidth*6/9,self.height*59/60)
        #     if(pult.status[i] == 'None'):   # разным цветом,в зависимости от информации
        #         cr.set_source_rgb(1,0,0)    # красным, если пульта нет, или заряд слишком маленький
        #     elif (pult.status[i] >= 5):
        #         cr.set_source_rgb(0,1,0)    # зеленым, если все хорошо
        #     elif (pult.status[i] < 3):
        #         cr.set_source_rgb(1,0,0)
        #     else:
        #         cr.set_source_rgb(1,1,0)    # желтым если начало садиится
        #     cr.show_text(str(pult.status[i]))

class TimerClass(threading.Thread): # класс для таймера
    global eventHighBeep,eventAirHorn,eventLowBeep,eventLongBeep,eventShortBeep
    def __init__(self, min, sec, timer):    # при инициализации передаем минуты и секунды, а так же какой таймер будем менять
        self.timer = timer  # переменная куда записывается какой таймер меняем
        self.isRunning = False  # флаг работы таймера
        self.isPaused = False   # флаг паузы таймера
        self.finalCountdown = False # флаг того, что идет отсчет последних 5 секунд
        self.currentTime = [min, sec]   # массив с текущим временем таймера
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        # self.restart = False    # флаг, что надо будет запустить отсчет заново для попытки
        self.timerCounter = 1   # счетчик кол-ва вложенных таймеров
        threading.Thread.__init__(self,daemon=True)  # наследование функций треда

    def update(self):   # функция обновляющая текст таймера
        while(self.isRunning):  # работает только когда таймер запущен
            if(self.isPaused == False): # и не на паузе
                self.currentTime[1] -= 1    # вычитаем 1 секунду
                if(self.currentTime[1] < 0):    # если секунды кончились
                    self.currentTime[1] = 59    # переписываем секунды
                    self.currentTime[0] -= 1    # вычитаем минуту

                if(self.currentTime[1] == 0 and self.currentTime[0] == 0):  # если дотикали до 0 - останавливаем таймер
                    if(self.timerCounter == 0):  # если нам не надо ставить сразу таймер попытки - останавливаемся
                        self.isRunning = False
                    else:
                        self.pause()    # ставим отсчет на паузу на всякий случай
                        self.setTime(0,10)  # если надо - выставляем таймер заново
                        self.resume()   # продолжаем отсчет с нового значения
                        self.restart = False
                        mainWindow.prevTime = 6 # настраиваем обратный отсчет для корректной отрисовки заново
                        self.timerCounter -= 1  # уменьшаем кол-во таймеров, которые осталось сосчитать

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
        self.update()   # запускаем функцию обновления таймера

    def setTime(self,min,sec):  # функция установки начального времени таймера
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
    try:
        mainTimer.isRunning = False
    except:
        print("No main timer")
    try:
        redTimer.isRunning = False
    except:
        print("No red timer")
    try:
        greenTimer.isRunning = False
    except:
        print("No green timer")
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
    print("Closing gpio...")
    gpioHandler.Close()
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
                                        port='/dev/ttyAMA0',    # параметры порта (USB0 для пк, AMA0 для родного uart малины)
                                        baudrate=9600,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS)  # открытие порта
        except serial.SerialException:
            print("ERROR: failed to open UART")
        self.status = [5.5,4.3,2.1]    #список содержащий статус для каждого из пультов (None - пульт не найден, напряжение - пульт на месте)
        self.receivedMessage = bytearray()   #полученное сообщение
        self.byte = bytearray()
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
                # print("Getting byte")
                self.byte = self.port.read()    # поочереди выхватываем байты посылки
                print(self.byte)
                self.receivedMessage.append(ord(self.byte))
                print(self.receivedMessage)
                if (hex(ord(self.byte)) == hex(0)):
                    print("parsing")
                    self.ParseMessage(self.receivedMessage)
                    print("cleaning")
                    self.receivedMessage.clear()
                    print(self.receivedMessage)
            else:
                print("Port is not opened")
        print("Reading stopped")

    def ParseMessage(self,encodedLine):
        print("got message")
        for i in range(3):
            print(encodedLine[i])
        # self.decodedLine = cobs.decode(encodedLine)

class GpioHandler(threading.Thread):    # класс отслеживающий состояние GPIO
    def __init__(self):
        # задаем номера gpio для кнопок
        self.GpioSelect = 2 # выбор режима работы
        self.GpioStart = 3  # запуск таймера
        self.GpioPause = 4  # пауза таймера
        self.GpioReset = 17 # сброс таймера
        self.GpioEncA = 27  # установка времени с энкодера
        self.GpioEncB = 22
        self.GpioShutdown = 23  # выключение малины
        chan_list = [self.GpioSelect,self.GpioStart,self.GpioPause,
                     self.GpioReset,self.GpioEncA,self.GpioEncB,self.GpioShutdown]
        GPIO.setmode(GPIO.BCM)  # выбор нумерации пинов - задаем напрямую
        GPIO.setup(chan_list,GPIO.IN)   # устанавливаем все пины на вход

        self.isRunning = False  # флаг, что мы все еще слушаем GPIO (нужен для корректного завершения потока)
        threading.Thread.__init__(self,daemon=True)

    def run(self):
        self.isRunning = True
        self.waitForPress()

    def waitForPress(self): # тупим в цикле пока что нибудь не произойдет
        if(self.isRunning):
            time.sleep(1)

    def HandlerShutdown(self):
        CloseProgram()
        #TODO: проверить будет ли выполняться что то после вызова Close Program
        print("Goodbye")

        #os.system("sudo shutdown -h now")

    def HandlerStart(self): # обработка нажатия на кнопку Start
        global mode
        print("Start countdown")
        if mainTimer.timerCounter > 0:
            mainTimer.pause()
            mainTimer.timerCounter -= 1 # уменьшаем кол-во таймеров, которые надо досчитать
            if(mainTimer.timerCounter == 0 and not mode == 0):    # если это последний таймер который надо запустить и режим попытки
                mainTimer.setTime(10,0) # то ставим его на 10 минут - попытка
            mainTimer.resume()

    def HandlerSelect(self):    # обработка выбора режима
        global mode
        mainTimer.pause()   # ставим таймер на паузу на всякий случай
        mode += 1   # выбираем следующий режим
        if(mode == 1):  # если он стал искатель
            print("Finder")
            mainTimer.timerCounter = 2  # добавляем число таймеров которые надо сосчитать
            mainTimer.setTime(3, 0)  # ставим 3 минуты на подготовку
        elif(mode == 2): # если стал экстремал
            print("Extremal")
            mainTimer.timerCounter = 2  # добавляем число таймеров которые надо сосчитать
            mainTimer.setTime(7, 0)  # ставим 7 минут на подготовку
        elif(mode > 2):
            print("Countdown")  # если просто обратный отсчет
            mode = 0    # mode изменяется в цикле 0 - 1 - 2 - 0
            mainTimer.timerCounter = 1  # говорим что сосчитать надо только один таймер
            mainTimer.setTime(10,0) # по умолчанию он будет таким

    def HandlerPause(self): # обработка нажатия на кнопку Pause
        if mainTimer.isPaused:  # если таймер стоял на паузе - запускаем его, и наоборот
            mainTimer.resume()
        else:
            mainTimer.pause()

    def HandlerReset(self): # обработка нажатия на кнопку Reset
        global mode
        if mode == 0:   # смотрим какой стоял режим работы и ставим его параметры по умолчанию
            mainTimer.timerCounter = 1  # говорим что сосчитать надо только один таймер
            mainTimer.setTime(10,0) # по умолчанию он будет таким
        if mode == 1:
            mainTimer.timerCounter = 2  # добавляем число таймеров которые надо сосчитать
            mainTimer.setTime(3, 0)  # ставим 3 минуты на подготовку
        if mode == 2:
            mainTimer.timerCounter = 2  # добавляем число таймеров которые надо сосчитать
            mainTimer.setTime(7, 0)  # ставим 7 минут на подготовку

    def HandlerEnc(self):   # функция вызывается по одному из каналов энкодера
        if GPIO.input(self.GpioEncB):   # смотрим при этом на состояние другого канала
            mainTimer.currentTime[1] += 1
        else:
            mainTimer.currentTime[1] -= 1
            if(mainTimer.currentTime[1] < 0):
                mainTimer.setTime(0,0)

    def Close(self):
        self.isRunning = False
        GPIO.cleanup()


mainWindow = MainWindow()  # создаем объект класса главного окна
gtkRunner = GtkRunner()

# создаем таймеры, минуты, секунды, какой таймер
redTimer = TimerClass(3, 0, 'red')  # тут красный
greenTimer = TimerClass(3, 0, 'green')  # тут зеленый
mainTimer = TimerClass(0, 10, 'main')   # тут главный
mainTimer.restart = True
player = PlayMusic()    # создаем объект класса проигрывания музыки

pult = PultHandler()    # создаем обработчик пульта

if gpio:
    gpioHandler = GpioHandler() # обработчик нажатий на кнопки


gtkRunner.start()   # запускаем гтк
mainTimer.start()   #запускаем таймеры
player.start()  # запускаем проигрыватель музыки
# redTimer.start()
# greenTimer.start()
pult.start()    #запускаем обработчик пульта

gtkRunner.join()    # цепляем треды к основному потоку
mainTimer.join()
# redTimer.join()
# greenTimer.join()