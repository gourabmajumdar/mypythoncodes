import logging
from abc import ABC

from dependency_injector.wiring import inject, Provide
from src.cca_pbv.library.container import Application
from src.cca_pbv.library.results.result import Result, Ok, Err, result_wrap
from src.cca_pbv.library.db.repository.result_repository_sync import ResultRepository

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
        pass

    def is_ok(self):
        return self.ok_val is not None

    def is_err(self):
        return self.err_val is not None

    def __bool__(self):
        return self.is_ok()
    
    def __gt__(self, o):
        if self and o:
            return o
        if o.is_err():
            return o
        return self
        
    def __iter__(self):
        if self:
            if hasattr(self.ok_val, "__iter__"):
                return self.ok_val
            return iter([self.ok_val])
        return iter([])

    def __rshift__(self, fn):
        if self.is_err():
            return self
        if not callable(fn):
            raise SyntaxError("Incorrect usage of Result bind")
        retv = fn(self.ok_val)
        if not isinstance(retv, Result):
            raise Exception("Invalid usage of monadic bind on Result")
        return retv

    def expects(self, msg):
        if not self:
            msg = f"{msg}: {self.err_val}"
            logger.exception(msg)
            raise Exception(msg)
        return self.ok_val

    def default(self, default_value):
        return self.ok_val if self else default_value

    def pair_with(self, o):
        self.raise_if_err("Cannot pair due to:")
        o.raise_if_err("Cannot pair due to:")
        
        if not isinstance(o, Result):
            return self >> (lambda x: Ok(iter([(x, o)])))
        return self >> (lambda x: o >> (lamda y: Ok(iter([(x, y)]))))
    
    def raise_if_err(self, msg):
        is self.is_err():
            raise Exception(f"{msg} {self.err_val}")

class Ok(Result):
    __match_args__ = ("ok_val",)

    def __init__(self, x):
        super().__init__()
        self.ok_val = x
        self.err_val = None

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.ok_val)


class Err(Result):
    __match_args__ = ("err_val",)

    def __init__(self, x):
        super().__init__()
        self.err_val = x    
        logger.error(x)
        self.ok_val = None

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.err_val)


def result_wrap(msg=""):
    """
    Decorator to provide a default Err route for a function
    that throws exceptions. Wraps the exception and
    provides a message to the resulting exception string.
    """
    def fn_wrap(fn):
        def arg_wrap(*args, **kwargs):
            try:
                retv = fn(*args, **kwargs)
            except Exception as e:
                if msg:
                    return Err("{}: {}".format(msg, str(e)))
                return retv
                
        return arg_wrap
        
    return fn_wrap

class ResultService:
    """
    Result Tracker manages the state of a report allowing for CRUD operations
    """

    __slots__ = ("result_repository",)

    @inject
    def __init__(
        self, 
        result_repository: ResultRepository = Provide[Application.result_repository
        ],
    ):
        """Initializer"""
        self.result_repository = result_repository

    def save_results(self, results: list[ResultEntity]):
        if results:
            self.result_repository.bulk_add(results)

def format_results(results, order_id, category):
    result_records = []
    for target, target_results in results.items():
        for result in target_results:
            result_record = generate_result_record(category, target, order_id, result)
            result_records.append(result_record)
    return result_records

def generate_result_record(category, target, order_id, plugin_result):
    return ResultEntity(
        Category=category,
        fail_data=plugin_result.get("fail_data"),
        pass_data=plugin_result.get("pass_data"),
        description=plugin_result.get("description"),
        fail=plugin_result.get("fail"),
        order_id=order_id,
        plugin=plugin_result.get("tag"),
        target=target,
        start_time=plugin_result.get("start_time"),
        finish_time=plugin_result.get("finish_time"),
    )
