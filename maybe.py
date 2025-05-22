from abc import ABC

class Maybe(ABC):
    """
    Monadic type named Maybe.
    Definition: Maybe = Some | Nothing

    Description:
    Acts like Rust's Option or Haskell's Maybe.
    Useful for handling cases where data may or may not exist.
    `Some(x)` means value exists.
    `Nothing()` means absence of value.
    """

    __slots__ = ["value", "has_value"]
    __match_args__=("value",)

    def __init__(self, value):
        self.value = value
        self.has_value = False
        return

    def is_some(self):
        return self.has_value

    def is_nothing(self):
        return not self.has_value
    
    def __bool__(self):
        return self.has_value

    def __eq__(self, other):
        if isinstance(o, Maybe):
            return (self.has_value == o.has_value) and (self.value == o.value)
        return self.value == o

    def __iter__(self):
        if self.has_value:
            if hasattr(self.value, "__iter__"):
                return self.value
            return iter([self.value])
        return iter([])
    
    def __gt__(self, o):
        if not isinstance(o, Maybe):
            return self.value > o
        if self.is_nothing():
            return Nothing
        return o
        
    def __lt__(self, o):
         if not isinstance(o, Maybe):
            return self.value < o
        if o.is_nothing():
            return o
        return self
        
    def __rshift__(self, fn):
        """ Monadic bind: maybe >> fn """
        if self.is_nothing():
            return self
        if not callable(fn):
            raise Exception("Invalid usage of __rshift__()")
        retv = fn(self.value)
        if not isinstance(retv, Maybe):
            raise Exception("Invalid Usage of Monadic Bind")
        return retv

    def __ge__(self, fn):
        """ fn: (a) -> b => a @ fn = Some(fn(a)) or Nothing """
        if self.is_nothing():
            return
        retv = fn(self.value)
        if retv.is_nothing():
            self = Nothing()
        return

    def chain(self, fn):
        """ Same as >> """
        return self >> fn

    def pair_with(self, o):
        """ zip two Maybes to Maybe[Tuple] """
        if not isinstance(o, Maybe):
            return self >> (lambda x: Some(iter([(x, o)])))
        return self >> (lambda x: o >> (lamda y: Some(iter([x, y]))))

    def expects(self, msg):
        if not self:
            raise Exception(f"Expectation Failed: {msg}")
        return self.value

    def default(self, default_value):
        if not self:
            return default_value
        return self.value
    
    pass

class Some(Maybe):
    def __init__(self, x):
        super().__init__(x)
        self.has_value = True
        return

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.value)
    
    pass

class Nothing(Maybe):
    def __init__(self): 
        super().__init__(None)
        return

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)
    
    pass
