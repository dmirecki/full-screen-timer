import Tkinter
from Tkinter import *
import argparse
import datetime
import pyaudio
import wave
from abc import ABCMeta, abstractmethod

import tkFont


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


class FullScreenApp(object):
    timer = None
    master = None

    def __init__(self, start_minutes, start_seconds):
        self.master = Tkinter.Tk()

        self._geom = '200x200+0+0'

        self.configure()
        self.bind_keys()

        self.timer = Timer(self.master, start_minutes, start_seconds)

    def run(self):
        self.master.mainloop()

    def configure(self):
        self.master.configure(background=Timer.BACKGROUND_COLOR, cursor='none')
        w, h = self.master.winfo_screenwidth(), self.master.winfo_screenheight()
        self.master.overrideredirect(1)
        self.master.geometry("%dx%d+0+0" % (w, h))

    def bind_keys(self):
        self.master.bind('<Escape>', self.exit)
        self.master.bind('<space>', self.start_time)
        self.master.bind('<r>', self.reset_timer)
        self.master.bind('<p>', self.pause)
        self.master.bind('<G>', self.toggle_geom)

    def exit(self, event):
        sys.exit()

    def start_time(self, event):
        self.timer.start()

    def reset_timer(self, event):
        self.timer.reset()

    def pause(self, event):
        if self.timer.state.is_pause():
            self.timer.cancel_pause()
        else:
            self.timer.pause()

    def toggle_geom(self, event):
        geom = self.master.winfo_geometry()
        self.master.geometry(self._geom)
        self._geom = geom


class AbstractTimerState:
    __metaclass__ = ABCMeta

    startTime = None
    fullStartTime = None
    pauseStartTime = None
    pauses = datetime.timedelta(0)

    @staticmethod
    def timedelta_format(timedelta, format):
        dt = datetime.datetime(2000, 1, 1) + timedelta
        return dt.strftime('%M:%S')

    @abstractmethod
    def update(self, timer): pass

    @abstractmethod
    def count_down(self, timer): pass

    @abstractmethod
    def pause(self): pass

    @abstractmethod
    def cancel_pause(self): pass

    @abstractmethod
    def reset(self): pass

    def is_pause(self):
        return FALSE


@Singleton
class ReadyState(AbstractTimerState):
    def count_down(self, timer):
        return StartingState.Instance().count_down(timer)

    def cancel_pause(self):
        return self

    def reset(self):
        return self

    def __init__(self):
        pass

    def update(self, timer):
        timer.configure(text=AbstractTimerState.timedelta_format(AbstractTimerState.startTime, '%M:%S'))
        return self

    def pause(self):
        return self


@Singleton
class CountingDownState(AbstractTimerState):
    def count_down(self, timer):
        return self

    def cancel_pause(self):
        return self

    def reset(self):
        return ReadyState.Instance()

    def __init__(self):
        pass

    def update(self, timer):
        diff = self.get_time()

        if diff <= datetime.timedelta(0):
            # self.setTime(datetime.timedelta(0))
            # self.playFinishSound()
            return RingingState.Instance().update(timer)

        timer.configure(text=AbstractTimerState.timedelta_format(diff, '%M:%S'))
        return self

    def pause(self):
        AbstractTimerState.pauseStartTime = datetime.datetime.now()
        return PauseState.Instance()

    def get_time(self):
        now = datetime.datetime.now()
        diff = now - AbstractTimerState.fullStartTime
        return AbstractTimerState.startTime - diff + AbstractTimerState.pauses


@Singleton
class PauseState(AbstractTimerState):
    def count_down(self, timer):
        return CountingDownState.Instance()

    def cancel_pause(self):
        AbstractTimerState.pauses += datetime.datetime.now() - AbstractTimerState.pauseStartTime
        return CountingDownState.Instance()

    def reset(self):
        return ReadyState.Instance()

    def __init__(self):
        pass

    def update(self, timer):
        return self

    def pause(self):
        return self

    def is_pause(self):
        return TRUE


@Singleton
class ZerosState(AbstractTimerState):
    def count_down(self, timer):
        return self

    def cancel_pause(self):
        return self

    def reset(self):
        return ReadyState.Instance()

    def __init__(self):
        pass

    def update(self, timer):
        timer.configure(text=AbstractTimerState.timedelta_format(datetime.timedelta(0), '%M:%S'))
        return self

    def pause(self):
        return self


@Singleton
class RingingState(AbstractTimerState):
    sound = "alarm.wav"

    def count_down(self, timer):
        return self

    def cancel_pause(self):
        return self

    def reset(self):
        return ReadyState.Instance()

    def __init__(self):
        pass

    def update(self, timer):
        self.playFinishSound()
        return ZerosState.Instance()

    def pause(self):
        return self

    def playFinishSound(self):
        chunk = 1024

        f = wave.open(self.sound,"rb")
        p = pyaudio.PyAudio()
        stream = p.open(format = p.get_format_from_width(f.getsampwidth()),
                        channels = f.getnchannels(),
                        rate = f.getframerate(),
                        output = True)
        data = f.readframes(chunk)

        while data != '':
            stream.write(data)
            data = f.readframes(chunk)

        stream.stop_stream()
        stream.close()

        p.terminate()

@Singleton
class StartingState(AbstractTimerState):
    def count_down(self, timer):
        AbstractTimerState.fullStartTime = datetime.datetime.now()
        AbstractTimerState.pauses = datetime.timedelta(0)
        return CountingDownState.Instance()

    def cancel_pause(self):
        return self

    def reset(self):
        return ReadyState.Instance()

    def __init__(self):
        pass

    def update(self, timer):
        return self

    def pause(self):
        return self


class Timer:
    timer = None
    state = None

    BACKGROUND_COLOR = 'black'
    FONT_COLOR = 'red'
    FONT_SIZE = 200
    FONT_FAMILY = "DS-Digital"
    REFRESHING_PERIOD = 200

    START_MILLISECONDS = 500

    def __init__(self, root, start_minutes, start_seconds):
        self.timer = Label(root, fg=self.FONT_COLOR)
        self.configure()
        AbstractTimerState.startTime = datetime.timedelta(minutes=start_minutes, seconds=start_seconds,
                                                          milliseconds=self.START_MILLISECONDS)
        self.state = ReadyState.Instance()
        self.update_time()

    def configure(self):
        self.timer.place(anchor=Tkinter.CENTER)
        self.timer.config(font=tkFont.Font(family=self.FONT_FAMILY, size=self.FONT_SIZE))
        self.timer.configure(background=self.BACKGROUND_COLOR)
        self.timer.pack(expand=True)

    def update_time(self):
        self.state = self.state.update(self.timer)
        self.timer.after(self.REFRESHING_PERIOD, self.update_time)

    def start(self):
        self.state = self.state.count_down(self.timer)

    def reset(self):
        self.state = self.state.reset()

    def pause(self):
        self.state = self.state.pause()

    def cancel_pause(self):
        self.state = self.state.cancel_pause()


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(prog="FullScreen Timer", description='')
    arg_parser.add_argument('minutes', type=int)
    arg_parser.add_argument('seconds', type=int)
    args = arg_parser.parse_args()

    FullScreenApp(start_minutes=args.minutes,
                  start_seconds=args.seconds).run()
