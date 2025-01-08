import sys
from typing import IO, Callable


class Pipe:
    def __init__(self):
        self.outputs: dict[str, IO] = dict[str, IO]()

    def write(self, text):
        # Write to actual stdout, which will print to the console
        sys.__stdout__.write(text)
        for dest in self.outputs.values():
            dest.write(text)

    def flush(self):
        # Flush the actual stdout
        sys.__stdout__.flush()
        for dest in self.outputs.values():
            dest.flush()

    def tee(self, stream: IO, name: str = None):
        if name in self.outputs.keys():
            raise "OutputExists"

        self.outputs[name if name else f'{len(self.outputs)}'] = stream

    def pop(self, name: str = None) -> IO:
        if not len(self.outputs):
            raise "AlreadyEmpty"
        if name:
            if name not in self.outputs:
                raise "InvalidName"
            stream = self.outputs.pop(name)
        else:
            stream = self.outputs.popitem()
        stream.close()
        return stream

    def clear(self):
        for stream in self.outputs.values():
            stream.close()
        self.outputs.clear()