from autotest import autotest
from inspect import isfunction, signature
from functools import partial
from collections import ChainMap


class meta(type):

    def __new__(claz, name, bases, namespace, **attributes):
        if name == 'prototype':
            return super().__new__(claz, name, bases, namespace)
        if bases == (prototype,):
            return prototype(name, (), namespace | attributes)
        return prototype(name, bases, namespace | attributes)
        

class prototype(dict, metaclass=meta):
    """ root or terminal for all prototype, singleton """

    __slots__ = ('prototypes', 'id')

    def __mro_entries__(this, bases):
        return bases

    def __init__(this, id='<anonymous>', prototypes=(), namespace=None, **attributes):
        if namespace:
            this.prototypes = namespace.pop('__orig_bases__', prototypes)
            this.id = namespace.pop('__module__') + '.' + namespace.pop('__qualname__')
            super().__init__(namespace, **attributes)
        else:
            this.prototypes = prototypes
            this.id = id
            super().__init__(attributes)

    def __getattr__(this, name, self=None):
        self = this if self is None else self
        try:
            attribute = super().__getitem__(name)
        except KeyError:
            for p in this.prototypes:
                try:
                    if isinstance(p, prototype):
                        attribute = p.__getattr__(name, self=self)
                    else:
                        attribute = getattr(p, name)
                    break
                except AttributeError:
                    continue
            else:
                raise AttributeError
        if isfunction(attribute):
            s = signature(attribute)
            attribute.__signature__ = s # cache
            if 'this' in s.parameters:
                attribute = partial(attribute, self, this)
            else:
                attribute = partial(attribute, self)
        return attribute

    def __setattr__(this, name, value):
        if name in this.__slots__:
            object.__setattr__(this, name, value)
        else:
            this[name] = value

    def __call__(self, **attributes):
        return prototype(prototypes=(self,), **attributes)

    def __eq__(self, rhs):
        if isinstance(rhs, prototype):
            return self.prototypes == rhs.prototypes \
               and self.id == rhs.id \
               and super().__eq__(rhs)
        return super().__eq__(rhs)

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __str__(self):
        return self.id + super().__str__()

    @property
    def dict(self):
        return ChainMap(self, *self.prototypes)

    def __getitem__(self, name):
        return self.__getattr__(name)


@autotest
def prototype_itself():
    assert isinstance(prototype, meta)
    assert isinstance(prototype, type)
    assert ('prototypes', 'id') == prototype.__slots__
    assert prototype.__bases__ == (dict,)
    assert not hasattr(prototype, 'doesnotexists')

def assert_invariants(o):
    assert isinstance(o, dict)
    assert isinstance(o, prototype)
    assert '__module__' not in o
    assert '__qualname__' not in o
    assert '__bases__' not in o
    assert hasattr(o, 'prototypes')
    assert hasattr(o, 'id')
    assert not hasattr(o, 'doesnotexists')

@autotest
def create_prototype():
    class creature(prototype):
        legs = 4
    assert_invariants(creature)
    assert () == creature.prototypes
    assert creature.legs == 4
    assert creature['legs'] == 4
    assert {'legs': 4} == creature, creature
    fullname = __name__+'.'+'create_prototype.<locals>.creature'
    assert fullname == creature.id, creature.id
    assert fullname+"{'legs': 4}" == str(creature), creature

@autotest
def set_attribute():
    class creature(prototype):
        birth = 2000
    assert creature.birth == 2000
    creature.birth = 2001
    assert creature.birth == 2001
    creature['birth'] = 2014
    assert creature.birth == 2014

@autotest
def create_object_with_prototype():
    class creature(prototype):
        legs = 4
    class person(creature):
        birth = 2003
    assert_invariants(person)
    assert (creature,) == person.prototypes
    assert person.birth == 2003
    assert person.legs == 4
    assert person['legs'] == 4
    assert str(person).endswith("create_object_with_prototype.<locals>.person{'birth': 2003}")
    person.legs = 2
    assert person.legs == 2
    assert creature.legs == 4
    assert str(person).endswith("create_object_with_prototype.<locals>.person{'birth': 2003, 'legs': 2}")

@autotest
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
    
@autotest
def functions_methods():
    class creature(prototype):
        def age(self):
            return 2023 - self.birth
    assert_invariants(creature)
    age = creature.age
    creature.birth = 2020
    assert 3 == age()

@autotest
def proper_self():
    class janssen(prototype):
        name = "janssen"
        def fullname(self, this):
            return self.name + ' ' + this.name
    class karel(janssen):
        name = "karel"
    fullname = karel.fullname()
    assert "karel janssen" == fullname, fullname

@autotest
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

@autotest
def clone_directly_by_calling():
    automobile = prototype(wheels=4)
    assert_invariants(automobile)
    assert 4 == automobile.wheels
    assert () == automobile.prototypes
    volvo = automobile(wheels=3)
    assert_invariants(volvo)
    assert 3 == volvo.wheels
    assert (automobile,) == volvo.prototypes, volvo.prototypes
   
@autotest
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
    assert dog1 != dog2                     # NB!
    assert dog1.id != dog2.id
    assert dog1.id == __name__+'.'+'prototype_equality_using_class.<locals>.dog1', dog1.id
    assert dog2.id == __name__+'.'+'prototype_equality_using_class.<locals>.dog2', dog1.id
    try:
        assert {dog1}
        assert False
    except TypeError as e:
        assert "unhashable type: 'prototype'" == str(e)

@autotest
def prototype_equality_anonymous_cloning():
    creature = prototype(birth=2001)
    vertibrate = creature(has_spine=True)
    assert creature != vertibrate
    warmblooded = creature(temperature=36)
    assert warmblooded != vertibrate
    mammal = prototype(warmblooded, vertibrate)
    assert mammal != warmblooded
    assert mammal != vertibrate
    dog1 = mammal()
    assert dog1 != mammal
    dog2 = mammal()
    assert dog1 == dog2                       # NB!
    assert dog1.id == dog2.id
    dog1.name = 'Oscar'
    assert dog1 != dog2
    assert dog1.id == dog2.id
    try:
        assert {dog1}
        assert False
    except TypeError as e:
        assert "unhashable type: 'prototype'" == str(e)

@autotest
def all_values_in_one_dict():
    creature = prototype(birth=2001)
    vertibrate = creature(has_spine=True)
    assert vertibrate.prototypes == (creature,), vertibrate.prototypes
    # NB implementing keys/__getitem__ does not work due to Pyton optimizing dicts
    d = dict(**vertibrate.dict)
    assert {'has_spine': True, 'birth': 2001} == d, d
    dog = vertibrate(birth=2013)
    d = dict(**dog.dict)
    assert {'has_spine': True, 'birth': 2013} == d, d

@autotest
def delegete_to_python_objects():
    # makes no sense, but it is possible
    woordjes = prototype(prototypes=("aap",))
    assert woordjes.prototypes == ("aap",), woordjes
    assert True == woordjes.startswith('aa')

