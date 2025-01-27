import subprocess
import types
from datetime import datetime
from contextlib import ContextDecorator
from enum import Enum
import rich

class TaskStatus(Enum):
    PENDING = 1
    STARTED = 2
    COMPLETED = 3
    FAILED = 4

class Timer(ContextDecorator):
    def __init__(self):
        self.returnvalue = None
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.duration = 'dnf'

    def __enter__(self):
        self.status = TaskStatus.STARTED
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = 'dnf'
        return self

    def __exit__(self, *exc):
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time
        if self.status == TaskStatus.STARTED:
            self.status = TaskStatus.COMPLETED
        return False

    def get_dict(self) -> dict:
        results = {
            'status':self.status.name.capitalize(),
            'duration':self.duration,
        }
        if self.returnvalue: results['returnvalue'] = self.returnvalue
        return results

    def time_function(self, *args, func:types.FunctionType) -> dict:
        try:
            with self:
                self.returnvalue = func( *args )
            # Change status depending on the truthiness of returnvalue
            # where False is Success and True is Failure.
            self.status = TaskStatus.FAILED if self.returnvalue else TaskStatus.COMPLETED
        except subprocess.CalledProcessError as e:
            # FIXME should this be more generic and handled elsewhere?
            print( '[red]subprocess error')
            print( f'[red]{e}' )
            print( f'{e.output}' )
            print( f'{e.stderr}' )
            self.status = TaskStatus.FAILED
        return self.get_dict()

    def ok(self) -> bool:
        return False if self.status == TaskStatus.FAILED else True