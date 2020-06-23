


import subprocess
import sys
import inspect
import functools
import time

from uuid import uuid1
import logging
from datetime import datetime
import os


class Log:

    def __init__(self, log_source, log_dir, log_level):
        self.log_dir = log_dir
        self.log_file_prefix = log_source

        self.logger = logging.getLogger(log_source)
        self.dt = datetime.now()

        self.set_log_file(file_path=self.get_log_file_path(self.dt))
        self.logger.setLevel(self.log_level_of_str(log_level))

        # stdo = logging.StreamHandler()
        # self.logger.addHandler(stdo)

        self.uidd = str(uuid1())

    @staticmethod
    def log_level_of_str(level):
        s = level.upper()
        if s == "DEBUG":
            return logging.DEBUG
        elif s == "INFO":
            return logging.INFO
        elif s == "WARNING":
            return logging.WARNING
        elif s == "ERROR":
            return logging.ERROR
        elif s == "CRITICAL":
            return logging.CRITICAL
        else:
            return logging.INFO

    def get_log_file_path(self, dt):
        # file_path = os.path.join(self.log_dir, "{}_{}.log".format(self.log_file_prefix, datetime.strftime(dt, "%Y_%m_%d_%H_%M")))
        file_path = os.path.join(self.log_dir, "{}_{}.log".format(self.log_file_prefix, datetime.strftime(dt, "%Y_%m_%d")))
        self.logger.debug("file_path={}".format(file_path))
        return file_path

    def set_log_file(self, file_path):
        for h in self.logger.handlers:
            self.logger.removeHandler(h)
        f = logging.FileHandler(file_path)
        f.setFormatter(logging.Formatter('%(asctime)s;%(name)s;%(levelname)s;%(message)s'))
        self.logger.addHandler(f)
        stdo = logging.StreamHandler()
        self.logger.addHandler(stdo)


    def change_file(self):
        dt = datetime.now()
        if dt.day != self.dt.day:# or dt.minute != self.dt.minute:
            self.dt = dt
            file_path = self.get_log_file_path(self.dt)
            self.set_log_file(file_path)

    def debug(self, msg):
        self.change_file()
        self.logger.debug("{};{}".format(self.uidd, msg))

    def info(self, msg):
        self.change_file()
        self.logger.info("{};{}".format(self.uidd, msg))

    def warning(self, msg):
        self.change_file()
        self.logger.warning("{};{}".format(self.uidd, msg))

    def error(self, msg):
        self.change_file()
        self.logger.error("{};{}".format(self.uidd, msg))

    def critical(self, msg):
        self.change_file()
        self.logger.critical("{};{}".format(self.uidd, msg))


class Memory:

    def __init__(self, memory=None):
        self.memory = {}
        if memory is not None:
            self.memory = memory

    def set(self, key, x):
        self.memory[key] = x

    def get(self, key):
        return self.memory[key]

    def get_output(self, key):
        return self.memory[key]["output"]

    def get_error(self, key):
        return self.memory[key]["error"]

    def get_memory(self):
        return self.memory



class SafeExecute:

    def __init__(self, memory=None, log=None, key=None, get_dict_func_on_error=None, repeat=1, sleep_on_repeat=0.5):
        print("__init__")
        self.key = key
        self.memory = memory
        self.log = log
        self.get_dict_func_on_error = get_dict_func_on_error
        self.repeat = repeat
        self.sleep_on_repeat = sleep_on_repeat


    def get_obj(self, instance, s):
        li = s.split(".")
        if len(li) == 0:
            return None
        if li[0] == "self":
            li = li[1:]
        x = instance
        for name in li:
            x = getattr(x, name)
        return x

    def __call__(self, *args0, **kwargs0):
        def func(*args1, **kwargs1):
            instance = args1[0]
            f = args0[0]
            if self.key is None:
                key = (instance.__class__.__name__, f.__name__)
            else:
                key = self.key
            i = 0
            while i < self.repeat:
                try:
                    res = f(*args1, **kwargs1)
                    d = {"operation": f.__name__, "dt_start": 0, "duration": 0, "error": None, "output": res}
                    if self.log is not None:
                        # log_obj = getattr(instance, self.log[0])
                        # log_func = getattr(log_obj, self.log[1])
                        log_func = self.get_obj(instance, self.log)
                        log_func("{}({}) returned {}".format(f.__name__, args1, str(res)))
                    if self.memory is not None:
                        memory = self.get_obj(instance, self.memory)
                        memory.set(key, d)
                        return
                    else:
                        return d
                except Exception as e:
                    d = {"operation": f.__name__, "dt_start": 0, "duration": 0, "error": str(e), "output": None}
                    if self.log is not None:
                        log_func = self.get_obj(instance, self.log)
                        log_func("{}({}) error {}".format(f.__name__, args1, str(e)))
                    if i >= self.repeat - 1:
                        if self.memory is not None:
                            memory = self.get_obj(instance, self.memory)
                            memory.set(key, d)
                            return
                        else:
                            return d
                    else:
                        s = str(e).lower()
                        get_dict_func = self.get_obj(instance, self.get_dict_func_on_error)
                        d = get_dict_func()
                        li = [d[k] for k in d.keys() if s.find(k.lower())]
                        if len(li) > 0:
                            func2 = li[0]
                            try:
                                func2()
                                if self.log is not None:
                                    log_func = self.get_obj(instance, self.log)
                                    log_func("error handler {} success".format(func2.__name__))
                            except Exception as e2:
                                if self.log is not None:
                                    log_func = self.get_obj(instance, self.log)
                                    log_func("error handler {} error {}".format(func2.__name__, str(e2)))
                i += 1
                time.sleep(self.sleep_on_repeat)
        func.wrapped = True
        return func







class MemoryArgs:

    def __init__(self, *args, **kwargs):
        print("__init__")
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args0, **kwargs0):
        f = args0[0]
        def func(instance): #*args1, **kwargs1):
            args2 = [instance] + list(map(lambda x: instance.memory[x] if type(x) == str else x, self.args))
            kwargs2 = {k: instance.memory[v] for k, v in self.kwargs.items()}
            return f(*args2, **kwargs2)
        func.wrapped = True
        return func


class Transaction:

    def __init__(self):
        pass
        # print("__init__")

    def __call__(self, *args0, **kwargs0):
        f = args0[0]
        def func(instance):
            li_actions = f(instance)
            li_methods = [method_name for method_name in dir(instance)
                          if callable(getattr(instance, method_name)) and hasattr(getattr(instance, method_name), "action")]

            for d in li_actions:
                attempts = d["repeat on fail"] + 1
                method_name = d["action"]
                b = False
                while attempts > 0:
                    if method_name not in li_methods:
                        break
                    action = getattr(instance, method_name)
                    action()
                    d_res = instance.memory[method_name]
                    err = d_res["error"]
                    if err is not None:
                        li = list(map(lambda s, name: name, filter(lambda s, name: err.lower().find(s.lower()) >= 0, d["on exception"])))
                        if len(li) > 0:
                            func = getattr(instance, li[0])
                            func(instance)
                        attempts -= 1
                    else:
                        attempts = 0
                        b = True
                if not b:
                    return method_name
            return ""
        func.wrapped = True
        return func



class CircuitBot:

    def __init__(self):
        self.memory = CircuitBot.init_memory()
        self.state = CircuitBot.init_state()

    @staticmethod
    def init_memory():
        return {}

    @staticmethod
    def init_state():
        return {}


    def get_sensor_method_names(self):
        return [getattr(self, method_name) for method_name in dir(self)
                      if callable(getattr(self, method_name)) and hasattr(getattr(self, method_name), "sensor")
                      ]

    def call_sensors(self):
        li = self.get_sensor_method_names()
        for x in li:
            x()

    def get_sensors_data(self):
        li = self.get_sensor_method_names()
        d = {k: self.memory[k] for k in li}
        return d

    def step_name_of_sensors(self, d_sensor):# return transaction method name basing on sensors data
        return ""


    def log(self):
        pass


    # def step_name_of_state(self):
    #     return ""

    def execute_transaction(self, method_name):
        x = getattr(self, method_name)
        failed_method_name = x()
        if len(failed_method_name) > 1:
            pass  # log failed method


    def execute_step(self, method_name):
        x = getattr(self, method_name)
        li_txns = x()
        for name in li_txns:
            self.execute_transaction(name)


    def main_loop(self):
        while True:
            self.call_sensors()
            d = self.get_sensors_data()
            method_name = self.step_name_of_sensors(d)
            if not (method_name in dir(self) and callable(getattr(self, method_name)) and hasattr(getattr(self, method_name), "step")):
                break #log graph error
            method = getattr(self, method_name)
            method()



    @SafeExecute()
    def example_sensor(self):
        return 1

    @SafeExecute()
    @MemoryArgs("a", "b")
    def example_action(self ,a, b):
        return a / b

    @Transaction()
    def example_transaction(self):
        return [
            {"action": "func1", "on exception": [("no space", "func_clear_space")
                                            , ("file not found", "func_copy_file")
                                            ]
             ,"repeat on fail": 0
             }


            ,("func1", [("no space", "func_clear_space")
                       ,("file not found", "func_copy_file")
                       ]
             )
        ]


    def example_step(self):
        return ["example_transaction", "example_transaction2"]







    # def main_loop(self):
    #     list_wrapped_methods = [getattr(self, method_name) for method_name in dir(self)
    #                   if callable(getattr(self, method_name)) and hasattr(getattr(self, method_name), "wrapped")
    #                   ]
    #     li1 = [getattr(self, method_name) for method_name in dir(self)
    #                   if callable(getattr(self, method_name)) and hasattr(getattr(self, method_name), "step")
    #                   ]
    #     li1.sort(key=lambda x: x.order)
    #     while True:
    #         for x in li1:
    #             failed_method_name = x()
    #             if len(failed_method_name) > 1:
    #                 if failed_method_name in list_wrapped_methods:
    #                     pass # log failed method
    #                 else:
    #                     break # error in graph

