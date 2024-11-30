import sys
import traceback
import inspect
from datetime import datetime
from pathlib import Path

from framework.command_controller import CommandController
from framework.command_line_args import CommandLineArgs

class Framework:
    def __init__(self):
        self._command_controller = CommandController()
        self._command_line_args = CommandLineArgs()

    def get_command_decorator_main(self):
        return self._command_controller.register_command_main

    def get_command_decorator_multiple(self):
        return self._command_controller.register_command_multiple

    def get_framework_args(self):
        return self._command_line_args.get_framework_args()

    def main(self):
        self._insert_framework_commands()

        # Parse command line
        try:
            self._command_line_args.parse(self._command_controller, sys.argv)
        except:
            self._print_help()
            sys.exit(1)

        # Get command to execute. It can either be parsed from cmdline (in case of MultipleCommands mode)
        # or implicitly defined (in case of SingleCommand mode).
        command = self._command_controller.get_command(self._command_line_args.command_name)
        if command is None:
            print(f'ERROR: Command "{self._command_line_args.command_name}" not found!')
            self._print_help()
            sys.exit(1)
        if self.get_framework_args().help:
            self._print_help(command)
            sys.exit(0)

        # Try to execute the command and, handle any exception and print user-friendly summary.
        try:
            # Execute command
            begin_timestamp = datetime.now()
            command_args, command_kwargs = self._command_line_args.get_command_args_kwargs()
            command(*command_args, **command_kwargs)
            self._print_execution_time(begin_timestamp, "SUCCESS")
            exit_code = 0
        except Exception as e:
            self._print_exception_info()
            self._print_execution_time(begin_timestamp, f"ERROR: {e}")
            exit_code = 1
        except KeyboardInterrupt:
            self._print_exception_info()
            self._print_execution_time(begin_timestamp, "INTERRUPT (Ctrl+C detected)")
            exit_code = 2

        # Return exit code
        sys.exit(exit_code)

    def _insert_framework_commands(self):
        if self._command_controller.is_multi_command():
            def list():
                commands_names = [command for command in self._command_controller.get_commands()]
                print(' '.join(commands_names))
            self._command_controller.register_command_multiple(list)



    def _print_help(self, command=None):
        # Print usage
        usage_tokens = [ "usage:"]
        usage_tokens.append(Path(self._command_line_args.get_process_name()).name)
        if self._command_controller.is_multi_command():
            usage_tokens.append("COMMAND_NAME")
        usage_tokens.append("COMMAND_OPTIONS...")
        usage_tokens.append("[-- [FRAMEWORK_OPTIONS...]]")
        print(' '.join(usage_tokens))
        print()

        # Print available commands
        self._command_controller.print_help()

        # Print help for current command
        if command is not None:
            arg_spec = inspect.getfullargspec(command)
            arg_names = arg_spec[0]
            print(f'Command options for "{command.__name__}" command:')
            for arg_name in arg_names:
                print(f"  --{arg_name}=")
            print()

        # Print help for framework args
        self._command_line_args.print_framework_args_help()

    def _print_execution_time(self, begin_timestamp, message):
        if self._command_line_args.get_framework_args().quiet:
            return
        begin_timestamp = begin_timestamp.replace(microsecond=0)
        end_timestamp = datetime.now().replace(microsecond=0)
        time_begin = begin_timestamp.strftime('%H:%M:%S')
        time_end = end_timestamp.strftime('%H:%M:%S')
        time_duration = end_timestamp - begin_timestamp
        print(f"\n{message}   startTime={time_begin} endTime={time_end} executionTime={time_duration}")

    def _print_exception_info(self):
        if not self._command_line_args.get_framework_args().verbose:
            return
        traceback.print_exc()

framework = Framework()
