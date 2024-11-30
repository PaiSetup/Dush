import enum

class CommandController:
    """
    This class manages commands that are available for user. Each command has a name and a function
    that is executed after selecting it. There are two modes of commands. The two modes cannot be
    mixed with each other.

    SingleCommand means there is nothing to choose and the program is basically a single script,
    optionally with some arguments. The command for SingleCommand mode is specified with the
    'main_command_decorator' method. The command will have a dummy name, since the user cannot
    select it by name anyway.

    MultipleCommands means there are many commands, each with a different name. User will be able
    to select the command to run in command line.
    """
    MAIN_COMMAND_NAME = 'main'

    class State(enum.Enum):
        Uninitialized = enum.auto()
        SingleCommand = enum.auto()
        MultipleCommands = enum.auto()

    class IncorrectStateException(Exception):
        pass

    def __init__(self):
        self._state = CommandController.State.Uninitialized
        self._commands = {}

    def is_single_command(self):
        return self._state == CommandController.State.SingleCommand

    def is_multi_command(self):
        return self._state == CommandController.State.MultipleCommands

    def get_commands(self):
        return list(self._commands.keys())

    def get_command(self, command_name):
        return self._commands.get(command_name)

    def register_command_multiple(self, function):
        # Validate state
        if self._state == CommandController.State.Uninitialized:
            self._state = CommandController.State.MultipleCommands
        elif self._state == CommandController.State.SingleCommand:
            raise CommandController.IncorrectStateException("Cannot use @command after @main_command")
        elif self._state == CommandController.State.MultipleCommands:
            pass  # It's ok, we can have multiple commands in this state.
        else:
            raise CommandController.IncorrectStateException("Unknown state")

        # Save the command in dict. Use its name as a key.
        self._commands[function.__name__] = function
        return function

    def register_command_main(self, function):
        # Validate state
        if self._state == CommandController.State.Uninitialized:
            self._state = CommandController.State.SingleCommand
        elif self._state == CommandController.State.SingleCommand:
            raise CommandController.IncorrectStateException("Cannot use @main_command twice")
        elif self._state == CommandController.State.MultipleCommands:
            raise CommandController.IncorrectStateException("Cannot use @main_command after @command")
        else:
            raise CommandController.IncorrectStateException("Unknown state")

        # Save the command in dict. Use a default name as a key.
        self._commands[CommandController.MAIN_COMMAND_NAME] = function
        return function

    def print_help(self):
        if self.is_multi_command():
            print("Available commands:")
            for command_name in self._commands.keys():
                print(f"    {command_name}")
            print()
