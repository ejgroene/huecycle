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
            for code in (c for c in ctor.func_code.co_consts if iscode(c)):
                setattr(self, code.co_name, FunctionType(code, ctor.func_globals, code.co_name))
            ctor(self)
        self.__dict__.update(kwargs)
            

    def __call__(self, function=None, **kwargs):
        return prototype(self, function, **kwargs)

    def __contains__(self, name):
        return name in self.__dict__

    def __repr__(self):
        return repr(self.__dict__)

    def update(self, kws):
        return self.__dict__.update(kws)

def object(*args, **kwargs):
    if args:
        if isinstance(args[0], FunctionType):
            return prototype(None, args[0], **kwargs)
        else:
            return prototype(args[0], None, **kwargs)
    else:
        return prototype(None, None, **kwargs)

from misc import autotest

@autotest
def CreateObjectFromPrototype():
    creature = object(alive=True)
    @creature
    def person(self):
        def age(self): return 2015 - self.birth
    me = object(person, birth=1990)
    assert me.age() == 25, me
    assert me.alive == True
    me.alive = False
    assert me.alive == False
    assert creature.alive == True

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
    @object
    def p1(self):
        self.prop = 1 + 2
        self.prak = "aa"
        self.this = self.f()
        def f(self): return self
    assert p1
    assert p1.f()
    assert p1 == p1.f()
    assert p1.prop == 3, p1.prop
    assert p1.prak == "aa"
    assert p1.this == p1
    @p1
    def p2(self):
        def g(self): return self
    assert p2
    assert p2.__prototypes__ == (p2, p1), p2.__prototypes__
    assert p2.prop == 3
    assert p2.f() == p2
    assert p2.g() == p2
    assert p2.this == p1

@autotest
def CallPrototypeCreateNewObject():
    p = object()
    o = p(a=42)
    assert o
    assert o != p
    assert o.__prototypes__ == (o, p)
    assert o.a == 42

@autotest
def UseGlobals():
    @object
    def one(self):
        def f(self):
            return autotest
    assert one.f() == autotest

@autotest
def AccessProperties():
    o = object(a=1, b=2)
    assert "a" in o
    assert "b" in o
    assert "c" not in o
    assert str(o) == "{'a': 1, 'b': 2, '__prototypes__': ({...},)}", str(o)
