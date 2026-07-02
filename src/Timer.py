"""This module provides utilities to measure the execution time of functions and
tasks, and to track their status using an enum-based task status framework.

It includes a `Timer` class implemented as a context manager for measuring and
reporting task durations, and a `TaskStatus` enumeration for representing the
state of a task.

Classes:
    TaskStatus: An enumeration representing possible states of a task.
    Timer: A context manager for measuring execution time and tracking task statuses.
"""
import subprocess
import json
from contextlib import ContextDecorator
from datetime import datetime
from enum import Enum

class TaskStatus(Enum):
    """
    Represents the various statuses a task can have.

    This class is an enumeration that defines the possible states of a task
    during its lifecycle. It is intended to provide a clear and consistent way
    to represent and handle task statuses in code.

    :cvar PENDING: The task is pending and has not started yet.
    :cvar STARTED: The task has started execution.
    :cvar COMPLETED: The task has finished execution successfully.
    :cvar FAILED: The task has finished execution but encountered failure.
    """
    PENDING = 1
    STARTED = 2
    COMPLETED = 3
    FAILED = 4

class Timer(ContextDecorator):
    """
    A Timer class for measuring and tracking the execution duration of code blocks or functions.

    This class serves as a context manager and decorator that records the start and end time of a
    code block or function. It calculates the duration of execution and provides status updates
    (PENDING, STARTED, COMPLETED, FAILED). Additionally, the class can serialize and log execution
    details in JSON format.

    :ivar name: Name of the timer instance, aiding in identification of timed processes.
    :type name: Optional[str]
    :ivar push: A boolean flag for managing specific behavior during timed function calls.
    :type push: bool
    :ivar returnvalue: The result of an executed task or function, if applicable.
    :type returnvalue: Any
    :ivar status: Current status of the timer (PENDING, STARTED, COMPLETED, FAILED).
    :type status: TaskStatus
    :ivar start_time: Recorded start time of the timer when entering the context.
    :type start_time: Optional[datetime]
    :ivar end_time: Recorded end time of the timer when exiting the context.
    :type end_time: Optional[datetime]
    :ivar duration: Duration of the timed execution as a string (or 'dnf' if not completed).
    :type duration: str
    """
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
        """
        Constructs a dictionary containing the status, duration, and optionally the return value
        if it exists.

        This method organizes information into a dictionary format, making it easy to access
        and operate on structured information regarding the instance's state.

        :return: A dictionary containing the status, duration, and optionally a return value.
        :rtype: dict
        """
        results:dict = {
            'status': self.status.name.capitalize(),
            'duration': self.duration
        }
        if self.returnvalue: results['returnvalue'] = self.returnvalue
        return results

    def time_function(self, *args, func, name=None) -> dict:
        """
        Measures the execution time of a function, tracks its success or failure status,
        and returns the resulting data as a dictionary.

        The provided function is executed with the given arguments, and the resulting
        status is determined based on the return value's truthiness. If an exception
        related to a subprocess error is raised, the failure status is recorded. The
        function's execution data is then returned as a dictionary representation.

        :param args: Positional arguments to be passed to the function being executed.
        :type args: tuple
        :param func: The function to be executed.
        :type func: Callable
        :param name: The name associated with the function execution. Optional.
        :type name: str, optional
        :return: A dictionary containing the execution details, including the
            function's result and status.
        :rtype: dict
        """
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
        """
        Determines whether the status of the task is not FAILED.

        This method checks the current status of the task and returns False
        if the status is TaskStatus.FAILED. Otherwise, it returns True.

        :return: A boolean value indicating whether the task status is not FAILED.
        :rtype: bool
        """
        return False if self.status == TaskStatus.FAILED else True