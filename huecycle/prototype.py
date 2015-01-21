from inspect import iscode
from types import FunctionType, MethodType

object_ = object

class prototype(object_):

    def __getattribute__(self, name):
        for proto in object_.__getattribute__(self, "__prototypes__"):
            try:
                attr = object_.__getattribute__(proto, name)
                return MethodType(attr, self) if isinstance(attr, FunctionType) else attr
            except AttributeError:
                continue

    def __init__(self, proto, ctor, **kwargs):
        self.__prototypes__ = (self,) + (proto.__prototypes__ if proto else ())
        if ctor:
            ctor(self)
            for code in (c for c in ctor.func_code.co_consts if iscode(c)):
                setattr(self, code.co_name, FunctionType(code, dict(), code.co_name))
        self.__dict__.update(kwargs)
            

def object(*args, **kwargs):
    if args and isinstance(args[0], FunctionType):
        return lambda proto=None: prototype(proto, args[0], **kwargs)
    else:
        return prototype(args[0] if args else None, None, **kwargs)

@object
def myobject1(self, c=42):
    self.prop = 1+2
    self.prak = "aa"
    def f(self):
        return self

@object
def myobject2(self, c=43):
    def g(self):
        return self

from misc import autotest

@autotest
def FindPrototypes():
    o1 = object(a=1, b=4)
    assert o1.__prototypes__ == (o1,)
    o2 = object(o1, a=2)
    assert o2.__prototypes__ == (o2, o1), o2.__prototypes__
    o3 = object(o2, a=3)
    assert o3.__prototypes__ == (o3, o2, o1)
    assert o1.a == 1
    assert o2.a == 2
    assert o3.a == 3
    assert o1.b == 4
    assert o2.b == 4
    assert o2.b == 4
    assert o1.x == None
    assert o2.x == None
    assert o3.x == None
    
@autotest
def CreatePrototype():
    p1 = myobject1()
    assert p1
    assert p1.f()
    assert p1 == p1.f()
    assert p1.prop == 3, p1.prop
    assert p1.prak == "aa"
    p2 = myobject2(p1)
    assert p2
    assert p2.__prototypes__ == (p2, p1), p2.__prototypes__
    assert p2.prop == 3
    assert p2.f() == p2
    assert p2.g() == p2
    assert p1.c == 42, p1.c
    assert p2.c == 43
