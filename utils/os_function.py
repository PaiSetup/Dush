import platform
import sys

def _os_function(plat, func, frame):
    if platform.system() == plat:
        return func
    elif func.__name__ in frame.f_locals:
        return frame.f_locals[func.__name__]
    else:
        def _not_implemented(*args, **kwargs):
            raise NotImplementedError(
                f"Function {func.__name__} is not defined "
                f"for platform {platform.system()}.")
        return _not_implemented

def linux_only(func):
    return _os_function('Linux', func, sys._getframe().f_back)

def windows_only(func):
    return _os_function('Windows', func, sys._getframe().f_back)

def is_windows():
    return platform.system() == "Windows"

def is_linux():
    return platform.system() == "Linux"
