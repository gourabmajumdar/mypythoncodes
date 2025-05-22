import logging
from abc import ABC

from dependency_injector.wiring import inject, Provide
from cca_pbv.library.container import Application
from cca_pbv.library.results.result import Result, Ok, Err, result_wrap
from cca_pbv.library.db.repository.result_repository_sync import ResultRepository

logger = logging.getLogger(__name__)


class Result(ABC):
    """
    Result monad
    Definition: Result = Ok | Err

    The goal of the result monad is to pass computations safely
    without having to explicitly handle line pathways.
    """

    __slots__ = ("ok_val", "err_val")

    def __init__(self):
        self.ok_val = None
        self.err_val = None

    def is_ok(self):
        return self.ok_val is not None

    def is_err(self):
        return self.err_val is not None

    def __bool__(self):
        return self.is_ok()

    def __iter__(self):
        if self.is_ok():
            if hasattr(self.ok_val, "__iter__"):
                return iter(self.ok_val)
            return iter([self.ok_val])
        return iter([])

    def __rshift__(self, fn):
        if self.is_err():
            return self
        if not callable(fn):
            raise Exception("Invalid usage of Result >>")
        ret = fn(self.ok_val)
        if not isinstance(ret, Result):
            raise Exception("Invalid usage of monadic bind on Result")
        return ret

    def expects(self, msg):
        if self.is_ok():
            return self.ok_val
        raise Exception(f"Expected Ok, got Err: {msg}")

    def default(self, default_value):
        return self.ok_val if self.is_ok() else default_value

    def unwrap(self):
        if self.is_ok():
            return self.ok_val
        raise Exception(f"Cannot unwrap Err: {self.err_val}")


class Ok(Result):
    __slots__ = ("ok_val",)

    def __init__(self, ok_val):
        super().__init__()
        self.ok_val = ok_val
        self.err_val = None

    def __repr__(self):
        return f"Ok({self.ok_val})"


class Err(Result):
    __slots__ = ("err_val",)

    def __init__(self, err_val):
        super().__init__()
        self.err_val = err_val
        self.ok_val = None

    def __repr__(self):
        return f"Err({self.err_val})"


def result_wrap(msg=None):
    """
    Decorator to provide a default Err route for a function
    that throws exceptions. Wraps the exception and
    provides a message to the resulting exception string.
    """
    def wrap_fn(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err_msg = f"{msg or fn.__name__}: {str(e)}"
                return Err(err_msg)
        return wrapper
    return wrap_fn


class ResultService:
    """
    Result Tracker manages the state of a report allowing for CRUD operations
    """

    __slots__ = ("result_repository",)

    @inject
    def __init__(self, result_repository: ResultRepository = Provide[Application.result_repository]):
        self.result_repository = result_repository

    def save_results(self, results: list[Result]):
        if results:
            self.result_repository.bulk_add(results)


def prepare_result(result, error_id, category, target, env_id, elapsed):
    return Ok({
        "error_id": error_id,
        "category": category,
        "target": target,
        "env_id": env_id,
        "result": result,
        "start_time": get_datetime_timestamp_now(),
        "finish_time": get_datetime_timestamp_now(),
        "elapsed": elapsed
    })
