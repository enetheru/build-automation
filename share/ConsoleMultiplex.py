from rich.console import Console


class ConsoleMultiplex(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outputs: dict[str, Console] = dict[str, Console]()

    def print(self, *args, **kwargs) -> None:
        super().print(*args, **kwargs)
        for dest in self.outputs.values():
            dest.print(*args, **kwargs)

    def tee(self, new_console: Console, name: str = None):
        if name in self.outputs.keys():
            raise "OutputExists"

        self.outputs[name if name else f"{len(self.outputs)}"] = new_console

    def pop(self, name: str = None) -> Console:
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
