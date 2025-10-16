from rich.console import Console

class ConsoleMultiplex(Console):
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
    #     console.tee( project_console , project.name )
    def __init__(self, multiplexer:ConsoleMultiplex, new_console:Console, name ):
        self.multiplexer = multiplexer
        self.console = new_console
        self.name = name

    def start( self ):
        self.multiplexer.tee( self.console, self.name )

    def end( self ):
        self.multiplexer.pop(self.name)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.end()
        return False