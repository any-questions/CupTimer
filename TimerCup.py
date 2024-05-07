#!/usr/bin/env python3
import time         # для таймеров
import threading    # для тредов
import gi           # для gui
import cairo        # для визуальных эффектов
import os           # чтобы иметь возможность слать команды os
import simpleaudio as sa  # для аудио
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, GLib, Gdk

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
modsDict = {"Перерыв":              [[10, 0], ],        # особый режим где нужен всего 1 таймер
            "Искатель":             [[3, 0], [10, 0]],
            "Экстремал":            [[7, 0], [10, 0]],
#            "Экстремал Pro 1.0":    [[7, 0], [10, 0]],
            "Искатель Мини":        [[3, 0], [5, 0]],
#            "Агро-I":               [[3, 0], [8, 0]],
#            "Отборочный тур":       [[5, 0], [5, 0]]    # этот режим работы должен крутиться до бесконечности
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
textCup = "Кубок РТК" 

pattern = '{0:02d}:{1:02d}'     # формат вывода строки

eventAttemptStart = threading.Event()   # события, которыми будем вызывать проигрывание аудио
eventAttemptEnd = threading.Event()

pauseButtonToggled = False     # флаг, что нажали на кнопку pause


class MainWindow(Gtk.Window):
    """Класс основного окна, на котором все отрисовывается"""
    global currentMode

    def __init__(self):
        super(MainWindow, self).__init__()  # переопределяем init
        self.set_title("Timer")                 # заголовок окна
        # self.set_size_request(800, 600)
        self.fullscreen()                       # растягиваем на весь экран
        self.connect("destroy", closeProgram)   # связываем закрытие окна с функцией заверщеия программы
        self._drawArea = Gtk.DrawingArea()      # создаем drawing area на которой будем рисовать приложение
        self._drawArea.connect("draw", self.expose)   # связываем событие с функцией перерисовки содержимого
        self.add(self._drawArea)                # добавляем drawing area в окно приложения
        self._isRunning = True                  # флаг, что программа работает
        GLib.timeout_add(200, self.onTimer)     # таймер по которому каждые 200 мс будем перерисовывать содержимое
        self.show_all()                         # отображаем окно
        cursor = Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)    # скрываем курсор
        self.get_window().set_cursor(cursor)
        self._currentTime = [0, 0]

        # служебные переменные (здесь обнулены, т.к. они обновляются при изменении размера окна, а это происходит
        # не сразу при запуске)
        self._width = 0
        self._height = 0
        self._lineHeight = 0
        self._size = 0              # текущий размер текста
        self._blinkCounter = 0      # счетчик, по которому будет мигать текст главного таймера в режиме паузы

        print("Main window is created")

    def onTimer(self):
        """Метод, который по таймеру вызывает событие на перерисовку"""
        if not self._isRunning:
            return False

        self._drawArea.queue_draw()    # событие на перерисовку
        return True

    def drawText(self, text, size, coord_x, coord_y, cr, color=(1, 1, 1)):
        """
        Отрисовка одной строки текста
        :param text: отображаемый текст
        :param size: размер текста
        :param coord_x: координата X центра текста
        :param coord_y: координата Y центра текста
        :param cr: служебный модуль cairo который надо передавать в функцию
        :param color: цвет текста, по умолчанию - белый, передается как кортеж (r, g, b)
        """
        cr.set_font_size(size)
        cr.set_source_rgb(color[0], color[1], color[2])
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents(text)
        cr.move_to(coord_x - dx / 2, coord_y + filledHeight / 2)
        '''
        Пояснение: text_extents возвращает параметры того, сколько будет занимать на экране текст, если его выводить
        функцией show_text. dx, dy - на сколько сместится курсор по оси X, и Y соответственно, filledWidth, 
        filledHeight - ширина и высота закрашиваемых пикселей (это важно). Если подсунуть в текст одни пробелы - 
        filledWidth и filledHeight будут 0, но dx - нет. Тоже касается выбранного шрифта Digital Dismay, если печатать 
        им цифру 1 значения dx и filledWidth будут разными. Это приводит к сдвигам текста когда пытаемся вывести на 
        экран 10:00 и 09:59. 
        Поэтому мы смотрим на смещение курсора и на высоту текста при печати. (Скорее всего я написал довольно невнятно,
        поэтому, вот пример:
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents("10:00")
        print("filledWidth = %d, filledHeight = %d, dx = %d, dy = %d" % (filledWidth, filledHeight, dx, dy))
        (x, y, filledWidth, filledHeight, dx, dy) = cr.text_extents("09:59")
        print("filledWidth = %d, filledHeight = %d, dx = %d, dy = %d" % (filledWidth, filledHeight, dx, dy))
        '''
        cr.show_text(text)

    def expose(self, widget, cr):
        """Функция перерисовки содержимого окна"""
        self._width = self.get_size()[0]        # получаем значения ширины и высоты
        self._height = self.get_size()[1]
        self._lineHeight = self._height / 5     # задаем высоту строки = 1/5  высоты экрана
        textHeight = self._lineHeight * 0.8
        textPos = self._lineHeight / 3

        cr.set_source_rgb(0, 0, 0)              # фон красим в черный
        cr.paint()                              # заливаем фон
        self._currentTime = mainTimer.getCurrentTime()

        # выставляем параметры шрифта
        # если тикают последние 10 секунд главного таймера (причем этот таймер последний)
        # не касается режимов Перерыв и бесконечных
        if mainTimer.finalCountdown is True and mainTimer.getTimerListLen() == 1 \
                and not modsNames[currentMode] == "Перерыв" and not modsNames[currentMode] in infinite:
            # если дотикал до конца таймер попытки - выводим соответствующий текст "Попытка закончена"
            if self._currentTime[0] == 0 and self._currentTime[1] == 0:
                time.sleep(0.5)     # ждем чуть чуть чтобы ноль явно повисел
                cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.drawText(textAttemptEnd, self._lineHeight, self._width/2, self._height/2, cr)
            else:   # если нет - выводим большие красные цифры последних секунд отсчета
                cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.drawText(mainTimer.getTimer(), self._lineHeight * 4,
                              self._width / 2, self._height / 2, cr, (1, 0, 0))

        else:   # если не идет обратный отсчет последних секунд
            # выставляем параметры шрифта
            cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            self.drawText(modsNames[currentMode], textHeight, self._width/2, textPos, cr)  # пишем имя текущего режима
            self.drawText(textCup, textHeight*1.1, self._width/2, self._lineHeight * 4.2, cr)  # пишем имя текущего режима

            if mainTimer.getTimerListLen() > 1:     # если есть еще доп таймеры в списке - добавляем фразу "подготовка"
                self.drawText(textPreparing, self._lineHeight/2, self._width/2, self._lineHeight, cr)
            elif modsNames[currentMode] in infinite:    # для бесконечных режимов пишем также фразу "попытка"
                self.drawText(textAttempt, self._lineHeight/2, self._width/2, self._lineHeight, cr)

            cr.select_font_face("Digital Dismay", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            # вывод главного таймера, если осталось 10 сек - рисуется красным(только для реджимов перерыв и бесконечных)
            if mainTimer.finalCountdown is True:
                self.drawText(mainTimer.getTimer(), self._lineHeight * 3, self._width / 2,
                              self._lineHeight * 2.5, cr, (1, 0, 0))
            else:
                self.drawText(mainTimer.getTimer(), self._lineHeight * 3, self._width / 2, self._lineHeight * 2.5, cr)

            if pauseButtonToggled and self._blinkCounter//5 != 0:
                cr.select_font_face("GOST type A", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                self.drawText(textAdditional, self._lineHeight, self._width/2, self._lineHeight*4, cr)

        self._blinkCounter += 1
        if self._blinkCounter > 9:
            self._blinkCounter = 0


############
'''
Класс для работы таймера. Параметрами являются список таймеров, который включает в себя:
минуты, секунды для нескольких таймеров подряд, и тип таймера - главный, красный или зеленый.
При работе таймера флаг isRunning позволяет треду работать, флаг isPaused - ставит текущий таймер на паузу.
Если в списке таймеров больше одного элемента - они отсчитываются по очереди,
если он только один - таймер останавливается.
после того как дотикает до конца.
'''
############


class TimerClass(threading.Thread):
    """Класс для работы таймера"""
    global eventAttemptStart, eventAttemptEnd

    def __init__(self, timerList: list, timer: str):
        """
        Конструктор класса
        :param timerList: список таймеров
        :param timer: тип таймера 'main', 'green' или 'red', нужен для отрисовки и отыгрываемого звука. Пока
        задействован только 'main'.
        """
        self.timerList = []             # список таймеров
        self.currentTime = [0, 0]       # записываем время: мин, сек
        self.setTimerList(timerList)    # записываем список таймеров и текущее время
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        self.timer = timer              # тип таймера
        self.isRunning = False          # флаг, чтобы тред работал
        self.paused = True              # флаг, чтобы ставить таймер на паузу
        self.finalCountdown = False     # флаг, что идет отсчет последних 5 секунд
        print(timer, "timer is created")
        threading.Thread.__init__(self, daemon=True)

    def update(self):
        """Функция обновления времени таймера. Запускается threading."""
        while self.isRunning:           # пока тред запущен
            if not self.isPaused():         # если таймер не на паузе

                self.currentTime[1] -= 1            # вычитаем одну секунду
                if self.currentTime[1] < 0:         # если секунды кончились,
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
                        # если таймеру надо крутиться до бесконечности
                        if self.timer == 'main' and modsNames[currentMode] in infinite:
                            self.setTimerList(modsDict[modsNames[currentMode]])     # обновляем список таймеров
                            self.resume()                                           # и сразу запускаем таймер дальше
                        else:
                            self.pause()        # если это был последний таймер - останавливаем отсчет
                    if self.timer == 'main' and modsNames[currentMode] in infinite:
                        if len(self.timerList) > 1:
                            eventAttemptEnd.set()
                elif self.currentTime[0] == 0 and self.currentTime[1] <= 10:  # если осталось тикать 10 секунд
                    self.finalCountdown = True  # поднимаем флаг, чтобы окно перерисовывалось по другому
                    ##########################
                    '''
                    КОСТЫЛЬ. ТАК ДЕЛАТЬ НЕ НАДО.
                    '''
                    ##########################
                    # за 4 секунды до конца отсчета таймера на подготовку запускаем аудио.
                    # потому что файл длится 4 секунды
                    if self.timer == 'main' and modsNames[currentMode] in infinite \
                            and self.currentTime[1] == 4 and len(self.timerList) > 1:
                        print("Attempt start!")
                        eventAttemptStart.set()

                time.sleep(1)   # останавливаем тред на секунду
        print(self.timer, "timer stopped")

    def run(self):
        """Функция для treading. Запускает работу таймера в отдельном потоке."""
        self.isRunning = True
        self.update()

    def setTimerList(self, timerList: list):   # функция задания нового списка таймеров
        """
        Задание нового списка таймеров
        :param timerList: список таймеров, например [[7, 0], [10, 0]]
        """
        self.pause()        # на всякий случай ставим на паузу
        self.timerList = timerList.copy()
        self.currentTime = [self.timerList[0][0], self.timerList[0][1]]
        self.finalCountdown = False

    def pause(self):
        """Поставить таймер на паузу"""
        self.paused = True

    def resume(self):
        """Продолжить отсчет таймера"""
        self.paused = False

    def isPaused(self):  # получить состояние флага паузы
        """Узнать, стоит ли таймер на паузе"""
        return self.paused

    def force(self):
        """Принудительно завершить отсчет текущего таймера, чтобы перейти к следующему"""
        if not (self.currentTime[0] == 0 and self.currentTime[1] == 0):
            self.pause()
            self.currentTime[0] = 0
            self.currentTime[1] = 5
            self.finalCountdown = True
            self.resume()

    def exit(self):
        """Завершить тред"""
        self.isRunning = False

    def getCurrentTime(self):
        """
        Возвращает текущее время таймера списком
        :return: список, например [1, 2]
        """
        return self.currentTime

    def getCurrentMin(self):
        """Возвращает текущее значение минут"""
        return self.currentTime[0]

    def getCurrentSec(self):
        """Возвращает текущее значение секунд"""
        return self.currentTime[1]

    def getTimerListLen(self):
        """Возвращает число таймеров, которое осталось дотикать"""
        return len(self.timerList)

    def getTimer(self):
        """Возвращает текущее время строкой, в формате паттерна"""
        self.timeString = pattern.format(self.currentTime[0], self.currentTime[1])  # записываем время в паттерн
        return self.timeString


######
'''
Класс для воспроизведения звуковых сигналов. Работает в отдельном потоке. По сути являет собой бесконечный цикл -
обработчик событий. События глобальные, выставляются классом таймера. Когда срабатывает событие - проигрывается
соответствующий звук и событие сбрасывается.
'''
######


class PlayMusic(threading.Thread):
    """Класс для воспроизведения мелодий"""
    def __init__(self):
        """Конструктор класса воспроизведения мелодий"""
        dirpath = os.getcwd()   # получаем расположение текущей папки
        foldername = os.path.basename(dirpath)  # получаем имя текущей папки
        # указываем пути к мелодиям, которые будем проигрывать
        if foldername == "CupTimer":
            print("Path to audio: sounds/*.wav")
            self.attemptStart = sa.WaveObject.from_wave_file("sounds/attempt_start_beautiful.wav")
            self.attemptEnd = sa.WaveObject.from_wave_file("sounds/attempt_end_beautiful.wav")
        else:
            print("Path to audio:"+dirpath+"/CupTimer/sounds/*.wav")
            self.attemptStart = sa.WaveObject.from_wave_file(dirpath+"/CupTimer/sounds/attempt_start_beautiful.wav")
            self.attemptEnd = sa.WaveObject.from_wave_file(dirpath + "/CupTimer/sounds/attempt_end_beautiful.wav")
        self.isRunning = False
        threading.Thread.__init__(self, daemon=True)     # наследование функций треда
        print("Audio player is created")

    def __del__(self):
        """Деструктор класса воспроизведения мелодий, останавливает флаг треда"""
        self.isRunning = False

    def run(self):
        """Функция для threading. Запуск обработчика событий для воспроизведения звука в отдельном потоке"""
        self.isRunning = True
        self.handler()

    def handler(self):
        """Обработчик событий - events, по которым воспроизводится звук"""
        while self.isRunning is True:   # работает пока поднят флаг
            if eventAttemptStart.is_set():
                eventAttemptStart.clear()
                self.attemptStart.play()

            elif eventAttemptEnd.is_set():
                eventAttemptEnd.clear()
                self.attemptEnd.play()
            time.sleep(0.001)
        print("Audio player stopped")

    def exit(self):
        self.isRunning = False


class GtkRunner(threading.Thread):
    """Служебный класс для запуска Gtk в отдельном потоке."""
    def __init__(self):   # запуск гтк в отдельном треде
        threading.Thread.__init__(self)

    def run(self):
        Gtk.main()


############
'''
Тут был класс для общения с UART и обработки входящих сообщений с пультов управления таймером.
Ищите в истории коммитов. Например тут: 0405c670526251198eb133b81a51cf4e19aa96bc
'''
############


class TimerHandler:
    """Класс для работы с главным таймером. По сути интерфейс, к которому будут обращаться обработчики нажатий на
    кнопки и на клавиатуру"""
    # объявляем методы статическими, чтобы можно было не объявлять экземпляр класса,
    # а вызывать как TimerHandler.shutdown()
    @staticmethod
    def shutdown():
        """Завершение работы программы"""
        if mainTimer.isPaused():
            print("Closing programm...")
            closeProgram(0)

    @staticmethod
    def start():
        """Запуск отсчета, или принудительное завершение таймера"""
        global pauseButtonToggled
        print("Start countdown pressed")
        if mainTimer.getCurrentMin() != 0 or mainTimer.getCurrentSec() != 0:
            pauseButtonToggled = False
            if mainTimer.isPaused():
                mainTimer.resume()
                print("resume countdown")
            else:
                mainTimer.force()
                print("force countdown")

    @staticmethod
    def nextMode():
        """Выбор режима работы"""
        global currentMode, pauseButtonToggled
        if mainTimer.isPaused():        # менять режим работы можно только если отсчет не идет
            pauseButtonToggled = False
            currentMode += 1            # выбираем следующий режим
            if currentMode > len(modsDict) - 1:
                currentMode = 0         # зацикливаем
            mainTimer.setTimerList(modsDict[modsNames[currentMode]])

    @staticmethod
    def prevMode():
        """Выбор режима работы (в обратную сторону, удобно при использовании клавиатуры)"""
        global currentMode, pauseButtonToggled
        if mainTimer.isPaused():        # менять режим работы можно только если отсчет не идет
            pauseButtonToggled = False
            currentMode -= 1            # выбираем следующий режим
            if currentMode < 0:         # зацикливаем
                currentMode = len(modsDict) - 1
            mainTimer.setTimerList(modsDict[modsNames[currentMode]])

    @staticmethod
    def pause():
        """Поставить таймер на паузу"""
        global pauseButtonToggled
        print("pause")
        if not mainTimer.isPaused():     # ставим таймер на паузу, если о
            pauseButtonToggled = True
        mainTimer.pause()

    @staticmethod
    def reset():
        """Сбросить таймер"""
        global pauseButtonToggled
        if mainTimer.isPaused():        # сброс доступен только если таймер не считает
            pauseButtonToggled = False
            mainTimer.setTimerList(modsDict[modsNames[currentMode]])

    @staticmethod
    def addMinute():
        """Добавить минуту (только в режиме перерыва и когда таймер на паузе)"""
        if modsNames[currentMode] == "Перерыв" and mainTimer.isPaused():
            minute = mainTimer.getCurrentMin()
            minute += 1
            if minute > 180:
                minute = 180
            mainTimer.setTimerList([[minute, 0], ])

    @staticmethod
    def reduceMinute():
        """Отнять минуту (только в режиме перерыва и когда таймер на паузе)"""
        if modsNames[currentMode] == "Перерыв" and mainTimer.isPaused():
            minute = mainTimer.getCurrentMin()
            minute -= 1
            if minute < 1:
                minute = 1
            mainTimer.setTimerList([[minute, 0], ])


############
'''
Класс работы с GPIO Raspberry Pi. К GPIO подключены кнопки Start, pause, Reset, Shutdown,
а также энкодер с кнопкой Select.
Все кнопки подтянуты к питанию с помощью внешнего резистора, поэтому программно подтягивать их никуда не нужно.
'''
############


class GpioHandler(threading.Thread):    # класс отслеживающий состояние GPIO
    """Класс для обработки GPIO"""
    global currentMode, pauseButtonToggled

    def __init__(self):
        # задаем номера gpio для кнопок
        self.GpioStart = 4      # запуск таймера
        self.GpioPause = 3      # пауза таймера
        self.GpioReset = 2      # сброс таймера
        self.GpioSelect = 17    # выбор режима работы
        self.GpioShutdown = 23  # выключение малины
        _chan_list = [self.GpioSelect, self.GpioStart, self.GpioPause,
                      self.GpioReset, self.GpioShutdown]
        _bouncetime = 200       # сколько мс ждем устаканивания дребезга
        GPIO.setmode(GPIO.BCM)  # выбор нумерации пинов - задаем напрямую
        GPIO.setup(_chan_list, GPIO.IN)   # устанавливаем все пины на вход

        # цепляем callback функции к изменению состояния пинов
        # применение - номер пина, что пытаемся ловить, функция - callback, сколько ждать устаканивания дребезга
        GPIO.add_event_detect(self.GpioSelect, GPIO.FALLING, callback=self.handlerSelect, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioStart, GPIO.FALLING, callback=self.handlerStart, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioPause, GPIO.FALLING, callback=self.handlerPause, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioReset, GPIO.FALLING, callback=self.handlerReset, bouncetime=_bouncetime)
        GPIO.add_event_detect(self.GpioShutdown, GPIO.FALLING, callback=self.handlerShutdown, bouncetime=_bouncetime)
        self.isRunning = False  # флаг, что мы все еще слушаем GPIO (нужен для корректного завершения потока)
        print("GPIO handler is created")
        threading.Thread.__init__(self, daemon=True)

    def handlerShutdown(self, channel):
        """Обработка нажатия на кнопку выключения"""
        os.system("sudo shutdown -h now")  # выключаем raspberry pi

    def handlerStart(self, channel):
        """Обработка нажатия на кнопку Start"""
        TimerHandler.start()

    def handlerSelect(self, channel):
        """Обработка выбора режима"""
        TimerHandler.nextMode()

    def handlerPause(self, channel):
        """Обработка нажатия на кнопку Pause"""
        TimerHandler.pause()

    def handlerReset(self, channel):
        """Обработка нажатия на кнопку Reset"""
        TimerHandler.reset()

    def exit(self):
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
    """Класс, читающий показания энкодера в отдельном потоке, считывает состояние примерно 1000 раз в секунду."""
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

    def update(self):
        """Функция, обновляющая текущее состояние энкодера"""
        while self.isRunning:
            self.encA = GPIO.input(self.GpioEncA)   # считываем новые состояния
            self.encB = GPIO.input(self.GpioEncB)
            # изменяем что-то, только если таймер не запущен, и в нужном режиме
            if modsNames[currentMode] == "Перерыв" and mainTimer.isPaused():
                if self.encA != self.encAprev:      # если изменилось состояние на первом канале
                    if self.encB != self.encA:      # и оно не совпадает со второым каналом
                        TimerHandler.addMinute()
                    else:                           # если совпадает со вторым каналом
                        TimerHandler.reduceMinute()
                self.encAprev = self.encA           # записываем новое "предыдущее" состояние первого канала
            time.sleep(0.001)                       # засыпаем
        print("Encoder handler stopped")

    def run(self):
        """Метод для threading. Запускает работу класса в отдельном потоке"""
        self.isRunning = True
        self.update()

    def exit(self):
        """Функция для остановки треда"""
        # print("Stopping encoder listener...")
        self.isRunning = False


if keys:    # если есть библиотека для работы с клавиатурой
    class EscException(Exception):  # исключение по которому будем закрывать программу
        pass

    def on_release(key):
        global currentMode, pauseButtonToggled
        try:
            if key.char == 'p' or key.char == 'P' or key.char == 'з' or key.char == 'З':  # клавиша P - пауза таймера
                TimerHandler.pause()

        except AttributeError:
            if key == keyboard.Key.space:           # клавиша Space - запуск
                TimerHandler.start()

            elif key == keyboard.Key.backspace:     # клавиша backspace - сброс таймера
                TimerHandler.reset()

            elif key == keyboard.Key.left:          # смена режима - стрелки право-лево
                TimerHandler.prevMode()

            elif key == keyboard.Key.right:
                TimerHandler.nextMode()

            elif key == keyboard.Key.up:            # увеличить время на паузе
                TimerHandler.addMinute()

            elif key == keyboard.Key.down:          # уменьшить время на паузе
                TimerHandler.reduceMinute()

            elif key == keyboard.Key.esc:           # закрытие программы
                TimerHandler.shutdown()
                raise EscException(key)             # дергаем исключение, которое закроет программу


def closeProgram(w):            # при закрытии программы останавливаем таймеры и закрываем окно
    try:
        mainTimer.exit()        # закрываем таймеры
    except NameError:
        print("No Main timer to stop")
    try:
        player.exit()           # закрываем воспроизведение музыки
    except NameError:
        print("No player to stop")
    eventAttemptStart.clear()   # очищаем все события
    eventAttemptEnd.clear()
    try:
        encoderHandler.exit()   # закрываем опрос энкодера
        gpioHandler.exit()      # очищаем GPIO

    except NameError:
        print("No GPIO to close")
    Gtk.main_quit()             # закрываем графическое окно
    print("Program closed")


mainWindow = MainWindow()       # создаем объект класса главного окна
gtkRunner = GtkRunner()         # объект для запуска GTK в отдельном потоке

# создаем таймеры, минуты, секунды, какой таймер
mainTimer = TimerClass(modsDict[modsNames[currentMode]], 'main')

player = PlayMusic()    # создаем объект класса проигрывания музыки

if gpio:    # если есть GPIO
    gpioHandler = GpioHandler()         # обработчик нажатий на кнопки
    encoderHandler = EncoderCounter()   # и энкодера
    encoderHandler.start()

gtkRunner.start()   # запускаем GTK
mainTimer.start()   # запускаем таймеры
player.start()      # запускаем проигрыватель музыки

if keys:    # если есть библиотека для работы с клавиатурой
    with keyboard.Listener(on_release=on_release) as listener:  # класс для мониторинга клавиатуры
        try:
            listener.join()
        except EscException as e:       # если срабатывает исключение
            print("Exception happened")
            closeProgram(0)             # закрываем программу
