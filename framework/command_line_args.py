import argparse
import inspect

class CommandLineArgs:
    def __init__(self):
        self._framework_args_parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
        self._framework_args_parser.add_argument("-p", "--project-dir-force")
        self._framework_args_parser.add_argument('-v', '--verbose', action='store_true')
        self._framework_args_parser.add_argument('-q', '--quiet', action='store_true')
        self._framework_args_parser.add_argument('-h', '--help', action='store_true')

        self._process_name = None
        self._command_args = None
        self._command_kwargs = None
        self.framework_args_parsed = None

    def parse(self, command_controller, args):
        # Get process name
        self._process_name = args[0]
        args = args[1:]

        if command_controller.is_single_command():
            # When @main_command decorator was used, we have only one possible command to call and it
            # has a hardcoded name. In this case we don't interpet the first argument as a command
            # name. It would be redundant.
            self.command_name = command_controller.MAIN_COMMAND_NAME
        elif command_controller.is_multi_command():
            # When @command decorators are used, we have many possible commands identified by name.
            # First cmdline argument is interpreted as the command name used for lookup later.
            if len(args) == 0 or args[0].startswith('-'):
                raise KeyError("No command specified")
            self.command_name = args[0]
            args = args[1:]
        else:
            raise ValueError("Unknown CommandController state")

        # Next tokens are command arguments (until the end of cmdline or "--"" argument)
        try:
            divider_index = args.index("--")
            command_args = args[:divider_index]
            args = args[divider_index+1:]
        except ValueError:
            command_args = args
            args = []
        are_kwargs_supported = self._are_kwargs_supported(command_controller.get_command(self.command_name))
        (self._command_args, self._command_kwargs) = CommandLineArgs._parse_to_args_kwargs(command_args, are_kwargs_supported)

        # Rest of tokens are global arguments intended for the framework
        (self._framework_args, unparsed_args) = self._framework_args_parser.parse_known_args(args)
        if unparsed_args:
            raise KeyError(f"Unknown arguments found: {unparsed_args}")

        # Validate some arguments
        if self._framework_args.quiet and self._framework_args.verbose:
            raise ValueError("Cannot both enable quiet and verbose mode")

    def get_process_name(self):
        return self._process_name

    def get_command_args_kwargs(self):
        return (self._command_args, self._command_kwargs)

    def get_framework_args(self):
        return self._framework_args

    def print_framework_args_help(self):
        help_lines = self._framework_args_parser.format_help()
        help_lines = help_lines.splitlines()
        help_lines = help_lines[3:]
        print("Framework options parsed after '--' divider:")
        for line in help_lines:
            print(line)

    def _are_kwargs_supported(self, command):
        if command is None:
            return True

        # If the command takes positional *args, then do not parse --key=value as kwargs, but instead
        # pass them verbatim as positional arguments.
        arg_spec = inspect.getfullargspec(command)
        vararg_name = arg_spec[1]
        return vararg_name is None

    def print_help_for_command(self, command):
        arg_spec = inspect.getfullargspec(command)
        arg_names = arg_spec[0]
        arg_defaults = arg_spec[3]
        varargs_name = arg_spec[1]
        kwargs_supported = varargs_name is None

        # TODO: simply converting to string is ok for strings and ints, but we'd need something like interpret_arg for enums.
        arg_default_strs = [f'"{default}"' for default in arg_defaults]
        required_args_count = len(arg_names) - len(arg_defaults)
        if required_args_count > 0:
            arg_default_strs = required_args_count * [None] + arg_default_strs

        if len(arg_names) == 0:
            print(f"The {command.__name__} command does not take any arguments.")
        elif kwargs_supported:
            print(f'The {command.__name__} command supports both positional or keyword (key=value) styles of passing arguments. Arguments are:')
            for name, default in zip(arg_names, arg_default_strs):
                if default is None:
                    default="  (required)"
                print(f"  --{name}={default}")
        else:
            print(f'The {command.__name__} command supports only positional style of passing arguments. Arguments are:')
            print("  ", end='')
            for name, default in zip(arg_names, arg_default_strs):
                default_str = f"(default: {default})" if default is not None else ""
                print(f"{name}{default_str}", end=', ')
            print(f"*{varargs_name}")


    @staticmethod
    def _parse_to_args_kwargs(input_args, are_kwargs_supported):
        args = []
        kwargs = {}

        for input_arg in input_args:
            if input_arg.startswith("--") and are_kwargs_supported:
                # This is a keyword arg

                if input_arg.count('=') != 1:
                    raise ValueError(f"Argument \"{input_arg}\" is incorrect - keyword arguments should be specified as --key=value")
                equal_sign_index = input_arg.index("=")
                key = input_arg[2:equal_sign_index]
                value = input_arg[equal_sign_index+1:]
                kwargs[key] = value
            elif input_arg.startswith("\\--") and are_kwargs_supported:
                # This is a normal arg that start with "--" and has escape backslash, so it's not treated as keyword
                args.append(input_arg[1:])
            else:
                # This is a normal arg
                args.append(input_arg)
        return args, kwargs
