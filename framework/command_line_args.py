import argparse
import sys

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
        (self._command_args, self._command_kwargs) = CommandLineArgs._parse_to_args_kwargs(command_args)

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

    @staticmethod
    def _parse_to_args_kwargs(input_args):
        args = []
        kwargs = {}

        for input_arg in input_args:
            if input_arg.startswith("--"):
                # This is a keyword arg

                if input_arg.count('=') != 1:
                    raise ValueError(f"Argument \"{input_arg}\" is incorrect - keyword arguments should be specified as --key=value")
                equal_sign_index = input_arg.index("=")
                key = input_arg[2:equal_sign_index]
                value = input_arg[equal_sign_index+1:]
                kwargs[key] = value
            elif input_arg.startswith("\\--"):
                # This is a normal arg that start with "--" and has escape backslash, so it's not treated as keyword
                args.append(input_arg[1:])
            else:
                # This is a normal arg
                args.append(input_arg)
        return args, kwargs
