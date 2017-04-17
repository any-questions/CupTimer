import time         # либа для таймеров
import threading    # либа для тредов
import gi           # либа для gui
import serial       # либа для uart
import simpleaudio  # для аудио
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

pattern = '{0:02d}:{1:02d}' # формат вывода строки

# wave_obj = simpleaudio.WaveObject.from_wave_file("sounds/airhorn.wav")
# play_obj = wave_obj.play()
# play_obj.wait_done()

short_beep = simpleaudio.WaveObject.from_wave_file("sounds/short_beep.wav")
long_beep = simpleaudio.WaveObject.from_wave_file("sounds/long_beep.wav")
high_beep = simpleaudio.WaveObject.from_wave_file("sounds/high_beep.wav")
low_beep = simpleaudio.WaveObject.from_wave_file("sounds/low_beep.wav")
horn = simpleaudio.WaveObject.from_wave_file("sounds/airhorn.wav")

class MainWindow():
    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file("MainWindow.glade")   # подгружаем интерфейс из файла
        self.window = builder.get_object("window1") # вытаскиваем нужные элементы (само окно)
        self.redTimerText = builder.get_object("redTimer")  # красный таймер
        self.greenTimerText = builder.get_object("greenTimer")  # зеленый таймер
        self.mainTimerText = builder.get_object("mainTimer")    # главный таймер
        self.pult1 = builder.get_object("pult1")    # метки онлайна для каждого пульта
        self.pult2 = builder.get_object("pult2")
        self.pult3 = builder.get_object("pult3")
        self.window.fullscreen()    # растягиваем окно на весь экран

    def resize(self,window):   # функция изменения размера шрифтов при изменении размеров экрана
        height = self.window.get_size()[1] # получаем значение высоты
        width = self.window.get_size()[0]  # и ширины
        self.greenTimerText.modify_font(Pango.FontDescription(str(height / 10)))  # изменяем размеры шрифтов
        self.redTimerText.modify_font(Pango.FontDescription(str(height / 10)))
        self.mainTimerText.modify_font(Pango.FontDescription(str(height / 5)))

    def close_window(self,a,b): # при закрытии окна останавливаем таймеры и закрываем окно
        mainTimer.isRunning = False
        redTimer.isRunning = False
        greenTimer.isRunning = False
        Gtk.main_quit()

class TimerClass(threading.Thread): # класс для таймера
    global horn, short_beep, long_beep, high_beep, low_beep
    def __init__(self, min, sec, timer):    # при инициализации передаем минуты и секунды, а так же какой таймер будем менять
        self.timer = timer  # переменная куда записывается какой таймер меняем
        self.isRunning = False  # флаг работы таймера
        self.currentTime = [min, sec]   # массив с текущим временем таймера
        timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        if (self.timer == 'main'):  # в зависимости от того, с каким таймером работаем (тут главный таймер)
            win.mainTimerText.set_markup(timeString)  # записываем паттерн в ярлык
        elif (self.timer == 'red'):  # (красный таймер)
            win.redTimerText.set_markup(timeString)
        elif (self.timer == 'green'):  # (зеленый таймер)
            win.greenTimerText.set_markup(timeString)
        threading.Thread.__init__(self)  # инициализация функции как треда

    def update(self):   # функция обновляющая текст таймера
        if(self.timer == 'main' and self.isRunning == True):
            play_obj = horn.play()
            play_obj.wait_done()
        while(self.isRunning):  #работает только когда таймер запущен
            self.currentTime[1] -= 1    # вычитаем 1 секунду
            if(self.currentTime[1] < 0):    # если секунды кончились
                self.currentTime[1] = 59    # переписываем секунды
                self.currentTime[0] -= 1    # вычитаем минуту
            if(self.currentTime[1] == 0 and self.currentTime[0] == 0):  # если дотикали до 0 - останавливаем таймер
                self.isRunning = False

            if(self.currentTime[1] == 0 and self.currentTime[0] == 0 and self.timer == 'main'): # если это последний тик главного таймера - пищим высоко
                play_obj = high_beep.play()
                play_obj.wait_done()
            elif(self.currentTime[1] < 6 and self.currentTime[0] == 0 and self.timer == 'main'):    #если у главного таймера еще 5 сек - пищим на каждой
                play_obj = low_beep.play()
                play_obj.wait_done()

            timeString = pattern.format(self.currentTime[0], self.currentTime[1])   # записываем время в паттерн
            if(self.timer=='main'): # в зависимости от того, с каким таймером работаем (тут главный таймер)
                win.mainTimerText.set_markup("<span color='#000000'>" + timeString + "</span>")  # записываем паттерн в ярлык
                win.pult1.set_from_icon_name("gtk-yes", Gtk.IconSize.DIALOG)
            elif(self.timer=='red'):    # (красный таймер)
                win.redTimerText.set_markup("<span color='#640000'>" + timeString + "</span>")
            elif(self.timer=='green'):  # (зеленый таймер)
                win.greenTimerText.set_markup("<span color='#006400'>" + timeString + "</span>")
            time.sleep(1)   #останавливаем тред на секунду

    def run(self):  # функция запускающая таймер
        self.isRunning = True   # поднимаем флаг чтобы таймер работал
        self.update()   # запускаем функцию обновления таймера
        # wave_obj = simpleaudio.WaveObject.from_wave_file("sounds/airhorn.wav")
        # play_obj = wave_obj.play()
        # play_obj.wait_done()


    def setTime(self,min,sec):  # функция установки начального времени таймера
        self.isRunning = False  #приостанавливаем таймер на всякий случай
        self.currentTime = [min,sec]    # записываем новое текущее время
        timeString = pattern.format(self.currentTime[0], self.currentTime[1]) # обновляем текст на экране
        if (self.timer == 'main'):
            win.mainTimerText.set_markup("<span color='#000000'>" + timeString + "</span>")
        elif (self.timer == 'red'):
            win.redTimerText.set_markup("<span color='#640000'>" + timeString + "</span>")
        elif (self.timer == 'green'):
            win.greenTimerText.set_markup("<span color='#006400'>" + timeString + "</span>")

    def pause(self):    # функция постановки таймера на паузу
        self.isRunning = False
    def resume(self):   # снятие с паузы
        self.isRunning = True

# class PultHandler():    # класс обработки сообщений с пульта
#     def __init__(self):
#         self.port = serial.Serial("/dev/ttyUSB0", baudrate=115200)  # открытие порта
#     def __del__(self):
#         self.port.close()   # закрытие порта


win = MainWindow()  # создаем объект класса главного окна
win.window.connect("check-resize", win.resize)  # привазываем ивенты к обработчикам: изменение размера
win.window.connect("delete-event", win.close_window)    # и закрытие окна

win.window.show_all()   # показать элементы оформления

mainTimer = TimerClass(0, 10, 'main')   # создаем таймеры (указываем время и какой таймер, тут главный)
redTimer = TimerClass(0, 11, 'red')  # тут красный
greenTimer = TimerClass(0, 11, 'green')  # тут зеленый


mainTimer.start()
time.sleep(0.5)
redTimer.start()
time.sleep(1.75)
greenTimer.start()

Gtk.main()  # запускаем Gtk

