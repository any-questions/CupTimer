#!/usr/bin/env python3
import time         # для таймеров
import threading    # для тредов
import gi           # для gui
import cairo        # для визуальных эффектов
import os           # чтобы иметь возможность слать команды os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GLib, Gdk
# import serial       # для uart
# import simpleaudio as sa  # для аудио (оставлено на будущее)
from pydub import AudioSegment
from pydub.playback import play
# import cobs         # для декодирования сообщений из uart (оставлено на будущее)

try:
    from pynput import keyboard     # для слежения за клавиатурой
    keys = True
except ImportError:
    print("Error importing pynput!")
    keys = False

try:
    import RPi.GPIO as GPIO  # для работы с GPIO
    gpio = True

except RuntimeError:
    print("Error importing RPi.GPIO!")
    gpio = False

# TODO: Придумать рабочий способ воспроизведения звука на Raspberry
# TODO: Максимально упростить добавление новых режимов

############
'''
Принцип работы таймера:
Кнопка Select используется для выбора режима работы таймера;
Кнопка Start - запускает таймер (или досрочно его завершает);
Кнопка Pause - ставит/снимает таймер с паузы;
Кнопка Reset - сбрасывает таймер в зависимости от режима;
Кнопка Выкл (Shutdown) - выключает компьютер полностью;
Поворотная ручка используется для задания времени таймера.
Таймер может работать в нескольких режимах: искатель, экстремал, экстремал про, искатель мини, агро,
просто обратный отсчет.

В режиме ИСКАТЕЛЬ, ЭКСТРЕМАЛ, ЭКСТРЕМАЛ Pro, Искатель Мини, АГРО-I при нажатии на кнопку Start - начинается обратный 
отсчет времени на подготовку, потом сразу начинается попытка.
Повторное нажатие на кнопку Start до окончания времени на подготовку сразу запускает попытку.
Следующее нажатие на кнопку Start до окончании времени завершает попытку.

В режиме ПЕРЕРЫВ время задается при помощи поворотной ручки с шагом в минуту, после чего при нажати на кнопку
Start начинается обратный отсчет до нуля. Повторное нажатие на кнопку Start досрочно останавливает таймер.

В режиме ОТБОРОЧНЫЙ ТУР таймер может работать до бесконечности - сначала время подготовки, потом время на попытку.

Изменение режима работы таймера, сброс таймера, а также выключение доступны только если обратный отсчет не идет, т.е.
во время обратного отсчета (любого) кнопки Select, Reset, Shutdown неактивны.
'''
############
'''
Допустимо управление таймером с клавиатуры:
Space = Start
Backspace = Reset
P (английская P, русская З) =  Pause
стрелки влево-вправо = Select
стрелки вверх-вниз = установка времени для режима работы ПЕРЕРЫВ
Esc = закрытие программы
'''
############
'''
Словарь с режимами работы таймера. 
Ключ - текст который будет отображаться на экране, значение - список из двух списков: первый - время подготовки, 
второй - время попытки. Время указывается как [минуты, секунды].
'''
############
modsDict = {"Перерыв":              [[10, 0], ],  # особый режим где нужен всего 1 таймер
            "Искатель 2.0":         [[3, 0], [10, 0]],
            "Экстремал 1.0":        [[7, 0], [10, 0]],
            "Экстремал Pro 1.0":    [[7, 0], [10, 0]],
            "Искатель Мини 2.0":    [[3, 0], [5, 0]],
            "Агро-I":               [[3, 0], [8, 0]],
            "Отборочный тур":       [[0, 20], [0, 20]]  # этот режим работы должен крутиться до бесконечности
            }


infinite = ["Отборочный тур"]   # список режимов которые должны крутиться до бесконечности
modsNames = list(modsDict.keys())
modsNames.sort()    # если не сортировать, этот список будет формироваться случайно до версии питона 3.7

# режим по умолчанию (в данном случае 0 - первый режим по алфавиту)
currentMode = 3

textAttempt = "Попытка"         # на отборочный тур надо дописывать "Попытка"
textPreparing = "Подготовка"    # для всех режимов время подготовки
textAttemptEnd = "Попытка закончена"
textAdditional = "Пауза"    # когда таймер ставим на паузу с кнопки - пишем об этом

pattern = '{0:02d}:{1:02d}'     # формат вывода строки

eventBeep = threading.Event()  # события, которыми будем вызывать проигрывание аудио
eventBleep = threading.Event()
eventGong1 = threading.Event()
eventGong2 = threading.Event()
eventGongLaugh = threading.Event()
eventAirHorn = threading.Event()
eventAttemptStart = threading.Event()
eventAttemptEnd = threading.Event()

pauseButtonToggled = False     # флаг, что нажали на кнопку Pause


class MainWindow(Gtk.Window):   # класс основного окна с тремя таймерами
    global currentMode, pause, finder, extremal

    def __init__(self):
        super(MainWindow, self).__init__()  # переопределяем init
        self.set_title("Timer")     # заголовок окна
        self.set_size_request(800,600)
        # self.fullscreen()   # растягиваем на весь экран
        self.connect("destroy", CloseProgram)    # связываем закрытие окна с функцией заверщеия программы
        self._drawArea = Gtk.DrawingArea()   # создаем drawing area на которой будем рисовать приложение
        self._drawArea.connect("draw", self.expose)   # связываем событие с функцией перерисовки содержимого
        self.add(self._drawArea)     # добавляем drawing area в окно приложения
        self._isRunning = True   # флаг что программа работает
        GLib.timeout_add(100, self.on_timer)    # таймер по которому каждые 100 мс будем перерисовывать содержимое
        self.show_all()     # отображаем окно
        cursor = Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)    # скрываем курсор
        self.get_window().set_cursor(cursor)
        self._currentTime = [0, 0]

        # служебные переменные (здесь обнулены, т.к. они обновляются при изменении размера окна, а это происходит
        # не сразу при запуске)
        self._width = 0
        self._height = 0
        self._lineHeight = 0
        self._size = 0      # текущий размер текста
        self._blinkCounter = 0    # счетчик, по которому будет мигать текст главного таймера в режиме паузы

        print("Main window is created")

    def on_timer(self):
        if not self._isRunning:
            return False

        self._drawArea.queue_draw()    # по таймеру дергаем событие на перерисовку
        return True

    def draw_text(self, text, size, coord_x, coord_y, cr, color=(1, 1, 1)):   # функция для отрисовки одной строки текста
        '''
        :param text: отображаемый текст
        :param size: размер текста
        :param coord_x: координата X центра текста
        :param coord_y: координата Y центра текста
        :param cr: служебный модуль cairo который надо передавать в функцию
        :param color: цвет текста, по умолчанию - белый
        :return:
        '''
        cr.set_font_size(size)
        cr.set_source_rgb(color[0], color[1], color[2])
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents(text)
        cr.move_to(coord_x - dx / 2, coord_y + filledHeight / 2)
        '''
        Пояснение: text_extents возвращает параметры того, сколько будет занимать на экране текст, если его выводить
        функцией show_text. dx, dy - на сколько сместится курсор по оси X, и Y соответственно, filledWidth, filledHeight - 
        ширина и высота закрашиваемых пикселей (это важно). Если подсунуть в текст одни пробелы - filledWidth и filledHeight
        будут 0, но dx - нет. Тоже касается выбранного шрифта Digital Dismay, если печатать им цифру 1 значения dx и 
        filledWidth будут разными. Это приводит к сдвигам текста когда пытаемся вывести на экран 10:00 и 09:59. 
        Поэтому мы смотрим на смещение курсора и на высоту текста при печати. (Скорее всего я написал довольно невнятно,
         поэтому вот пример:
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents("10:00")
        print("filledWidth = %d, filledHeight = %d, dx = %d, dy = %d" % (filledWidth, filledHeight, dx, dy))
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents("09:59")
        print("filledWidth = %d, filledHeight = %d, dx = %d, dy = %d" % (filledWidth, filledHeight, dx, dy))
        '''
        cr.show_text(text)

    def expose(self, widget, cr):
        self._width = self.get_size()[0]     # получаем значения ширины и высоты
        self._height = self.get_size()[1]
        self._lineHeight = self._height / 5  # задаем высоту строки = 1/5  высоты экрана
        textHeight = self._lineHeight * 0.8
        textPos = self._lineHeight / 3

        cr.set_source_rgb(0, 0, 0)    # фон красим в черный
        cr.paint()  # заливаем фон
        self._currentTime = mainTimer.GetCurrentTime()

        # выставляем параметры шрифта
        # если тикают последние 10 секунд главного таймера (причем этот таймер последний)
        # не касается режимов Перерыв и бесконечных
        if mainTimer.finalCountdown is True and mainTimer.GetTimerListLen() == 1 \
                and not modsNames[currentMode] == "Перерыв" and not modsNames[currentMode] in infinite:
            # если дотикал до конца таймер попытки - выводим соответствующий текст "Попытка закончена"
            if self._currentTime[0] == 0 and self._currentTime[1] == 0:
                time.sleep(0.5)     # ждем чуть чуть чтобы ноль явно повисел
                cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.draw_text(textAttemptEnd, self._lineHeight, self._width/2, self._height/2, cr)
            else:   # если нет - выводим большие красные цифры последних секунд отсчета
                cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.draw_text(mainTimer.GetTimer(), self._lineHeight*4, self._width/2, self._height/2, cr, (1, 0, 0))

        else:   # если не идет обратный отсчет последних секунд
            # выставляем параметры шрифта
            cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

            self.draw_text(modsNames[currentMode], textHeight, self._width/2, textPos, cr)  # пишем имя текущего режима

            if mainTimer.GetTimerListLen() > 1:     # если есть еще доп таймеры в списке - добавляем фразу "подготовка"
                self.draw_text(textPreparing, self._lineHeight/2, self._width/2, self._lineHeight, cr)
            elif modsNames[currentMode] in infinite:    # для бесконечных режимов пишем также фразу "попытка"
                self.draw_text(textAttempt, self._lineHeight/2, self._width/2, self._lineHeight, cr)

            cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            # вывод главного таймера, если осталось 10 сек - рисуется красным(только для реджимов перерыв и бесконечных)
            if mainTimer.finalCountdown is True:
                self.draw_text(mainTimer.GetTimer(), self._lineHeight*3, self._width/2, self._lineHeight*2.5, cr,(1,0,0))
            else:
                self.draw_text(mainTimer.GetTimer(), self._lineHeight*3, self._width/2, self._lineHeight*2.5, cr)

            if pauseButtonToggled and self._blinkCounter//5 != 0:
                cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.draw_text(textAdditional, self._lineHeight, self._width/2, self._lineHeight*4,cr)

        self._blinkCounter += 1
        if self._blinkCounter > 9: self._blinkCounter = 0

############
'''
Класс для работы таймера. Параметрами являются список таймеров, который включает в себя:
минуты, секунды для нескольких таймеров подряд, и тип таймера - главный, крсный или зеленый.
При работе таймера флаг isRunning позволяет треду работать, флаг isPaused - ставит текущий таймер на паузу.
Если в списке таймеров больше одного элемента - они отсчитываются по очереди,
если он только один - таймер останавливается.
после того как дотикает до конца.
'''
############


class TimerClass(threading.Thread):
    # global eventHighBeep, eventAirHorn, eventLowBeep, eventLongBeep, eventShortBeep
    global eventAttemptStart, eventAttemptEnd
    def __init__(self, timerList, timer):
        self.timerList = []  # список таймеров
        self.currentTime = [0, 0]     # записываем время: мин, сек
        self.SetTimerList(timerList)    # записываем список таймеров и текущее время
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        self.timer = timer  # тип таймера
        self.isRunning = False  # флаг, чтобы тред работал
        self.isPaused = True    # флаг, чтобы ставить таймер на паузу
        self.finalCountdown = False     # флаг, что идет отсчет последних 5 секунд
        print(timer,"timer is created")
        threading.Thread.__init__(self, daemon=True)

    def Update(self):   # функция обновления таймера
        while self.isRunning:      # пока тред запущен
            if not self.isPaused:  # если таймер не на паузе

                self.currentTime[1] -= 1    # вычитаем одну секунду
                if self.currentTime[1] < 0:     # если секунды кончились
                    if self.currentTime[0] > 0:     # а минуты еще остались
                        self.currentTime[1] = 59    # переписываем секунды
                        self.currentTime[0] -= 1    # вычитаем минуту
                    else:
                        self.currentTime[1] = 0
                    if self.currentTime[0] < 0:
                        self.currentTime[0] = 0

                if self.currentTime[0] == 0 and self.currentTime[1] == 0:   # если дотикали до нуля
                    if len(self.timerList) > 1:     # если еще остались таймеры, которые нужно дотикать
                        self.timerList.pop(0)       # убираем из списка тот, который кончился
                        self.finalCountdown = False
                        # записываем время нового таймера: мин, сек
                        self.currentTime = [self.timerList[0][0], self.timerList[0][1]]
                    else:
                        if self.timer == 'main' and modsNames[currentMode] in infinite:     # если таймеру надо крутиться до бесконечности
                            self.SetTimerList(modsDict[modsNames[currentMode]])   # обновляем список таймеров
                            self.Resume()   # и сразу запускаем таймер дальше
                        else:
                            self.isPaused = True    # если это был последний таймер - останавливаем отсчет
                    if self.timer == 'main' and modsNames[currentMode] in infinite:
                        if len(self.timerList) > 1:
                            print("Prepare!")
                            eventAttemptEnd.set()
                        else:
                            print("Attempt!")
                            eventAttemptStart.set()

                elif self.currentTime[0] == 0 and self.currentTime[1] <= 10:  # если осталось тикать 10 секунд
                    self.finalCountdown = True  # поднимаем флаг, чтобы окно перерисовывалось по другому
                time.sleep(1)   # останавливаем тред на секунду
        print(self.timer,"timer stopped")

    def run(self):  # функция для запуска треда
        self.isRunning = True
        self.Update()

    def SetTimerList(self, timerList):   # функция задания нового списка таймеров
        self.isPaused = True    # на всякий случай ставим на паузу
        self.timerList = timerList.copy()
        self.currentTime = [self.timerList[0][0], self.timerList[0][1]]
        self.finalCountdown = False

    def Pause(self):    # поставить отсчет на паузу
        self.isPaused = True

    def Resume(self):   # снять отсчет с паузы
        self.isPaused = False

    def GetIsPaused(self):  # получить состояние флага паузы
        return self.isPaused

    def Force(self):    # завершить отсчет текущего таймера, чтобы перейти к следующему
        if not (self.currentTime[0] == 0 and self.currentTime[1] == 0):
            self.isPaused = True
            self.currentTime[0] = 0
            self.currentTime[1] = 1
            self.finalCountdown = True
            self.isPaused = False

    def Exit(self):     # завершить тред
        self.isRunning = False

    def GetCurrentTime(self):   # возвращает время которое осталось дотикать
        return self.currentTime

    def GetCurrentMin(self):    # возвращает число минут которые осталось дотикать
        return self.currentTime[0]

    def GetCurrentSec(self):    # возвращает число секунд которое осталось дотикать
        return self.currentTime[1]

    def GetTimerListLen(self):  # возвращает число таймеров, которые осталось дотикать
        return len(self.timerList)

    def GetTimer(self):
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        return self.timeString


######
'''
Класс для воспроизведения звуковых сигналов. Работает в отдельном потоке. По сути являет собой бесконечный цикл -
обработчик событий. События глобальные, выставляются классом таймера. Когда срабатывает событие - проигрывается
соответствующий звук и событие сбрасывается.
'''
######


class PlayMusic(threading.Thread):  # класс для воспроизведения мелодий
    def __init__(self):
        dirpath = os.getcwd()   # получаем расположение текущей папки
        print("Сurrent directory is:", dirpath)
        foldername = os.path.basename(dirpath)  # получаем имя текущей папки
        print("Сurrent folder is:", foldername)
        # указываем пути к мелодиям, которые будем проигрывать
        if foldername == "CupTimer":
            print("Path to audio: sounds/*.wav")
            # self.horn = sa.WaveObject.from_wave_file("sounds/airhorn.wav")
            # self.beep = sa.WaveObject.from_wave_file("sounds/beep.wav")
            # self.bleep = sa.WaveObject.from_wave_file("sounds/bleep.wav")
            # self.gong1 = sa.WaveObject.from_wave_file("sounds/gong1.wav")
            # self.gong2 = sa.WaveObject.from_wave_file("sounds/gong2.wav")
            # self.gongLaugh = sa.WaveObject.from_wave_file("sounds/gongLaugh.wav")
            self.attemptStart = AudioSegment.from_mp3("sounds/attempt_start.mp3")
            self.attemptEnd = AudioSegment.from_mp3("sounds/attempt_end.mp3")
        else:
            print("Path to audio:"+dirpath+"/CupTimer/sounds/*.wav")
            # self.horn = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/airhorn.wav")
            # self.beep = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/beep.wav")
            # self.bleep = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/bleep.wav")
            # self.gong1 = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/gong1.wav")
            # self.gong2 = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/gong2.wav")
            # self.gongLaugh = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/gongLaugh.wav")
            self.attemptStart = AudioSegment.from_mp3(dirpath+"sounds/attempt_start.mp3")
            self.attemptEnd = AudioSegment.from_mp3(dirpath+"sounds/attempt_end.mp3")
        self.isRunning = False
        threading.Thread.__init__(self, daemon=True)     # наследование функций треда
        print("Audio player is created")

    def __del__(self):  # деструктор останавливает флаг
        self.isRunning = False

    def run(self):  # запуск обработчика событий
        self.isRunning = True
        self.Handler()

    def Handler(self):  # обработчик событий
        while self.isRunning is True:   # работает пока поднят флаг
            # if eventAirHorn.isSet():      # стартовый горн
            #     eventAirHorn.clear()
            #     self.horn.play()
            # elif eventBeep.isSet():
            #     eventBeep.clear()
            #     self.beep.play()
            #
            # elif eventBleep.isSet():
            #     eventBleep.clear()
            #     self.bleep.play()
            #
            # elif eventGong1.isSet():
            #     eventGong1.clear()
            #     self.gong1.play()
            #
            # elif eventGong2.isSet():
            #     eventGong2.clear()
            #     self.gong2.play()
            #
            # elif eventGongLaugh.isSet():
            #     eventGongLaugh.clear()
            #     self.gongLaugh.play()
            if eventAttemptStart.is_set():
                eventAttemptStart.clear()
                play(self.attemptStart)
            elif eventAttemptEnd.is_set():
                eventAttemptEnd.clear()
                play(self.attemptEnd)
            time.sleep(0.001)
        print("Audio player stopped")

    def Exit(self):
        self.isRunning = False

############
'''
Маленький служебный класс для запуска Gtk в отдельном потоке.
'''
############


class GtkRunner(threading.Thread):
    def __init__(self):   # запуск гтк в отдельном треде
        threading.Thread.__init__(self)

    def run(self):
        Gtk.main()

############
'''
Класс для общения с UART и обработки входящих сообщений с пультов управления таймером.
Пока не доработан и не используется.
'''
############


class PultHandler(threading.Thread):    # класс обработки сообщений с пульта
    def __init__(self):
        self.isRunning = False
        try:
            print("Opening UART port...")
            # параметры порта (USB0 для пк, AMA0 для родного uart малины)
            self.port = serial.Serial(  # открываем порт
                                        port='/dev/ttyAMA0',
                                        baudrate=9600,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS)  # открытие порта
        except serial.SerialException:
            print("ERROR: failed to open UART")
        # список содержащий статус для каждого из пультов (None - пульт не найден, напряжение - пульт на месте)
        self.status = [5.5, 4.3, 2.1]
        self.receivedMessage = bytearray()   # полученное сообщение
        self.byte = bytearray()
        threading.Thread.__init__(self, daemon=True)  # наследование функций треда

    def __del__(self):
        print("Closing port...")
        self.isRunning = False
        try:
            self.port.close()   # закрытие порта
        except AttributeError:  # сообщение об ошибке, если не вышло
            print("Closing ERROR, no port was created.")

    def Exit(self):
        print("Closing pult...")
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
            self.ReadPort()     # получение сообщений из порта
        except:
            print("Reading ERROR, no port was created.")    # сообщение об ошибке, если не вышло

    def ReadPort(self):     # функция читающая порт
        while self.isRunning is True:
            if self.port.isOpen:   # проверяем открыт ли uart
                # print("Getting byte")
                self.byte = self.port.read()    # поочереди выхватываем байты посылки
                print(self.byte)
                self.receivedMessage.append(ord(self.byte))
                print(self.receivedMessage)
                if hex(ord(self.byte)) == hex(0):
                    print("parsing")
                    self.ParseMessage(self.receivedMessage)
                    print("cleaning")
                    self.receivedMessage.clear()
                    print(self.receivedMessage)
            else:
                print("Port is not opened")
        print("Reading stopped")

    def ParseMessage(self, encodedLine):
        print("got message")
        for i in range(3):
            print(encodedLine[i])
        # self.decodedLine = cobs.decode(encodedLine)



############
'''
Класс для работы с главным таймером. К нему будут обращаться обработчики нажатий на кнопки и на клавиатуру. 
'''
############


class TimerHandler:
    # объявляем так чтобы можно было не объявлять экземпляр класса, а вызывать как TimerHandler.shutdown()
    @staticmethod
    def shutdown():     # завершение работы
        if mainTimer.GetIsPaused():
            print("Closing programm...")
            CloseProgram(0)

    @staticmethod
    def start():    # нажатие на кнопку Start - запуск отсчета или принудительный переход к следующему отсчету
        global pauseButtonToggled
        print("Start countdown pressed")
        if mainTimer.GetCurrentMin() != 0 or mainTimer.GetCurrentSec() != 0:
            pauseButtonToggled = False
            if mainTimer.GetIsPaused():
                mainTimer.Resume()
                print("Resume countdown")
            else:
                mainTimer.Force()
                print("Force countdown")

    @staticmethod
    def next_mode():   # выбор режима работы
        global  currentMode, pauseButtonToggled
        if mainTimer.GetIsPaused():     # менять режим работы можно только если отсчет не идет
            pauseButtonToggled = False
            currentMode += 1   # выбираем следующий режим
            if currentMode > len(modsDict) - 1:
                currentMode = 0
            mainTimer.SetTimerList(modsDict[modsNames[currentMode]])

    @staticmethod
    def prev_mode():
        global currentMode, pauseButtonToggled
        if mainTimer.GetIsPaused():     # менять режим работы можно только если отсчет не идет
            pauseButtonToggled = False
            currentMode -= 1   # выбираем следующий режим
            if currentMode < 0:
                currentMode = len(modsDict) - 1
            mainTimer.SetTimerList(modsDict[modsNames[currentMode]])

    @staticmethod
    def pause():    # установка таймера на паузу
        global pauseButtonToggled
        print("Pause")
        if not mainTimer.GetIsPaused():     # ставим таймер на паузу, если о
            pauseButtonToggled = True
        mainTimer.Pause()

    @staticmethod
    def reset():    # сброс таймера
        global pauseButtonToggled
        if mainTimer.GetIsPaused():  # сброс доступен только если таймер не считает
            pauseButtonToggled = False
            mainTimer.SetTimerList(modsDict[modsNames[currentMode]])


    @staticmethod
    def add_minute():   # добавить минуту (только в режиме перерыва и когда таймер на паузе)
        if modsNames[currentMode] == "Перерыв" and mainTimer.GetIsPaused():
            min = mainTimer.GetCurrentMin()
            min += 1
            if min > 99:
                min = 99
            mainTimer.SetTimerList([[min, 0], ])

    @staticmethod
    def reduce_minute():   # убрать минуту (только в режиме перерыва и когда таймер на паузе)
        if modsNames[currentMode] == "Перерыв" and mainTimer.GetIsPaused():
            min = mainTimer.GetCurrentMin()
            min -= 1
            if min < 1:
                min = 1
            mainTimer.SetTimerList([[min, 0], ])


############
'''
Класс работы с GPIO Raspberry Pi. К GPIO подключены кнопки Start, Pause, Reset, Shutdown,
а также энкодер с кнопкой Select.
Все кнопки подтянуты к питанию с помощью внешнего резистора, поэтому программно подтягивать их никуда не нужно.
'''
############


class GpioHandler(threading.Thread):    # класс отслеживающий состояние GPIO
    global currentMode, pause, finder, extremal, pauseButtonToggled

    def __init__(self):
        # задаем номера gpio для кнопок
        self.GpioStart = 4  # запуск таймера
        self.GpioPause = 3  # пауза таймера
        self.GpioReset = 2  # сброс таймера
        self.GpioSelect = 17    # выбор режима работы
        self.GpioShutdown = 23  # выключение малины
        _chan_list = [self.GpioSelect, self.GpioStart, self.GpioPause,
                     self.GpioReset, self.GpioShutdown]
        _bouncetime = 200   # сколько мс ждем устаканивания дребезга
        GPIO.setmode(GPIO.BCM)  # выбор нумерации пинов - задаем напрямую
        GPIO.setup(_chan_list, GPIO.IN)   # устанавливаем все пины на вход
        # цепляем callback функции к изменению состояния пинов
        # применение - номер пина, что пытаемся ловить, функция - callback, сколько ждать устаканивания дребезга
        GPIO.add_event_detect(self.GpioSelect, GPIO.FALLING, callback=self.HandlerSelect, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioStart, GPIO.FALLING, callback=self.HandlerStart, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioPause, GPIO.FALLING, callback=self.HandlerPause, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioReset, GPIO.FALLING, callback=self.HandlerReset, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioShutdown, GPIO.FALLING, callback=self.HandlerShutdown, bouncetime=_bouncetime)
        self.isRunning = False  # флаг, что мы все еще слушаем GPIO (нужен для корректного завершения потока)
        print("GPIO handler is created")
        threading.Thread.__init__(self, daemon=True)

    def HandlerShutdown(self, channel):     # обработка нажатия на кнопку выключения
        os.system("sudo shutdown -h now")  # выключаем raspberry pi

    def HandlerStart(self, channel):    # обработка нажатия на кнопку Start
        TimerHandler.start()

    def HandlerSelect(self, channel):   # обработка выбора режима
        TimerHandler.next_mode()

    def HandlerPause(self, channel):    # обработка нажатия на кнопку Pause
        TimerHandler.pause()

    def HandlerReset(self, channel):    # обработка нажатия на кнопку Reset
        TimerHandler.reset()

    def Exit(self):
        # print("Stopping GPIO handler...")
        self.isRunning = False
        GPIO.cleanup()
        print("GPIO handler stopped")

############
'''
Класс читающий показания энкодера в отдельном потоке. Работает непрерывно, считывает состояние каналов энкодера
около 1000 раз в секунду. Работает только в режиме просто обратного отсчета.
'''
############


class EncoderCounter(threading.Thread):
    def __init__(self):
        self.GpioEncA = 27  # пины - каналы энкодера
        self.GpioEncB = 22
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.GpioEncA, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # каналы энкодера  на вход
        GPIO.setup(self.GpioEncB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.isRunning = False  # флаг для корректного завершения треда
        self.encAprev = GPIO.input(self.GpioEncA)   # записываем начальные состояния каналов
        self.encA = GPIO.input(self.GpioEncA)
        self.encB = GPIO.input(self.GpioEncB)
        print("Encoder handler is created")
        threading.Thread.__init__(self, daemon=True)

    def Update(self):   # функция, которая читает состояние энкодера
        while self.isRunning:
            self.encA = GPIO.input(self.GpioEncA)   # считываем новые состояния
            self.encB = GPIO.input(self.GpioEncB)
            # изменяем что-то, только если таймер не запущен и в нужном режиме
            if  modsNames[currentMode] == "Перерыв" and mainTimer.GetIsPaused():
                if self.encA != self.encAprev:  # если изменилось состояние на первом канале
                    if self.encB != self.encA:  # и оно не совпадает со второым каналом
                        TimerHandler.add_minute()
                    else:   # если совпадает со вторым каналом
                        TimerHandler.reduce_minute()
                self.encAprev = self.encA   # записываем новое "предыдущее" состояние первого канала
            time.sleep(0.001)   # засыпаем
        print("Encoder handler stopped")

    def run(self):
        self.isRunning = True
        self.Update()

    def Exit(self):     # закрытие треда
        # print("Stopping encoder listener...")
        self.isRunning = False


if keys:    # если есть библиотека для работы с клавиатурой
    class EscException(Exception): pass     # исключение по которому будем закрывать программу

    def on_release(key):
        global currentMode, pause, finder, pauseButtonToggled
        try:
            if key.char == 'p' or key.char == 'P' or key.char == 'з' or key.char == 'З':  # клавиша P - пауза таймера
                TimerHandler.pause()

        except AttributeError:
            if key == keyboard.Key.space:  # клавиша Space - запуск
                TimerHandler.start()

            elif key == keyboard.Key.backspace:     # клавиша backspace - сброс таймера
                TimerHandler.reset()

            elif key == keyboard.Key.left:  # смена режима - стрелки право-лево
                TimerHandler.prev_mode()

            elif key == keyboard.Key.right:
                TimerHandler.next_mode()

            elif key == keyboard.Key.up:  # увеличить время на паузе
                TimerHandler.add_minute()

            elif key == keyboard.Key.down:    # уменьшить время на паузе
                TimerHandler.reduce_minute()

            elif key == keyboard.Key.esc:   # закрытие программы
                TimerHandler.shutdown()
                raise EscException(key)  # дергаем исключение, которое закроет программу


def CloseProgram(w):    # при закрытии программы останавливаем таймеры и закрываем окно
    try:
        mainTimer.Exit()    # закрываем таймеры
    except NameError:
        print("No Main timer to stop")
    try:
        redTimer.Exit()
    except NameError:
        print("No Red timer to stop")
    try:
        greenTimer.Exit()
    except NameError:
        print("No Green timer to stop")
    try:
        player.Exit()   # закрываем воспроизведение музыки
    except NameError:
        print("No player to stop")
    eventAirHorn.clear()    # очищаем все события
    eventGongLaugh.clear()
    eventBeep.clear()
    eventBleep.clear()
    eventGong1.clear()
    eventGong2.clear()
    try:
        pult.Exit()
    except NameError:
        print("No pult handler to stop")
    try:
        encoderHandler.Exit()   # закрываем опрос энкодера
        gpioHandler.Exit()  # очищаем GPIO

    except NameError:
        print("No GPIO to close")
    Gtk.main_quit()     # закрываем графическое окно
    print("Program closed")

mainWindow = MainWindow()   # создаем объект класса главного окна
gtkRunner = GtkRunner()     # объект для запуска GTK в отдельном потоке

# создаем таймеры, минуты, секунды, какой таймер
mainTimer = TimerClass(modsDict[modsNames[currentMode]], 'main')   # тут главный

player = PlayMusic()    # создаем объект класса проигрывания музыки
# pult = PultHandler()    # создаем обработчик пульта

if gpio:    # если есть GPIO
    gpioHandler = GpioHandler()     # обработчик нажатий на кнопки
    encoderHandler = EncoderCounter()   # и энкодера
    encoderHandler.start()

gtkRunner.start()   # запускаем GTK
mainTimer.start()   # запускаем таймеры
player.start()  # запускаем проигрыватель музыки
# pult.start()    # запускаем обработчик пульта

# gtkRunner.join()    # цепляем треды к основному потоку
# mainTimer.Resume()
if keys:    # если есть библиотека для работы с клавиатурой
    with keyboard.Listener(on_release=on_release) as listener:  # класс для мониторинга клавиатуры
        try:
            listener.join()
        except EscException as e:    # если срабатывает исключение
            print("Exception happened")
            CloseProgram(0)  # закрываем программу