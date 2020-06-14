
import subprocess
import sys
import inspect
import functools




class SafeExecute:

    def __init__(self, is_memory=True, group_name=None):
        print("__init__")
        self.group_name = group_name
        self.is_memory = is_memory

    def __call__(self, *args0, **kwargs0):
        def func(*args1, **kwargs1):
            instance = args1[0]
            f = args0[0]
            try:
                res = f(*args1, **kwargs1)
                d = {"operation": f.__name__, "dt_start": 0, "duration": 0, "error": None, "output": res}
                if self.is_memory:
                    instance.memory[f.__name__] = d
                return d
            except Exception as e:
                d = {"operation": f.__name__, "dt_start": 0, "duration": 0, "error": str(e), "output": None}
                if self.is_memory:
                    instance.memory[f.__name__] = d
                return d
        func.wrapped = True
        func.group_name = self.group_name
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

