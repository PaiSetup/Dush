from utils.os_function import is_windows
from enum import Enum

class Compiler(Enum):
    VisualStudio = 1
    Ninja = 2

    def __str__(self):
        return {
            Compiler.VisualStudio: "vs",
            Compiler.Ninja: "ninja",
        }[self]

class Bitness(Enum):
    x32 = 1
    x64 = 2

    def __str__(self):
        return {
            Bitness.x32: "32",
            Bitness.x64: "64",
        }[self]

class BuildType(Enum):
    Debug = 1
    Release = 2
    RelWithDebInfo = 3

    def __str__(self):
        return {
            BuildType.Debug: "Debug",
            BuildType.Release: "Release",
            BuildType.RelWithDebInfo: "RelWithDebInfo",
        }[self]

class BuildConfig:
    def __init__(self, compiler=None, bitness=None, build_type=None) -> None:
        self.compiler = compiler if compiler else BuildConfig.default_compiler
        self.bitness = bitness if bitness else BuildConfig.default_bitness
        self.build_type = build_type if build_type else BuildConfig.default_build_type

    def __str__(self):
        return f"{self.compiler}_{self.bitness}_{self.build_type}"

    @classmethod
    def configure(cls, allowed_compilers, allowed_bitnesses, allowed_build_types, default_compiler, default_bitness, default_build_type):
        if (default_compiler not in allowed_compilers or
           default_bitness not in allowed_bitnesses or
           default_build_type not in allowed_build_types):
            raise ValueError("Incorrect BuildConfig configuration")

        cls.allowed_compilers = allowed_compilers
        cls.allowed_bitnesses = allowed_bitnesses
        cls.allowed_build_types = allowed_build_types
        cls.default_compiler = default_compiler
        cls.default_bitness = default_bitness
        cls.default_build_type = default_build_type

    @staticmethod
    def interpret_arg(arg, name, allow_empty=True):
        result = BuildConfig()

        if len(arg) == 0:
            if allow_empty:
                return result
            else:
                raise KeyError(f"Argument {name} must be a valid config")

        for token_raw in arg.split("_"):
            token = token_raw.strip().lower()
            if not result._interpret_token(token):
                raise KeyError(f'Argument {name} must be a valid build config. Could not interpret "{token_raw}" in "{arg}"')
        return result

    def _interpret_token(self, token):
        supported_tokens = [
            ("32", Bitness.x32),
            ("64", Bitness.x64),
            ("d", BuildType.Debug),
            ("rd", BuildType.RelWithDebInfo),
            ("r", BuildType.Release),
            ("ninja", Compiler.Ninja),
        ]
        if is_windows():
            supported_tokens.append(("vs", Compiler.VisualStudio))

        for string_value, interpreted_value in supported_tokens:
            # Depending on the type of interpreted value we will use different lists
            # of allowed values. If the value is not allowed, don't even try to interpret it.

            # Interpreted value may be of 3 different types. Verify the type and select proper
            # values based on it:
            #  - list of allowed values for a given type
            #  - destination field, to which we should write, if the value is interpreted correctly.
            match interpreted_value:
                case Compiler():
                    allowed_values = BuildConfig.allowed_compilers
                    dst_field = "compiler"
                case Bitness():
                    allowed_values = BuildConfig.allowed_bitnesses
                    dst_field = "bitness"
                case BuildType():
                    allowed_values = BuildConfig.allowed_build_types
                    dst_field = "build_type"
                case _:
                    raise KeyError("Unsupported token type")

            # Try to interpret input token by comparing it with expected string value.
            if interpreted_value in allowed_values and token == string_value:
                setattr(self, dst_field, interpreted_value)
                return True

        return False

    @staticmethod
    def all_permutations():
        for compiler in BuildConfig.allowed_compilers:
            for bitness in BuildConfig.allowed_bitnesses:
                for build_type in BuildConfig.allowed_build_types:
                    yield BuildConfig(compiler, bitness, build_type)

    @staticmethod
    def interpret_array(*args, allow_empty=True):
        return [BuildConfig.interpret_arg(arg, "config", allow_empty=allow_empty) for arg in args]

# By default allow all configurations
# TODO remove this and require explicit configure
BuildConfig.configure(
    list(Compiler),
    list(Bitness),
    list(BuildType),
    Compiler.VisualStudio,
    Bitness.x64,
    BuildType.Debug,
)
