import enum

def interpret_arg(arg, arg_type, name, *args, **kwargs):
    if type(arg) == arg_type:
        return arg
    if arg_type == bool:
        if arg == "1" or arg == 1 or arg == True:
            return True
        elif arg == "0" or arg == 0 or arg == False:
            return False
        else:
            raise ValueError(f"Argument {name} must be a 0 or 1")
    elif arg_type == int:
        try:
            return int(arg)
        except ValueError:
            raise ValueError(f"Argument {name} must be an integer")
    elif hasattr(arg_type, "interpret_arg"):
        return arg_type.interpret_arg(arg, name, *args, **kwargs)
    else:
        raise TypeError("Unknown type for interpret_arg")

class OptionEnable(enum.Enum):
    Auto = enum.auto()
    On = enum.auto()
    Off = enum.auto()

    def should_specify(self):
        return self == OptionEnable.On or self == OptionEnable.Off

    def int_value(self, default=None):
        if self == OptionEnable.On:
            return 1
        elif self == OptionEnable.Off:
            return 0
        elif default is not None:
            return int(default)
        else:
            raise ValueError("Must be On or Off to call int_value()")

    @staticmethod
    def interpret_arg(arg, name):
        bool_value = interpret_arg(arg, bool, name)
        return OptionEnable.On if bool_value else OptionEnable.Off
