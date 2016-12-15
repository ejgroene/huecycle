from types import FunctionType, MethodType, ClassType
from inspect import isbuiltin, isclass

object_ = object # Yes, this module redefines the meaning of object

def find_attr(self, prototypes, name):
    for prototype in prototypes:
        try:
            attribute = object_.__getattribute__(prototype, name)
        except AttributeError:
            continue
        if isinstance(attribute, FunctionType):
            return  MethodType(attribute, __self__(self, prototype))
        if isinstance(attribute, dict):
            return object(self, **dict((str(k),v) for k,v in attribute.iteritems()))
        return attribute

class __self__(object_):

    def __init__(self, __self__, __this__):
        self.__self__ = __self__
        self.__this__ = __this__

    @property
    def next(self):
        return __defer__(self.__self__, self.__this__.__prototypes__[1:])

    @property
    def this(self):
        return __defer__(self.__self__, self.__this__.__prototypes__)

    def __getattribute__(self, name):
        if name.startswith("__") or name in ("next", "this"):
            return object_.__getattribute__(self, name)
        return find_attr(self.__self__, self.__self__.__prototypes__, name)

    def __setattr__(self, name, value):
        if name.startswith("__"):
            return object_.__setattr__(self, name, value)
        setattr(self.__self__, name, value)

    def __eq__(self, rhs): 
        return rhs == self.__self__

    def __call__(self, *args, **kwargs):
        return self.__self__.__call__(*args, **kwargs)

    def __contains__(self, name):
        return name in self.__self__

    def __getitem__(self, name):
        return self.__self__[name]

    def __repr__(self):
        return repr(self.__self__)

class __defer__(object_):

    def __init__(self, __self__, __prototypes__):
        self.__self__ = __self__
        self.__prototypes__ = __prototypes__

    def __getattribute__(self, name):
        if name.startswith("__"):
            return object_.__getattribute__(self, name)
        return find_attr(self.__self__, self.__prototypes__, name)

class object(object_):

    def __getitem__(self, name):
        return getattr(self, str(name)) 

    def __getattribute__(self, name):
        if name.startswith("__"):
            return object_.__getattribute__(self, name)
        return find_attr(self, self.__prototypes__, name)

    def __init__(self, *prototypes_or_functions, **attributes):
        self.__prototypes__ = (self,)
        for arg in prototypes_or_functions:
            # delegate to given object
            if isinstance(arg, object):
                self.__prototypes__ += arg.__prototypes__
            # delegate to given object via self
            elif isinstance(arg, __self__):
                self.__prototypes__ += arg.__self__.__prototypes__
            elif isinstance(arg, FunctionType):
                # add given function as attribute (method)
                if arg.__code__.co_varnames[:1] == ('self',):
                    attributes[arg.__name__] = arg
                # use given function as factory for attributes
                elif arg.__code__.co_argcount == 0:
                    attributes.update(arg())
                else:
                    raise Exception("function '%s' must accept no args or first arg must be 'self'" % arg.__name__)
            # use given old style Python class as source for attributes
            elif isinstance(arg, ClassType):
                attributes = arg.__dict__
            # delegate to new style Python class or object
            elif isinstance(arg, type) or \
                    isinstance(arg, object_) and type(arg).__module__ != '__builtin__': 
                self.__prototypes__ += (arg,)
            else:
                raise Exception("arg '%s' must be a constructor, prototype, function or class" % arg)
        self.__dict__.update(attributes)
           
    def __call__(self, *prototypes_or_functions, **attributes):
        return object(self, *prototypes_or_functions, **attributes)

    def __contains__(self, name):
        return name in self.__dict__

    def __repr__(self):
        return repr(dict(self.__iter__()))

    def __iter__(self):
        return ((name, value) for name, value in self.__dict__.iteritems() if not name.startswith("_"))

    def update(self, attributes):
        return self.__dict__.update(attributes)

from autotest import autotest

@autotest
def CheckFunctions():
    def f(not_self, a, b=10):
        pass
    try:
        object(f)
        assert False
    except Exception as e:
        assert str(e) == "function 'f' must accept no args or first arg must be 'self'", e
    def g(a, b):
        pass
    try:
        object(g)
        assert False
    except Exception as e:
        assert str(e) == "function 'g' must accept no args or first arg must be 'self'"
    try:
        object('10')
        assert False
    except Exception as e:
        assert str(e) == "arg '10' must be a constructor, prototype, function or class", e


@autotest
def UseTwoPrototypes():
    def f1(self):
        return "f1"
    o1 = object(f1)
    def f2(self):
        return "f2"
    o2 = object(f2)
    o3 = object(o1, o2)
    assert o3.f1() == "f1"
    assert o3.f2() == "f2"
    def f2(self):
        return "new f2"
    o4 = object(f2)
    o5 = object(o3, o4)
    assert o5.f2() == "f2"
    o5 = object(o4, o3)
    assert o5.f2() == "new f2"
    def f2(self):
        return "own f2"
    o6 = object(o5, o4, o3, o2, o1, f2)
    assert o6.f2() == "own f2"
    assert o6.f1() == "f1"
    
@autotest
def SelfAsPrototype():
    def f(self):
        return "f"
    def g(self):
        o1 = self()
        o2 = object(self)
        return o1, o2
    o = object(f, g)
    x, y = o.g()
    assert x.f() == "f", x.f()
    assert y.f() == "f", y.f()

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
    o3 = object(o2, lambda self: 23, lambda self: 56, lambda: {"x": 89})
    assert o3["<lambda>"]() == 56  #yuk
    assert o3.x == 89

@autotest
def This():
    @object
    def Obj():
        a = 42
        def f(self):
            return self, self.this.g()
        def g(self):
            return self.a
        return locals()
    assert Obj.f() == (Obj, 42), Obj.f()
    assert Obj.g() == 42
    @Obj
    def Obj1():
        def g(self):
            return 2 * self.next.g()
        return locals()
    @Obj1
    def Obj2():
        def f(self):
            return self.next.f()
        def g(self):
            self.a = 12
            return self.next.g() * 2
        return locals()
    assert Obj2.f() == (Obj2, 42), Obj2.f()
    assert Obj2.g() == 48, Obj2.g()

@autotest
def CreateFromOldStyleClass():
    @object
    class obj: # strange but convenient syntax?
        a = 42
        def f(self):
            return 54
    assert obj.a == 42
    assert obj.f() == 54

@autotest
def DelegateToNormalPythonClass():
    class A(object_):
        c = 10
        def f(self):
            return 42
        def g(self):
            return self.b # Oh yeah!
    assert isinstance(A, type)
    o = object(A, b=67)
    assert o.f() == 42
    assert o.b == 67
    assert o.g() == 67
    assert o.c == 10

@autotest
def DelegateToNormalPythonInstance():
    class A(object_):
        c = 16
        def f(self):
            return 23
        def g(self):
            return self.d
    a = A()
    a.d = 8
    assert isinstance(a, object_)
    o = object(a)
    assert o.f() == 23
    assert o.c == 16
    assert o.d == 8
    assert o.g() == 8

@autotest
def CreateObjectFromPrototype():
    creature = object(alive=True)
    @creature
    class person():
        def age(self): return 2015 - self.birth
    me = object(person, birth=1990)
    assert me.age() == 25, me
    assert me.alive == True
    me.alive = False
    assert me.alive == False
    assert creature.alive == True
    her = person(birth=1994) # nicer syntax
    assert her.age() == 21

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
        def f(self): return self.__this__
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

@autotest
def EmbeddedObjectCreationWithSelfAsDecorator():
    def f(self):
        @self
        def f():
            return {"a": 42}
        return f
    o = object(f, a=24)
    assert o.f().a == 42

@autotest
def Contains():
    def f(self, a):
        return a in self
    o = object(f, a=10)
    assert 'a' in o
    assert o.f('a')
    assert not o.f('b')


@autotest
def GetItem():
    def f(self, a):
        return self[a]
    o = object(f, a=29)
    assert o['a'] == 29
    assert o.f('a') == 29

@autotest
def Equals():
    def g(self):
        return self
    def f(self, a):
        return self == a and a == self
    o = object(f, g)
    assert o == o.g()
    assert o.g() == o
    assert o.f(o)
    assert not o.f(None)

@autotest
def IteratePublicAttributes():
    def f(self): pass
    def _g(self): pass
    o = object(f, _g, a=10, _b=20)
    assert [('f', f), ('a', 10)], list(o)

@autotest
def DictsBecomeObjects():
    o = object(a={'b':{'c':{'d':3}}})
    assert o.a.b.c.d == 3, o.a.b.c.d
    o = object(a={'b':{2:{'d':3}}})
    assert o.a.b[2].d == 3, o.a.b.c.d
