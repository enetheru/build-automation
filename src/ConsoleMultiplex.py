"""
Extension of the Console class and support for multiplexing outputs.

This module provides classes for extending the functionality of the Rich Console
to enable output multiplexing. It includes the `ConsoleMultiplex` class, which
manages multiple output destinations, and the `TeeOutput` class for teeing the
output into a new console.

Classes:
    - ConsoleMultiplex: Extends the Rich Console to allow output to multiple
      registered destinations simultaneously.
    - TeeOutput: Provides functionality to temporarily tee the output of a
      console.

Exceptions:
    None
"""
from rich.console import Console

class ConsoleMultiplex(Console):
    """
    Extension of the Console class to support multiplexing outputs.

    ConsoleMultiplex allows printing to multiple registered console outputs
    simultaneously. The main console output can be toggled on or off using
    the `quiet` attribute. This class is useful for directing output to
    different destinations, such as files, in-memory buffers, or other
    console instances.

    :ivar quiet: If set to True, suppresses output to the main console.
    :type quiet: bool
    :ivar outputs: A dictionary of registered output console destinations.
        Keys are the names of the outputs, and values are Console instances.
    :type outputs: dict[str, Console]
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiet = False
        self.outputs: dict[str, Console] = dict[str, Console]()

    def print(self, *args, **kwargs ):
        """Print output to the console and all registered outputs.

        Args:
            *args: Positional arguments to print.
            **kwargs: Keyword arguments for rich console printing.

        Returns:
            None: Prints to the main console (if not quiet) and all registered outputs.
        """
        if not self.quiet: super().print(*args, **kwargs)
        for dest in self.outputs.values():
            dest.print(*args, **kwargs)

    def tee(self, new_console: Console, name: str = None):
        """Register a new console output destination.

        Args:
            new_console (Console): The console to add as an output destination.
            name (str, optional): The name of the output destination. Defaults to a numbered name.

        Returns:
            None: Adds the console to the outputs dictionary.

        Raises:
            OutputExists: If the specified name already exists.
        """
        if name in self.outputs.keys():
            raise "OutputExists"

        self.outputs[name if name else f"{len(self.outputs)}"] = new_console

    def pop(self, name: str = None) -> Console:
        """Remove and return a console output destination.

        Args:
            name (str, optional): The name of the output to remove. If None, removes the last added output.

        Returns:
            Console: The removed console.

        Raises:
            AlreadyEmpty: If no outputs are registered.
            InvalidName: If the specified name does not exist.
        """
        if not len(self.outputs):
            raise "AlreadyEmpty"
        if name:
            if name not in self.outputs:
                raise "InvalidName"
            console = self.outputs.pop(name)
        else:
            console = self.outputs.popitem()

        console.file.close()
        return console


class TeeOutput:
    """
    Facilitates redirection of the output from a console to a specified target
    using a multiplexer.

    This class enables the management of a console's output through a "tee" mechanism,
    which allows duplicating the output to multiple destinations or contextually redirecting it.
    It provides methods to start and end the redirection, and supports usage in a
    context manager to ensure proper cleanup of resources.

    :ivar multiplexer: Multiplexer used to manage teeing of console output.
    :type multiplexer: ConsoleMultiplex
    :ivar console: Console instance from which the output is redirected.
    :type console: Console
    :ivar name: Name or target label used for redirection.
    :type name: str
    """
    #     console.tee( project_console , project.name )
    def __init__(self, multiplexer:ConsoleMultiplex, new_console:Console, name ):
        self.multiplexer = multiplexer
        self.console = new_console
        self.name = name

    def start( self ):
        """
        Starts the process of directing the output from the given console to the
        specified name using a multiplexer.

        This method sets up a connection between the console and a designated name
        using a tee mechanism provided by the multiplexer object.

        :return: None
        """
        self.multiplexer.tee( self.console, self.name )

    def end( self ):
        """
        Removes the current task or item associated with the provided name from
        the multiplexer.

        :return: None
        :rtype: None
        """
        self.multiplexer.pop(self.name)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.end()
        return False