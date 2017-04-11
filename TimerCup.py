import time         # либа для таймеров
import threading    # либа для тредов
import gi           # либа для gui
import serial       # либа для uart
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

pattern = '{0:02d}:{1:02d}' # формат вывода строки

class MainWindow():
    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_file("MainWindow.glade")
        self.window = builder.get_object("window1")
        self.redTimerText = builder.get_object("redTimer")
        self.greenTimerText = builder.get_object("greenTimer")
        self.mainTimerText = builder.get_object("mainTimer")
        self.pult1 = builder.get_object("pult1")
        self.pult2 = builder.get_object("pult2")
        self.pult3 = builder.get_object("pult3")
        self.window.fullscreen()
    def resize(self,window):   # функция изменения размера шрифтов при изменении размеров экрана
        height = self.window.get_size()[1] # получаем значение высоты
        width = self.window.get_size()[0]  # и ширины
        self.greenTimerText.modify_font(Pango.FontDescription(str(height / 10)))  # изменяем размеры шрифтов
        self.redTimerText.modify_font(Pango.FontDescription(str(height / 10)))
        self.mainTimerText.modify_font(Pango.FontDescription(str(height / 5)))
    def close_window(self,a,b): # при закрытии окна останавливаем таймеры и закрываем окно
        # mainTimer.isRunning = False
        # redTimer.isRunning = False
        # greenTimer.isRunning = False
        Gtk.main_quit()


# class MyWindow(Gtk.Window): # класс основного окна
#     def __init__(self):
#         Gtk.Window.__init__(self, title="Timers")   #инициализация окна GTK
#         self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)   # вертикальная развертка виджетов
#         self.hbox = Gtk.Box(spacing=10) # горизонтальная развертка виджетов
#
#         self.greenTimer = Gtk.Label()   # текст зеленого таймера
#         self.greenTimer.set_markup("<span color='#006400'>00:00</span>")    # вывод текста зеленого таймера
#         self.hbox.pack_start(self.greenTimer, True, True, 0)    # вставляем текст таймера в горизонтальную развертку
#         self.redTimer = Gtk.Label() # аналогично зеленому таймеру
#         self.redTimer.set_markup("<span color='#640000'>00:00</span>")
#         self.hbox.pack_start(self.redTimer, True, True, 0)
#
#         self.vbox.pack_start(self.hbox, True, True, 0)  # вставляем горизонтальную развертку первым пунктом вертикальной
#         self.mainTimer = Gtk.Label()    # текст главного таймера (10 или 3 мин на подготовку)
#         self.mainTimer.set_markup("<span color='#000000'>00:00</span>") # его текст
#         self.vbox.pack_start(self.mainTimer, True, True, 0) # вставляем его в вертикальную развертку
#
#         self.add(self.vbox) # вставляем вертикальную развертку со всем в главный виджет
#         self.fullscreen()   # растягиваем на весь экран
#     def resize(self, window):   # функция изменения размера шрифтов при изменении размеров экрана
#         height = self.get_size()[1] # получаем значение высоты
#         width = self.get_size()[0]  # и ширины
#         self.greenTimer.modify_font(Pango.FontDescription(str(height/10)))  # изменяем размеры шрифтов
#         self.redTimer.modify_font(Pango.FontDescription(str(height/10)))
#         self.mainTimer.modify_font(Pango.FontDescription(str(height/5)))
#
#     def close_window(self,a,b): # при закрытии окна останавливаем таймеры и закрываем окно
#         mainTimer.isRunning = False
#         redTimer.isRunning = False
#         greenTimer.isRunning = False
#         Gtk.main_quit()

# class TimerClass(threading.Thread): # класс для таймера
#     def __init__(self, min, sec, timer):    # при инициализации передаем минуты и секунды, а так же какой таймер будем менять
#         self.timer = timer  # переменная куда записывается какой таймер меняем
#         self.isRunning = False  # флаг работы таймера
#         self.currentTime = [min, sec]   # массив с текущим временем таймера
#         timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
#         if (self.timer == 'main'):  # в зависимости от того, с каким таймером работаем (тут главный таймер)
#             win.mainTimer.set_markup("<span color='#000000'>" + timeString + "</span>")  # записываем паттерн в ярлык
#         elif (self.timer == 'red'):  # (красный таймер)
#             win.redTimer.set_markup("<span color='#640000'>" + timeString + "</span>")
#         elif (self.timer == 'green'):  # (зеленый таймер)
#             win.greenTimer.set_markup("<span color='#006400'>" + timeString + "</span>")
#         threading.Thread.__init__(self)  # инициализация функции как треда
#
#     def update(self):   # функция обновляющая текст таймера
#         while(self.isRunning):  #работает только когда таймер запущен
#             self.currentTime[1] -= 1    # вычитаем 1 секунду
#             if(self.currentTime[1] < 0):    # если секунды кончились
#                 self.currentTime[1] = 59    # переписываем секунды
#                 self.currentTime[0] -= 1    # вычитаем минуту
#             timeString = pattern.format(self.currentTime[0], self.currentTime[1])   # записываем время в паттерн
#             if(self.timer=='main'): # в зависимости от того, с каким таймером работаем (тут главный таймер)
#                 win.mainTimer.set_markup("<span color='#000000'>" + timeString + "</span>")  # записываем паттерн в ярлык
#             elif(self.timer=='red'):    # (красный таймер)
#                 win.redTimer.set_markup("<span color='#640000'>" + timeString + "</span>")
#             elif(self.timer=='green'):  # (зеленый таймер)
#                 win.greenTimer.set_markup("<span color='#006400'>" + timeString + "</span>")
#             time.sleep(1)   #останавливаем тред на секунду
#     def run(self):  # функция запускающая таймер
#         self.isRunning = True   # поднимаем флаг чтобы таймер работал
#         self.update()   # запускаем функцию обновления таймера
#
#     def setTime(self,min,sec):  # функция установки начального времени таймера
#         self.isRunning = False  #приостанавливаем таймер на всякий случай
#         self.currentTime = [min,sec]    # записываем новое текущее время
#         timeString = pattern.format(self.currentTime[0], self.currentTime[1]) # обновляем текст на экране
#         if (self.timer == 'main'):
#             win.mainTimer.set_markup("<span color='#000000'>" + timeString + "</span>")
#         elif (self.timer == 'red'):
#             win.redTimer.set_markup("<span color='#640000'>" + timeString + "</span>")
#         elif (self.timer == 'green'):
#             win.greenTimer.set_markup("<span color='#006400'>" + timeString + "</span>")
#
#     def pause(self):    # функция постановки таймера на паузу
#         self.isRunning = False
#     def resume(self):   # снятие с паузы
#         self.isRunning = True

win = MainWindow()
win.window.connect("check-resize", win.resize)
win.window.connect("delete-event", win.close_window)

win.window.show_all()

#
# mainTimer = TimerClass(10, 0, 'main')
# redTimer = TimerClass(2, 0, 'red')
# greenTimer = TimerClass(2, 0, 'green')

# win.show_all()
# mainTimer.start()
# time.sleep(0.5)
# redTimer.start()
# time.sleep(1.75)
# greenTimer.start()
Gtk.main()
