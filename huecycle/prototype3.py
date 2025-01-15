from inspect import isfunction, signature
from functools import partial
from collections import ChainMap

import selftest

test = selftest.get_tester(__name__)


""" Introduces the notion of delegetion or prototyping to Python. The goals are:
    1. Have an easier model for looking up properties and methods as compared
       to the Python MRO and the hard to grasp multiple inheritance and 
       metaclasses. This is accomplished by:
       A. removing the distinction between classes an objects entirely,
       B. object creation is by calling things, using "class" is syntactic sugar,
       C. unify dot notation (.attr) and bracket notion ([attr]) for lookup,
       D. attribute lookup follow the order of prototypes, depth first.

    2. More easily define or redefine properties with less code:
       A. an object with some properties: a = prototype(a=10, b=7, ...)
       B. call it to get a derived object: b = a(b=9)
       C. a method is any function accepting self (and optionally this)
          a = prototype(f=lambda self: return 42)
          a.g = g_defined_elsewhere
        
    3. keep it as close to Python as possible,
       A. a prototype object is just a Python dict,
       B. it behaves as normal as possible, except for attribute lookup
    4. when needed, stay close to Javascript, as possible.
       A. This applies mostly to the distinction between self and this.

       TODO Python          Javascript            Scope       Filtering
            __contains__    in                      self        -
            __iter__        for...in                self        str keys/enumerable
            __getitem__     []                      self        ?
            __len__         ?
            keys()          keys()                  this        enumerable
            values()        values()                this        enumerable
            items()         entries()               this        enumerable
                            getOwnPropertyNames()   this        str keys
                            getOwnPropertySymbols() this        -
                            ownKeys()               this        -
                            assign()                this        enumerable
            **              ...                     this        enumerable

        Prototype does not distinguish between enumerable and other attributes.
        It could by having an extra dict/removing __slots__ and/or skipping
        any attributes starting with '_', to keep it Pythonic.

"""


class meta(type):
    def __new__(claz, name, bases, namespace, **attributes):
        # Create the prototype class itself
        if name == "prototype":
            return super().__new__(claz, name, bases, namespace)

        # Support top level prototype object with "class X(prototype):"
        if bases == (prototype,):
            bases = ()

        # Turn class definition into new prototype object
        return prototype(name, bases, namespace, **attributes)


class prototype(dict, metaclass=meta):
    __slots__ = ("prototypes", "__id__")

    @classmethod
    def __subclasshook__(subclass):
        print("__subclasshook__", subclass)

    def __mro_entries__(this, bases):
        # Enable inheritance from (prototype) objects
        assert all(type(b) is prototype for b in bases), bases
        return bases

    def __init__(
        this, __id__="<anonymous>", prototypes=(), namespace=None, **attributes
    ):
        assert isinstance(__id__, str), __id__

        # Called via meta, during a class statement
        if namespace:
            this.prototypes = namespace.pop("__orig_bases__", prototypes)
            this.__id__ = (
                namespace.pop("__module__") + "." + namespace.pop("__qualname__")
            )
            super().__init__(namespace, **attributes)

        # Called directly, inline object creation
        else:
            this.prototypes = prototypes
            this.__id__ = __id__
            super().__init__(attributes)

    def __getattr__(this, name):
        # Non-existing attributes return None
        try:
            # Our this becomes 'self' for the prototypes being visited later
            return this._get_attr_ex(name, this)
        except AttributeError:
            return None

    def _get_attr_ex(this, name, self):
        try:
            # Try get the attribute from ourself
            attribute = super().__getitem__(name)
        except KeyError:
            pass

        # When found, handle descriptors, methods, etc
        else:
            # Prototypes can contain other prototypes
            if type(attribute) is prototype:
                return attribute

            # Bind 'this' if declared as second positional argument
            if isfunction(attribute):
                attribute.__signature__ = s = signature(attribute)  # will be cached
                if "this" in s.parameters:
                    return partial(attribute, self, this)

            # Support for properties/descriptions, including functions
            if hasattr(attribute, "__get__"):
                return attribute.__get__(self)

            # Wrap dicts (and replace!) with prototype
            if type(attribute) is dict:
                attribute = prototype(self.__id__ + "." + name, **attribute)
                setattr(this, name, attribute)

            # Nothing special
            return attribute

        # When not found, lookup the attribute in our prototypes, in order
        for p in this.prototypes:
            try:
                # Recursively traverse up if p is a prototype
                if type(p) is prototype:
                    return p._get_attr_ex(name, self)

                # Just get attr from anything else
                else:
                    return getattr(p, name)

            except AttributeError:
                continue

        # All fails
        raise AttributeError(name)

    def __setattr__(this, name, value):
        # Internal, set values for private attrs
        if name in this.__slots__:
            object.__setattr__(this, name, value)

        # Everything is set on 'this' (not self)
        else:
            this[name] = value

    def __delattr__(self, name):
        # Like __getattr__, we can delete non-existing attributes
        try:
            del self[name]
        except KeyError:
            pass

    __getitem__ = __getattr__

    def __call__(self, __id__="<anonymous>", **attributes):
        # Call a prototype to create a new prototype based on it
        return prototype(__id__, (self,), **attributes)

    def __eq__(self, rhs):
        # Do some elaborate checks iff we meet a friend
        if isinstance(rhs, prototype):
            return (
                self.prototypes == rhs.prototypes
                and self.__id__ == rhs.__id__
                and super().__eq__(rhs)
            )

        # Otherwise, compare to dict
        return super().__eq__(rhs)

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __contains__(self, name):
        return hasattr(self, name)

    def __iter__(self):
        seen = set()
        for k in super().__iter__():
            seen.add(k)
            yield k
        for p in self.prototypes:
            for k in p:
                if not k in seen:
                    seen.add(k)
                    yield k

    def __str__(self):
        return f"{self.__id__}{super().__str__()}"

    @property
    def dict(self):
        # Provide a dict view for destructuring as **<dict> uses shortcuts
        return ChainMap(self, *self.prototypes)


@test
def prototype_itself():
    assert issubclass(prototype, dict)
    assert isinstance(prototype, meta)
    assert isinstance(prototype, type)
    assert ("prototypes", "__id__") == prototype.__slots__
    assert prototype.__bases__ == (dict,)
    assert not hasattr(prototype, "doesnotexists")


def assert_invariants(o):
    assert isinstance(o, dict)
    assert isinstance(o, prototype)
    assert "__module__" not in o.keys()
    assert "__qualname__" not in o.keys()
    assert "__bases__" not in o.keys()
    assert hasattr(o, "prototypes")
    assert hasattr(o, "__id__")
    # assert not hasattr(o, 'doesnotexists')  # return None
    assert not o.doesnotexists


@test
def create_prototype():
    class creature(prototype):
        legs = 4

    assert_invariants(creature)
    assert () == creature.prototypes
    assert creature.legs == 4
    assert creature["legs"] == 4
    assert "legs" in creature
    assert {"legs"} == creature.keys()
    assert [4] == list(creature.values())
    assert {("legs", 4)} == creature.items()
    assert {"legs": 4} == creature, creature
    fullname = __name__ + "." + "create_prototype.<locals>.creature"
    assert fullname == creature.__id__, creature.__id__
    assert fullname + "{'legs': 4}" == str(creature), creature


@test
def set_attribute():
    class creature(prototype):
        birth = 2000

    assert creature.birth == 2000
    creature.birth = 2001
    assert creature.birth == 2001
    creature["birth"] = 2014
    assert creature.birth == 2014
    assert "birth" in creature
    assert {"birth"} == creature.keys()
    assert [2014] == list(creature.values())
    assert {("birth", 2014)} == creature.items()


@test
def create_object_with_prototype():
    class creature(prototype):
        legs = 4

    class person(creature):
        birth = 2003

    assert_invariants(person)
    assert (creature,) == person.prototypes
    assert person.birth == 2003
    assert person.legs == 4
    assert person["legs"] == 4
    assert "legs" in person
    assert {"birth"} == person.keys(), person.keys()
    assert [2003] == list(person.values())
    assert {("birth", 2003)} == person.items()
    assert str(person).endswith(
        "create_object_with_prototype.<locals>.person{'birth': 2003}"
    )
    assert ["birth", "legs"] == [k for k in person]
    person.legs = 2
    assert person.legs == 2
    assert creature.legs == 4
    assert str(person).endswith(
        "create_object_with_prototype.<locals>.person{'birth': 2003, 'legs': 2}"
    )
    assert {"birth", "legs"} == person.keys(), person.keys()
    assert {2003, 2} == set(person.values())
    assert {("birth", 2003), ("legs", 2)} == person.items()


@test
def object_with_more_prototypes():
    class creature(prototype):
        birth = 2001

    class vertibrate(creature):
        has_spine = True

    class warmblooded(creature):
        temperature = 36

    class mammal(warmblooded, vertibrate):
        pass

    assert_invariants(mammal)
    assert mammal.prototypes == (warmblooded, vertibrate)
    assert mammal.birth == 2001
    assert mammal.temperature == 36
    assert mammal.has_spine == True
    mammal.temperature = 37
    assert mammal.temperature == 37
    assert warmblooded.temperature == 36
    creature.birth = 2020
    assert mammal.birth == 2020


@test
def functions_methods():
    class creature(prototype):
        def age(self):
            return 2023 - self.birth

    assert_invariants(creature)
    age = creature.age
    creature.birth = 2020
    assert 3 == age()


@test
def proper_self():
    class janssen(prototype):
        name = "janssen"

        def fullname(self, this):
            return self.name + " " + this.name

    class karel(janssen):
        name = "karel"

    fullname = karel.fullname()
    assert "karel janssen" == fullname, fullname


@test
def optional_attributes():
    class automobile(prototype, wheels=4):
        pass

    assert_invariants(automobile)
    assert () == automobile.prototypes
    assert 4 == automobile.wheels

    class volvo(automobile, wheels=3):
        pass

    assert_invariants(volvo)
    assert (automobile,) == volvo.prototypes
    assert 3 == volvo.wheels


@test
def clone_directly_by_calling():
    automobile = prototype(wheels=4)
    assert_invariants(automobile)
    assert 4 == automobile.wheels
    assert () == automobile.prototypes
    volvo = automobile(wheels=3)
    assert_invariants(volvo)
    assert 3 == volvo.wheels
    assert (automobile,) == volvo.prototypes, volvo.prototypes


@test
def prototype_equality_using_class():
    class creature(prototype):
        birth = 2001

    class vertibrate(creature):
        has_spine = True

    assert creature != vertibrate

    class warmblooded(creature):
        temperature = 36

    assert warmblooded != vertibrate

    class mammal(warmblooded, vertibrate):
        pass

    assert mammal != warmblooded
    assert mammal != vertibrate

    class dog1(mammal):
        pass

    assert dog1 != mammal

    class dog2(mammal):
        pass

    assert dog1 != dog2  # NB!
    assert dog1.__id__ != dog2.__id__
    assert (
        dog1.__id__ == __name__ + "." + "prototype_equality_using_class.<locals>.dog1"
    ), dog1.__id__
    assert (
        dog2.__id__ == __name__ + "." + "prototype_equality_using_class.<locals>.dog2"
    ), dog1.__id__
    try:
        assert {dog1}
        assert False
    except TypeError as e:
        assert "unhashable type: 'prototype'" == str(e)


@test
def prototype_equality_anonymous_cloning():
    creature = prototype(birth=2001)
    vertibrate = creature(has_spine=True)
    assert creature != vertibrate
    warmblooded = creature(temperature=36)
    assert warmblooded != vertibrate
    mammal = prototype(prototypes=(warmblooded, vertibrate))
    assert mammal != warmblooded
    assert mammal != vertibrate
    dog1 = mammal()
    assert dog1 != mammal
    dog2 = mammal()
    assert dog1 == dog2  # NB!
    assert dog1.__id__ == dog2.__id__
    dog1.name = "Oscar"
    assert dog1 != dog2
    assert dog1.__id__ == dog2.__id__
    try:
        assert {dog1}
        assert False
    except TypeError as e:
        assert "unhashable type: 'prototype'" == str(e)


@test
def all_values_in_one_dict():
    creature = prototype(birth=2001)
    vertibrate = creature(has_spine=True)
    assert vertibrate.prototypes == (creature,), vertibrate.prototypes
    # NB Python ignores keys/__getitem__ on **<dict> so no **vertibrate
    d = dict(**vertibrate.dict)
    assert {"has_spine": True, "birth": 2001} == d, d
    dog = vertibrate(birth=2013)
    d = dict(**dog.dict)
    assert {"has_spine": True, "birth": 2013} == d, d


@test
def delegete_to_python_objects():
    # This is nice for mocking in tests
    woordjes = prototype(
        "woordjes",
        prototypes=("aap noot mies",),
        # Override capitalize, which is called in this test
        capitalize=lambda self: " ".join(s.capitalize() for s in self.splitlines()),
        # Override splitlines, which is called by capitalize
        splitlines=lambda self: self.split(" "),
    )
    assert woordjes.prototypes == ("aap noot mies",), woordjes
    assert True == woordjes.startswith("aa")
    assert ["aap noot mies"] == "aap noot mies".splitlines()
    assert ["aap", "noot", "mies"] == woordjes.splitlines()
    assert "Aap noot mies" == "aap noot mies".capitalize()
    assert "Aap Noot Mies" == woordjes.capitalize()


@test
def turn_dict_into_prototype():
    service = prototype("service", props={"a": 42})
    light = service("light")
    assert light.__id__ == "light"
    props = light.props
    assert props == {"a": 42}, props
    assert isinstance(props, prototype)
    assert props.a == 42
    assert props["a"] == 42
    assert props.__id__ == "light.props", props.__id__
    props["b"] = 43
    assert props.b == 43
    assert {"a": 42, "b": 43} == props, props
    props_again = light.props
    assert props_again == {"a": 42, "b": 43}, props_again
    assert props is props_again

    assert service.props is light.props


@test
def properties():
    class aap(prototype):
        n = 10

        @property
        def one(self):
            return f"<{self.n}>"

        two = property(lambda self: f">{self.n}<")
        tri = property("({n})".format_map)  # nice idiom ?

        def fort(self):
            return f"one:{self.one}"

    test.eq("<10>", aap.one)
    test.eq(">10<", aap.two)
    test.eq("(10)", aap.tri)
    test.eq("one:<10>", aap.fort())

    class noot(aap):
        n = 11

    test.eq("<11>", noot.one)


@test
def del_attribute():
    class aap(prototype):
        a = 10

    class noot(aap):
        a = 32

    test.eq(aap.a, 10)
    test.eq(noot.a, 32)
    del noot.a
    test.eq(aap.a, 10)
    test.eq(noot.a, 10)
    del noot.a
    with test.raises(KeyError):
        del noot["a"]
    test.eq(noot.a, 10)


@test
def getattr_returns_none():
    class boom(prototype):
        pass

    test.eq(None, boom.a)


@test
def iter_unique():
    p0 = prototype(a=10)
    p1 = p0(a=11)
    test.eq(["a"], [a for a in p1])


# @test
def ununumerable_attrs():
    class a(prototype):
        _x = 10

    test.eq(None, a._x)
