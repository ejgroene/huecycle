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

class object(object_):

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

    def __init__(self, *args, **kwargs):
        ''' @decorator:         __init__(self, func)
            with attributes:    __init__(self, func..., **attrs)
            with prototype:     __init__(self, prototype, func0..., **attrs)
        '''
        self.__prototypes__ = (self,)
        for arg in args:
            if isinstance(arg, object):
                self.__prototypes__ += arg.__prototypes__
            elif isinstance(arg, FunctionType):
                if arg.__code__.co_varnames[:1] == ('self',):
                    kwargs[arg.__name__] = arg
                elif arg.__code__.co_argcount == 0:
                    kwargs.update(arg())
        self.__dict__.update(kwargs)
           
    def __call__(self, *args, **kwargs):
        return object(self, *args, **kwargs)

    def __contains__(self, name):
        return name in self.__dict__

    def __repr__(self):
        return repr(dict(self.__iter__()))

    def __iter__(self): #TESTME
        return ((name, value) for name, value in self.__dict__.iteritems() if not name.startswith("_"))

    def update(self, kws):
        return self.__dict__.update(kws)

from autotest import autotest

@autotest
def CreateObject1():
    o = object()
    assert o
    o = object(a=1)
    assert o.a == 1
    o1 = object(o)
    assert o1.a == 1
    o1 = object(o, a=2)
    assert o1.a == 2
    o2 = object(o1, f=lambda self: 42)
    assert o2.f() == 42
    def f(self): return 84
    o2 = object(o1, f=f)
    assert o2.f() == 84
    def g(self, x): return 2 * x
    o2 = object(o1, f, g)
    assert o2.f() == 84
    assert o2.g(9) == 18
    def ctor():
        return {"a": 23}
    o3 = object(o2, ctor)
    assert o3.a == 23, o3.a

@autotest
def This():
    @object
    def Obj():
        def f(self):
            return self, self.this
        return locals()
    assert Obj.f() == (Obj, Obj)
    @Obj
    def Obj2():
        return locals()
    assert Obj2.f() == (Obj2, Obj)

@autotest
def CreateObjectFromPrototype():
    creature = object(alive=True)
    @creature
    def person():
        def age(self): return 2015 - self.birth
        return locals()
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
    def p1():
        prop = 1 + 2
        prak = "aa"
        def f(self): return self.this
        return locals()
    assert p1
    assert p1.f()
    assert p1 == p1.f()
    assert p1.prop == 3, p1.prop
    assert p1.prak == "aa"
    @p1
    def p2():
        def g(self): return self
        return locals()
    assert p2
    assert p2.__prototypes__ == (p2, p1), p2.__prototypes__
    assert p2.prop == 3
    assert p2.f() == p1
    assert p2.g() == p2

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
    def one():
        def f(self):
            return autotest
        return locals()
    assert one.f() == autotest

@autotest
def AccessProperties():
    o = object(a=1, b=2)
    assert "a" in o
    assert "b" in o
    assert "c" not in o
    assert str(o) == "{'a': 1, 'b': 2}", str(o)

@object
def o0():
    pass
    return locals()

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
    def x():
        a=2
        return locals()
    assert x.a == 2

@autotest
def FindFunctionsNoLuckWithLocals():
    a = 42
    def F(b, c=84, *args, **kwargs):
        d = a
        e = b
        f = c
        def G(g, h=21, *orgs, **kworgs):
            i = a
            j = b
            k = c
            l = d
            m = e
            n = f
            o = g
            p = h
            return 63
        return locals()
    F(12)
    #my_F = FunctionType(code, globals, name, argdefaults, closure)
    assert F.__closure__[0].cell_contents == 42
    assert F.__defaults__ == (84,)
    assert F.__dict__ == {}
    assert F.__class__ == FunctionType
    assert F.__globals__ == globals()
    C = F.__code__
    assert C.co_argcount == 2
    assert C.co_consts[0] == None
    assert C.co_consts[1] == 21
    #assert C.co_consts[3] == 75
    assert C.co_cellvars == ('b', 'c', 'd', 'e', 'f')
    assert C.co_flags == 31, C.co_flags # 19 = no *args/**kwargs 23 = *args, 27 = **kwargs, 31 = *args + **kwargs
    assert C.co_freevars == ('a',)
    assert C.co_name == 'F'
    assert C.co_names == ('locals',), C.co_names
    assert C.co_nlocals == 5, C.co_nlocals
    assert C.co_stacksize == 7 # ??
    assert C.co_varnames == ('b', 'c', 'args', 'kwargs', 'G'), C.co_varnames
    G = C.co_consts[2]
    assert G.co_argcount == 2
    assert G.co_consts == (None, 63)
    assert G.co_cellvars == (), G.co_cellvars
    assert G.co_flags == 31, G.co_flags # 1=optimized | 2=newlocals | 4=*arg | 8=**arg
    assert G.co_freevars == ('a', 'b', 'c', 'd', 'e', 'f'), G.co_freevars
    assert G.co_name == 'G'
    assert G.co_names == (), G.co_names
    assert G.co_nlocals == 12, G.co_nlocals
    assert G.co_stacksize == 1, G.co_stacksize
    assert G.co_varnames == ('g', 'h', 'orgs', 'kworgs', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p'), G.co_varnames
  
    G_globals = F.__globals__
    G_globals.update(locals())
    G_arg_defaults = {} # ??
    G_closure = () # values for freevars come from globals
    G_closure = tuple(G_globals.get(var, "%s?" % var) for var in G.co_freevars)

    l = {}
    g = globals()
    eval("F(13)", g, l)
    assert g == globals()
    assert l == {}


@autotest
def WithClass():
    a = 42
    class _:
        b = a
        def G(c, d=21, *orgs, **kworgs):
            e = a
            f = b
            g = c
            h = d
            return 63

    assert _.__dict__["b"] == 42
    G = _.__dict__["G"]
    assert G.__closure__[0].cell_contents == 42, G.__closure__


@autotest
def SimplerWithFunctionsAsProperties():
    o = object()
    def f(self):
        return "Hello!"
    o2 = o(f=f)
    assert o2.f() == "Hello!"
    def g(self):
        return "Goodbye!"
    o3 = o(f, g)
    assert o3.f() == "Hello!"
    assert o3.g() == "Goodbye!"
