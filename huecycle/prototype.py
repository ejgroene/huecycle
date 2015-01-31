from inspect import iscode
from types import FunctionType, MethodType

object_ = object

class Self(object):
    def __init__(me, self, this):
        me.self = self
        me.this = this
    def __getattribute__(me, name):
        if name in ("this", "self"): return object_.__getattribute__(me, name)
        return getattr(object_.__getattribute__(me, "self"), name)
    def __setattr__(me, name, value):
        if name in ("this", "self"): return object_.__setattr__(me, name, value)
        setattr(me.self, name, value)
    def __eq__(me, rhs): 
        return rhs == me.self
    def __call__(me, *args, **kwargs): #TestMe
        return object_.__getattribute__(me, "self").__call__(*args, **kwargs)
    def __getitem__(me, name):
        return object_.__getattribute__(me, "self")[name]

class prototype(object_):

    def __getitem__(self, name):
        return getattr(self, str(name))  #TestMe

    def __getattribute__(self, name):
        for proto in object_.__getattribute__(self, "__prototypes__"):
            try:
                attr = object_.__getattribute__(proto, name)
            except AttributeError:
                continue
            if isinstance(attr, FunctionType):
                return  MethodType(attr, Self(self, proto))
            if isinstance(attr, dict) and not name == "__dict__": #TestMe
                return prototype(self, None, **attr)                #TestMe
            return attr

    def __init__(self, proto, ctor, **kwargs):
        self.__prototypes__ = (self,) + (proto.__prototypes__ if proto else ())
        self.__dict__.update(kwargs)
        if ctor:
            for code in (c for c in ctor.func_code.co_consts if iscode(c)):
                setattr(self, code.co_name, FunctionType(code, ctor.func_globals, closure=ctor.func_closure))
            assert ctor.func_code.co_argcount == 1, "self must be the single argument of constructor"
            ctor(self)
            
    def __call__(self, function=None, **kwargs):
        return prototype(self, function, **kwargs)

    def __contains__(self, name):
        return name in self.__dict__

    def __repr__(self):
        return repr(self.__dict__)

    def __iter__(self): #TESTME
        return ((name, value) for name, value in self.__dict__.iteritems() if not name.startswith("__"))

    def update(self, kws):
        return self.__dict__.update(kws)

def object(*args, **kwargs):
    if args:
        if isinstance(args[0], FunctionType):
            return prototype(None, args[0])
        else:
            return prototype(args[0], None, **kwargs)
    else:
        return prototype(None, None, **kwargs)

from autotest import autotest

@autotest
def This():
    @object
    def Obj(self):
        def f(self):
            return self, self.this
    assert Obj.f() == (Obj, Obj)
    @Obj
    def Obj2(self):
        pass
    assert Obj2.f() == (Obj2, Obj)

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
        return locals()
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

@object
def o0(self):
    pass

#@autotest   # a bit to difficult yet; methods don't know their 'this', only self
def CallParent():
    a = 1
    @o0
    def o1(self):
        def f(self, s):
            return  "|%s|" % s
    @o1
    def o2(self):
        def f(self, s):
            return "[%s]" % self.this.f(s)
    o3 = o2()
    assert o1.f("X") == "|X|"
    assert o2.f("Y") == "[|Y|]"
    assert o3.f("Z") == "[|Z|]", o3.f("Z")


@autotest
def OverrideAttributesInCtor():
    @object
    def x(self):
        self.a=2
    assert x.a == 2

@autotest
def ArgsMakeNoSense():
    try:
        @object
        def x(self, s):
            pass
    except AssertionError as e:
        assert str(e) == "self must be the single argument of constructor", e
    try:
        @object
        def x(self, s=1):
            pass
    except AssertionError as e:
        assert str(e) == "self must be the single argument of constructor", e
    myobject = object()
    try:
        @myobject
        def x(self, s=1):
            pass
    except AssertionError as e:
        assert str(e) == "self must be the single argument of constructor", e
