import time         # либа для таймеров
import threading    # либа для тредов
import queue        # либа для очередей
import gi           # либа для gui
import serial       # либа для uart
import simpleaudio as sa  # для аудио
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

pattern = '{0:02d}:{1:02d}' # формат вывода строки

eventShortBeep = threading.Event()
eventLongBeep = threading.Event()
eventHighBeep = threading.Event()
eventLowBeep = threading.Event()
eventAirHorn = threading.Event()

class MainWindow(): # класс основного окна с тремя таймерами
    global eventHighBeep,eventAirHorn,eventLowBeep,eventLongBeep,eventShortBeep
    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file("MainWindow.glade")   # подгружаем интерфейс из файла
        self.mainWindow = builder.get_object("mainWindow") # вытаскиваем нужные элементы (само окно)
        self.countdownWindow = builder.get_object("countdownWindow")
        self.redTimerText = builder.get_object("redTimer")  # красный таймер
        self.greenTimerText = builder.get_object("greenTimer")  # зеленый таймер
        self.mainTimerText = builder.get_object("mainTimer")    # главный таймер
        self.pult1 = builder.get_object("pult1")    # метки онлайна для каждого пульта
        self.pult2 = builder.get_object("pult2")
        self.pult3 = builder.get_object("pult3")
        self.mainWindow.fullscreen()    # растягиваем окно на весь экран

    def Resize(self, window):   # функция изменения размера шрифтов при изменении размеров экрана
        height = self.mainWindow.get_size()[1] # получаем значение высоты
        width = self.mainWindow.get_size()[0]  # и ширины
        self.greenTimerText.modify_font(Pango.FontDescription('Ds-Digital Italic '+str(height/10)))  # изменяем размеры шрифтов
        self.redTimerText.modify_font(Pango.FontDescription('Ds-Digital Italic '+str(height/10)))
        self.mainTimerText.modify_font(Pango.FontDescription('Ds-Digital Italic '+str(height/5)))

    # def SwitchWindow(self): # функция переключения между окнами
    #     self.mainWindow.iconify()   # сворачиваем главное окно
    #     self.mainWindow.close()  # закрываем главное окно
    #     time.sleep(0.01)
    #     self.countdownWindow.show()
    #     self.countdownWindow.fullscreen()

class CountDownWindow():
    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file("CountDownWindow.glade")   # подгружаем интерфейс из файла
        self.countDownWindow = builder.get_object("countDownWindow")
        self.countDownLabel = builder.get_object("countDownLabel")
        self.countDownWindow.fullscreen()
    def Resize(self,window):
        height = self.countDownWindow.get_size()[1]
        self.countDownLabel.modify_font(Pango.FontDescription('Ds-Digital Italic '+str(height/5)))

def SwitchWindow():
    if(win.mainWindow.is_active()):
        # win.mainWindow.iconify()
        win.mainWindow.close()
        time.sleep(0.01)
        countDown.countDownWindow.show_all()
        countDown.countDownWindow.fullscreen()


class TimerClass(threading.Thread): # класс для таймера
    global eventHighBeep,eventAirHorn,eventLowBeep,eventLongBeep,eventShortBeep
    def __init__(self, min, sec, timer, win):    # при инициализации передаем минуты и секунды, а так же какой таймер будем менять
        self.timer = timer  # переменная куда записывается какой таймер меняем
        self.isRunning = False  # флаг работы таймера
        self.currentTime = [min, sec]   # массив с текущим временем таймера
        self.eventShortBeep = threading.Event()
        timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        if (self.timer == 'main'):  # в зависимости от того, с каким таймером работаем (тут главный таймер)
            win.mainTimerText.set_text(timeString)  # записываем паттерн в ярлык
        elif (self.timer == 'red'):  # (красный таймер)
            win.redTimerText.set_text(timeString)
        elif (self.timer == 'green'):  # (зеленый таймер)
            win.greenTimerText.set_text(timeString)
        threading.Thread.__init__(self)  # инициализация функции как треда

    def update(self):   # функция обновляющая текст таймера
        while(self.isRunning):  #работает только когда таймер запущен
            self.currentTime[1] -= 1    # вычитаем 1 секунду
            if(self.currentTime[1] < 0):    # если секунды кончились
                self.currentTime[1] = 59    # переписываем секунды
                self.currentTime[0] -= 1    # вычитаем минуту
            if(self.currentTime[1] == 0 and self.currentTime[0] == 0):  # если дотикали до 0 - останавливаем таймер
                self.isRunning = False
                if(self.timer == 'main'):
                    eventLowBeep.set()
                    SwitchWindow()

            timeString = pattern.format(self.currentTime[0], self.currentTime[1])   # записываем время в паттерн
            if(self.timer=='main'): # в зависимости от того, с каким таймером работаем (тут главный таймер)
                eventHighBeep.set()
                win.mainTimerText.set_text(timeString)  # записываем паттерн в ярлык
                win.pult1.set_from_icon_name("gtk-yes", Gtk.IconSize.DIALOG)
            elif(self.timer=='red'):    # (красный таймер)
                win.redTimerText.set_text(timeString)
            elif(self.timer=='green'):  # (зеленый таймер)
                win.greenTimerText.set_text(timeString)

            print(self.timer + " " + str(self.currentTime[0]) + " m " + str(self.currentTime[1]) + " s ")   # дебаговый вывод
            time.sleep(1)   #останавливаем тред на секунду

    def __del__(self):
        self.isRunning = False

    def run(self):  # функция запускающая таймер
        self.isRunning = True   # поднимаем флаг чтобы таймер работал
        if(self.timer == 'main'):
            eventAirHorn.set()
        self.update()   # запускаем функцию обновления таймера

    def setTime(self,min,sec):  # функция установки начального времени таймера
        self.isRunning = False  #приостанавливаем таймер на всякий случай
        self.currentTime = [min,sec]    # записываем новое текущее время
        timeString = pattern.format(self.currentTime[0], self.currentTime[1]) # обновляем текст на экране
        if (self.timer == 'main'):
            win.mainTimerText.set_markup(timeString)
        elif (self.timer == 'red'):
            win.redTimerText.set_markup(timeString)
        elif (self.timer == 'green'):
            win.greenTimerText.set_markup(timeString)

    def pause(self):    # функция постановки таймера на паузу
        self.isRunning = False

    def resume(self):   # снятие с паузы
        self.isRunning = True

class PlayMusic(threading.Thread):
    def __init__(self):
        self.short_beep = sa.WaveObject.from_wave_file("sounds/short_beep.wav")
        self.long_beep = sa.WaveObject.from_wave_file("sounds/long_beep.wav")
        self.low_beep = sa.WaveObject.from_wave_file("sounds/low_beep.wav")
        self.high_beep = sa.WaveObject.from_wave_file("sounds/high_beep.wav")
        self.horn = sa.WaveObject.from_wave_file("sounds/airhorn.wav")
        threading.Thread.__init__(self)
    def __del__(self):
        self.isRunning = False

    def run(self):
        self.isRunning = True
        self.Handler()

    def Handler(self):
        while(self.isRunning == True):
            if(eventLongBeep.isSet()):
                eventLongBeep.clear()
                print("Long Beep ")
            elif (eventShortBeep.isSet()):
                eventShortBeep.clear()
                print("Short Beep ")
            elif (eventHighBeep.isSet()):
                eventHighBeep.clear()
                print("High Beep ")
            elif (eventLowBeep.isSet()):
                eventLowBeep.clear()
                print("Low Beep ")
                # win.SwitchWindow()
            elif (eventAirHorn.isSet()):
                eventAirHorn.clear()
                print("Air Horn ")
    # def horn(self):
    #     self.horn.play()
    # def short_beep(self):
    #     self.short_beep.play()
    # def long_beep(self):
    #     self.long_beep.play()
    # def low_beep(self):
    #     self.low_beep.play()
    # def high_beep(self):
    #     self.high_beep.play()


def CloseProgram(a, b): # при закрытии программы останавливаем таймеры и закрываем окно
    mainTimer.isRunning = False
    redTimer.isRunning = False
    greenTimer.isRunning = False
    player.isRunning = False
    eventShortBeep.clear()
    eventLongBeep.clear()
    eventHighBeep.clear()
    eventLowBeep.clear()
    eventAirHorn.clear()
    print("WINDOW CLOSED")
    # Gtk.main_quit()

def GtkRun():
    Gtk.main()


# class PultHandler():    # класс обработки сообщений с пульта
#     def __init__(self):
#         self.port = serial.Serial("/dev/ttyUSB0", baudrate=115200)  # открытие порта
#     def __del__(self):
#         self.port.close()   # закрытие порта

win = MainWindow()  # создаем объект класса главного окна
countDown = CountDownWindow()   # создаем объект  класса окна обратного отсчета
player = PlayMusic()    # создаем объект класса проигрывания музыки
player.start()
win.mainWindow.connect("check-resize", win.Resize)  # привазываем ивенты к обработчикам: изменение размера
win.mainWindow.connect("delete-event", CloseProgram)    # и закрытие окна

win.mainWindow.show_all()   # показать элементы оформления

redTimer = TimerClass(0, 5, 'red', win)  # тут красный
greenTimer = TimerClass(0, 5, 'green', win)  # тут зеленый
mainTimer = TimerClass(0, 4, 'main',win)   # создаем таймеры (указываем время и какой таймер, тут главный)

mainTimer.start()
# time.sleep(0.5)
redTimer.start()
# time.sleep(1.75)
greenTimer.start()

t1 = threading.Thread(target=GtkRun())  # запускаем Gtk
