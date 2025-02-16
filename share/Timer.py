import subprocess
import json
from contextlib import ContextDecorator
from datetime import datetime
from enum import Enum

class TaskStatus(Enum):
    PENDING = 1
    STARTED = 2
    COMPLETED = 3
    FAILED = 4

class Timer(ContextDecorator):
    def __init__(self, name=None, push=True ):
        self.push = push
        self.name = name
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
        self.duration = str(self.end_time - self.start_time)[:-3]
        if self.status == TaskStatus.STARTED:
            self.status = TaskStatus.COMPLETED
        print('json:', json.dumps({self.name:self.get_dict()}, default=str))
        return False

    def get_dict(self) -> dict:
        results:dict = {
            'status': self.status.name.capitalize(),
            'duration': self.duration
        }
        if self.returnvalue: results['returnvalue'] = self.returnvalue
        return results

    def time_function(self, *args, func, name=None) -> dict:
        self.name = name
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
            self.status = TaskStatus.FAILED
        return self.get_dict()

    def ok(self) -> bool:
        return False if self.status == TaskStatus.FAILED else True