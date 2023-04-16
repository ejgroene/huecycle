## begin license ##
#
# "Metastreams Json LD" provides utilities for handling json-ld data structures
#
# Copyright (C) 2022 Seecr (Seek You Too B.V.) https://seecr.nl
#
# This file is part of "Metastreams Json LD"
#
# "Metastreams Json LD" is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# "Metastreams Json LD" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "Metastreams Json LD"; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
## end license ##

from inspect import isfunction, currentframe
from operator import attrgetter
from functools import reduce
from pprint import pformat
from copy import copy
import sys

"""
         13669367 function calls (10903180 primitive calls) in 3.850 seconds

   Ordered by: internal time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
2946891/180704    1.900    0.000    3.640    0.000 jsonldwalk3.py:84(handle)
  6154520    0.422    0.000    0.422    0.000 {method 'get' of 'dict' objects}
   180704    0.235    0.000    2.067    0.000 jsonldwalk3.py:76(handle)
   391657    0.216    0.000    0.334    0.000 didl.py:25(map_predicate_to_ids_fn)
   180704    0.189    0.000    0.264    0.000 didl.py:100(literal_mainEntityOfPage)
   115554    0.173    0.000    0.181    0.000 didl.py:40(literal_workExample)
   500201    0.161    0.000    0.196    0.000 didl.py:129(<lambda>)
   391657    0.118    0.000    0.118    0.000 didl.py:26(<listcomp>)
   180704    0.077    0.000    3.717    0.000 jsonldwalk3.py:93(walk_fn)
   180704    0.075    0.000    0.075    0.000 didl.py:101(<listcomp>)
  1042350    0.071    0.000    0.071    0.000 jsonldwalk3.py:108(ignore_assert_fn)
   180704    0.066    0.000    3.783    0.000 didl.py:201(didl2schema)
   180704    0.046    0.000    0.067    0.000 cProfile.py:117(__exit__)
   500201    0.036    0.000    0.036    0.000 jsonldwalk3.py:115(ignore_silently)
   180704    0.022    0.000    0.022    0.000 jsonldwalk3.py:133(map_predicate_fn)
   180704    0.021    0.000    0.021    0.000 jsonldwalk3.py:128(identity)
   180704    0.021    0.000    0.021    0.000 {method 'disable' of '_lsprof.Profiler' objects}


LAST: 13f6f29c-09d0-11ed-8d25-9f009bfa3105
RECORDS: 191787
RATE: 8417.154533366092
"""


def iterate(f, v):
    while v:
        yield v
        v = f(v)


def trace(locals_from_stack):
    return "".join(
        f"\n{n*'-'}> {p}"
        for n, p in enumerate(lokals["__key__"] for lokals in locals_from_stack)
    )


def locals_with_key():
    return [
        fl
        for fl in (
            tb.tb_frame.f_locals
            for tb in iterate(attrgetter("tb_next"), sys.exc_info()[2])
        )
        if "__key__" in fl
    ]


def compile(rules):
    # recursively compile everything
    rules = copy(rules)
    for predicate, subrule in rules.items():
        if type(subrule) is dict:
            rules[predicate] = compile(subrule)
        else:
            pass

    get = rules.get
    if "*" in rules:
        default = rules["*"]
    else:
        keys = set(rules.keys()) if rules else {}

        def default(a, s, p=None, os=None):
            e = LookupError(f"No rule for '{p}' in {keys}")
            e.subject = (
                s if s is not None else os[0]
            )  # called by __switch__ without subject
            raise e

    all_rule = get("__all__")

    if "__key__" in rules:
        key_fn = rules["__key__"]

        def handle(accu, subject, predicate, objects):
            if all_rule is not None:
                accu = all_rule(accu, subject, predicate, objects)
            for subject in objects:
                for predicate in subject:
                    objects = subject[predicate]
                    __key__ = key_fn(accu, subject, predicate, objects)
                    accu = get(__key__, default)(accu, subject, predicate, objects)
            return accu

    elif "__switch__" in rules:
        switch_fn = rules["__switch__"]

        def handle(accu, subject, predicate, objects):
            if all_rule is not None:
                accu = all_rule(accu, subject, predicate, objects)
            for subject in objects:
                __key__ = switch_fn(accu, subject)
                accu = get(__key__, default)(accu, None, None, (subject,))
            return accu

    elif isinstance(rules, dict):
        # this is the thinnest bottleneck
        def handle(accu, subject, predicate, objects, **opts):
            if isinstance(objects, str):
                accu = rules[objects](accu, subject, objects, None, **opts)
                return accu
            if (
                all_rule is not None
            ):  # TODO move this check to compile time (use exec to dynamically compile handle with/out all_rule)
                accu = all_rule(accu, subject, predicate, objects)
            for subject in (objects,) if isinstance(objects, dict) else objects:
                for __key__ in subject:
                    accu = get(__key__, default)(
                        accu, subject, __key__, subject[__key__], **opts
                    )
            return accu

    else:
        raise Exception(f"Illegal rule: {rules!r}")
    return handle


def walk(rules, catch=True):
    w = compile(rules)

    def walk_fn(subject, accu=None, **opts):
        accu = {} if accu is None else accu
        try:
            return w(accu, None, None, (subject,), **opts)
        except Exception as e:
            if catch:
                locals_from_stack = locals_with_key()
                subject = locals_from_stack[-1].get("subject")
                raise Exception(
                    f"{e.__class__.__name__}: {str(e)} at:{trace(locals_from_stack)} while processing:\n{pformat(subject)}"
                ) from e
            raise e

    return walk_fn


""" Some auxilary rules (not tested here) on top of Walk, that are generic enough to place here. """


def do_assert(s, expected, param):
    if callable(expected) and expected(param) or expected == param:
        return True
    e = AssertionError(param)
    e.subject = s
    raise e


def ignore_assert(*, s=None, p=None, os=None):
    """ignores subtree, applying asserts when given"""
    assert s or p or os, "specify at least one assert, or use ignore_silently"

    def ignore_assert_fn(a, s_, p_, os_):
        # assert s is None or isfunction(s) and s(s_) or s == s_, s_A
        assert s is None or do_assert(s_, s, s_)
        assert p is None or do_assert(s_, p, p_)
        assert os is None or do_assert(s_, os, os_)
        return a

    return ignore_assert_fn


def ignore_silently(a, *_, **__):
    return a


def unsupported(_, __, p, ___):
    raise Exception(f"Unsupported predicate '{p}'")


def all_values_in(*values):
    vs = set(values)

    def all_values_in_fn(os):
        return all(o["@value"] in vs for o in os)

    return all_values_in_fn


""" Rules that *** work only with default accu={} *** """


def identity(a, _, p, os):
    a[p] = os
    return a


def map_predicate(p):
    def map_predicate_fn(a, _, __, os):
        a[p] = os
        return a

    return map_predicate_fn


def map_predicate2(p, normalize=tuple):
    def map_predicate_fn(a, _, __, os):
        old = a.setdefault(p, ())
        a[p] = old + normalize(os)
        return a

    return map_predicate_fn


def set_if_absent(a, s, p, os):
    if p not in a:
        a[p] = os
    return a


def append(a, s, p, os):
    a.setdefault(p, []).extend(os)
    return a


import autotest

test = autotest.get_tester(__name__)


@test
def simple_basics():
    r = []
    w = walk({"a": lambda *a: r.append(a)})
    w({"a": "whatever-is-here"})
    test.eq(({}, {"a": "whatever-is-here"}, "a", "whatever-is-here"), r.pop())
    w({"a": [42]})
    test.eq(({}, {"a": [42]}, "a", [42]), r.pop())


@test
def nested_rule():
    r = []
    w = walk(
        {
            "a": {
                "b": {
                    "c": lambda *a: r.append(a),
                },
            },
        }
    )
    w({"a": [{"b": [{"c": 42}]}]})
    test.eq(({}, {"c": 42}, "c", 42), r.pop())
    with test.raises(
        Exception,
        "TypeError: 'int' object is not iterable at:\n> a\n-> b while processing:\n{'b': 42}",
    ):
        w({"a": [{"b": 42}]})


# @test
def modifying_input_is_not_allowed():
    r = []
    rules = {
        "a/a": lambda a, s, p, o: r.append(s.pop("a/b") * o),
        "a/b": ignore_silently,
    }
    j0 = {"a/b": 2, "a/a": 42}
    # with test.raises(Exception, "RuntimeError: dictionary changed size during iteration at: "):
    try:
        walk(rules)(j0)
    except Exception as e:
        print(type(e))
        print(repr(e))


@test
def default_rule():
    r = []
    rules = {"*": lambda a, s, p, o: r.append((p, "default"))}
    j0 = {"a/a": 42, "a/b": 2}
    walk(rules)(j0)
    test.eq(("a/b", "default"), r.pop())
    test.eq(("a/a", "default"), r.pop())

    # should have same result
    w = walk({"a": rules})
    w({"a": [j0]})
    test.eq(("a/b", "default"), r.pop())
    test.eq(("a/a", "default"), r.pop())

    # should have same result
    w = walk({"*": rules})
    w({"a": [j0]})
    test.eq(("a/b", "default"), r.pop())
    test.eq(("a/a", "default"), r.pop())


@test
def values():
    r = []
    rules = {
        "@value": lambda *a: r.append(a),  # returns None
        "*": lambda *a: r.append(a),
    }
    w = walk(rules)
    s = {"@value": "hello", "b/b": [{"id": "16"}]}
    w(s)
    test.eq((None, s, "b/b", [{"id": "16"}]), r.pop())
    test.eq(({}, s, "@value", "hello"), r.pop())

    # should have same result
    w = walk({"a": rules})
    w({"a": [s]})
    test.eq((None, s, "b/b", [{"id": "16"}]), r.pop())
    test.eq(({}, s, "@value", "hello"), r.pop())


@test
def reduce_returned_values():
    j = {"a": 42, "b": 16}
    r = walk({"a": lambda a, s, p, o: o, "*": lambda a, s, p, o: [42, (p, o)]})(j)
    test.eq([42, ("b", 16)], r)


@test
def my_accu_plz():
    a = {}
    id_a = id(a)
    r = walk({"*": lambda a, s, p, os: a})({"a": 10}, accu=a)
    test.eq(id_a, id(r))


# @test
def pass_args():
    r = Walk(
        {"*": lambda a, s, p, os, x, y, z=42: a | {"x": x, "y": y, "z": z}}
    ).subject({1: 2}, 3, 4, z=5)
    test.eq({"x": 3, "y": 4, "z": 5}, r)


@test
def append_to_list():
    w = walk({"*": append})
    r = w({"a": [1]})
    r = w({"a": [2]}, accu=r)
    test.eq({"a": [1, 2]}, r)


@test
def custom_key():
    r = []
    q = []
    rules = {
        "__key__": lambda *a: r.append(a),  # returns None
        None: lambda *a: q.append(a),
    }
    w = walk(rules)
    w({"a": 42})
    test.eq(({}, {"a": 42}, "a", 42), r.pop())
    test.eq(({}, {"a": 42}, "a", 42), q.pop())

    # should have same results
    w = walk({"b": rules})
    w({"b": [{"a": 42}]})
    test.eq(({}, {"a": 42}, "a", 42), r.pop())
    test.eq(({}, {"a": 42}, "a", 42), q.pop())

    # should have same results
    w = walk({"b": rules, "__key__": lambda a, s, p, os: p})
    w({"b": [{"a": 42}]})
    test.eq(({}, {"a": 42}, "a", 42), r.pop())
    test.eq(({}, {"a": 42}, "a", 42), q.pop())


@test
def custom_key_with_subwalk():
    r = []
    w = walk({"__key__": lambda a, s, p, os: p, "a": {"b": lambda *a: r.append(a)}})
    w({"a": [{"b": "identiteit"}]})
    test.eq(({}, {"b": "identiteit"}, "b", "identiteit"), r.pop())


def append(os=None):
    def append_fn(a, s, p, os_):
        a.setdefault(os, []).extend(os_)
        return a

    return append_fn


@test
def switch_toplevel():
    r1 = []
    r2 = []
    rules = {
        "__switch__": lambda a, s: s["@type"][0],
        "numbers": lambda *a: r1.append(a),
        "strings": lambda *a: r2.append(a),
    }
    w = walk(rules)
    w(
        {
            "@type": ["numbers"],
            "a": [42],
        }
    )
    test.eq(({}, None, None, ({"@type": ["numbers"], "a": [42]},)), r1.pop())
    test.eq([], r2)
    w(
        {
            "@type": ["strings"],
            "a": ["42"],
        }
    )
    test.eq([], r1)
    test.eq(({}, None, None, ({"@type": ["strings"], "a": ["42"]},)), r2.pop())

    # should have same results
    w = walk({"z": rules})
    w(
        {
            "z": [
                {
                    "@type": ["numbers"],
                    "a": [42],
                }
            ]
        }
    )
    test.eq(({}, None, None, ({"@type": ["numbers"], "a": [42]},)), r1.pop())
    test.eq([], r2)
    w(
        {
            "z": [
                {
                    "@type": ["strings"],
                    "a": ["42"],
                }
            ],
        }
    )
    test.eq([], r1)
    test.eq(({}, None, None, ({"@type": ["strings"], "a": ["42"]},)), r2.pop())


@test
def switch_with_dict():
    w = walk(
        {
            "__switch__": lambda a, s: s["base"][0]["@value"],
            2: {
                "base": ignore_silently,
                "x": lambda a, s, p, os: a
                | {"result": [{"@value": 2 ** o["@value"]} for o in os]},
            },
            8: {
                "base": ignore_silently,
                "x": lambda a, s, p, os: a
                | {"result": [{"@value": 8 ** o["@value"]} for o in os]},
            },
        }
    )
    r = w({"base": [{"@value": 2}], "x": [{"@value": 3}]})
    test.eq({"result": [{"@value": 8}]}, r)
    r = w({"base": [{"@value": 8}], "x": [{"@value": 3}]})
    test.eq({"result": [{"@value": 512}]}, r)


@test
def swith_in_swith():
    w = walk(
        {
            "__switch__": lambda a, s: s["a"],
            "1": {
                "__switch__": lambda a, s: s["x"][0]["y"][0],
                "koel": {
                    "a": ignore_assert(os="1"),
                    "x": identity,
                },
            },
        }
    )
    r = w({"a": "1", "x": [{"y": ["koel"]}]})
    test.eq({"x": [{"y": ["koel"]}]}, r)


@test
def with_type():
    r = []
    w = walk(
        {
            "__switch__": lambda *a: r.append(a),
            None: {"@type": identity},
        }
    )
    w({"@type": ["whatever-is-here"]})
    test.eq(({"@type": ["whatever-is-here"]}, {"@type": ["whatever-is-here"]}), r.pop())


@test
def subwalk_from_mods():
    w = walk(
        {
            "__switch__": lambda a, s: s["@type"][0],
            "personal": {"@type": lambda a, s, p, os: a | {"type is": os}},
        }
    )
    r = w(
        {
            "@type": ["personal"],
        }
    )
    test.eq({"type is": ["personal"]}, r)


@test
def builtin_subwalk():
    w = walk({"a": {"b": identity}})
    r = w({"a": [{"b": 41}]})
    test.eq({"b": 41}, r)  # NB subwalk flattens


@test
def builtin_subwalk_stack_for_errors():
    w = walk(
        {
            "a": {"b": identity},
            "b": {
                "c": identity,
                "d": {},
            },
        }
    )
    with test.raises(
        Exception,
        "LookupError: No rule for 'e' in {} at:\n> b\n-> d\n--> e while processing:\n{'e': 42}",
    ):
        w({"b": [{"d": [{"e": 42}]}]})
    with test.raises(
        Exception,
        "LookupError: No rule for 'X' in {'b'} at:\n> a\n-> X while processing:\n{'X': [{'e': 42}]}",
    ):
        w({"a": [{"X": [{"e": 42}]}]})


##### More elaborate tests from old processor #####

from pyld import jsonld

dcterms = "http://purl.org/dc/terms/"
foaf = "http://xmlns.com/foaf/0.1/"
schema = "http://schema.org/"


def expand(data):
    """test helper"""
    data["@context"] = {"dcterms": dcterms, "schema": schema, "foaf": foaf}
    return jsonld.expand(data)


rules = {
    "@id": set_if_absent,
    "@value": lambda a, s, p, v: a | {"@value": v},
    "@type": lambda a, s, p, v: a | {"@type": v},
    "*": lambda a, s, p, os: a | {p: [walk_one(o) for o in os]},
}
more_rules = {
    # NB: "(lambda x=42: ...)()" betekent "(let [x 42] ...)" als in Clojure.
    dcterms + "name": lambda a, s, p, os: a
    | (
        lambda name=os[0]["@value"].split(): {
            foaf + "givenName": [{"@value": name[0]}],
            foaf + "familyName": [{"@value": name[1]}],
        }
    )(),
    dcterms + "creator": lambda a, s, p, os: a | {p: [walk_one(o) for o in os]},
    dcterms + "title": lambda a, s, p, os: a | {schema + "name": os},
    foaf + "familyName": lambda a, s, p, os: a
    | {
        schema
        + "name": [
            {"@value": s.get(foaf + "givenName")[0]["@value"] + " " + os[0]["@value"]}
        ]
    },
    foaf + "givenName": ignore_silently,
    dcterms + "publisher": lambda a, s, p, os: a
    | {
        schema
        + "publisher": [
            {schema + "name": [o]} if "@value" in o else walk_one(o) for o in os
        ]
    },
    foaf + "name": lambda a, s, p, os: a | {schema + "name": [walk_one(o) for o in os]},
}

walk_one = walk(rules | more_rules)


def walk_all(objects):
    w = walk(rules | more_rules)
    accu = {}
    for o in objects:
        accu = w(o, accu=accu)
    return accu


@test
def title():
    objects = expand({"dcterms:title": "Titel van een document"})
    test.eq(1, len(objects))
    o = objects[0]
    test.eq("Titel van een document", o[dcterms + "title"][0]["@value"])
    n = walk_all(objects)  # default accu is {}
    test.eq({"http://schema.org/name": [{"@value": "Titel van een document"}]}, n)


@test
def title_lang():
    objects = expand(
        {
            "dcterms:title": [
                {"@value": "Titel van een document", "@language": "nl"},
                {"@value": "Title of a document", "@language": "en"},
                {"@value": "Titre d'un document", "@language": "fr"},
                {"@value": "Titel eines Dokuments", "@language": "de"},
            ]
        }
    )
    n = walk_all(objects)
    vs = n["http://schema.org/name"]
    test.eq(4, len(vs))
    test.eq({"@value": "Titel van een document", "@language": "nl"}, vs[0])
    test.eq({"@value": "Title of a document", "@language": "en"}, vs[1])
    test.eq({"@value": "Titre d'un document", "@language": "fr"}, vs[2])
    test.eq({"@value": "Titel eines Dokuments", "@language": "de"}, vs[3])


@test
def keep_first_id():
    """NB: using walk with a list accumulates everything in one accu !"""
    m = walk_all(
        [{"@id": "first"}, {"@id": "second", schema + "about": [{"@id": "third"}]}]
    )
    test.eq({"@id": "first", "http://schema.org/about": [{"@id": "third"}]}, m)


@test
def list_of_values():
    m = walk_one({schema + "name": [{"@value": "aap"}, {"@value": "noot"}]})
    test.eq({schema + "name": [{"@value": "aap"}, {"@value": "noot"}]}, m)


@test
def types():
    m = walk_one({"@type": ["atype:A"]})
    test.eq({"@type": ["atype:A"]}, m)


@test
def recur():
    m = walk_one(
        {dcterms + "publisher": [{foaf + "name": [{"@value": "Aap noot mies"}]}]}
    )
    test.eq(
        {schema + "publisher": [{schema + "name": [{"@value": "Aap noot mies"}]}]}, m
    )


@test
def insert_predicate():
    m = walk_one({dcterms + "publisher": [{"@value": "Aap noot mies"}]})
    test.eq(
        {schema + "publisher": [{schema + "name": [{"@value": "Aap noot mies"}]}]}, m
    )

    m = walk_one({dcterms + "publisher": [{"@value": "Aap"}, {"@value": "noot"}]})
    test.eq(
        {
            schema
            + "publisher": [
                {schema + "name": [{"@value": "Aap"}]},
                {schema + "name": [{"@value": "noot"}]},
            ]
        },
        m,
    )

    m = walk_one(
        {
            dcterms
            + "publisher": [
                {"@value": "Aap"},
                {dcterms + "title": [{"@value": "noot"}]},
            ]
        }
    )
    test.eq(
        {
            schema
            + "publisher": [
                {schema + "name": [{"@value": "Aap"}]},
                {schema + "name": [{"@value": "noot"}]},
            ]
        },
        m,
        diff=test.diff,
    )

    m = walk_one(
        {
            dcterms
            + "publisher": [{schema + "about": [{"@value": "noot"}]}, {"@value": "Aap"}]
        }
    )
    test.eq(
        {
            schema
            + "publisher": [
                {schema + "about": [{"@value": "noot"}]},
                {schema + "name": [{"@value": "Aap"}]},
            ]
        },
        m,
    )


@test
def testFoaf_emptyGivenName():
    object = expand({"dcterms:creator": {"foaf:givenName": []}})


@test
def testFoaf_noFamilyName():
    object = expand({"dcterms:creator": {"foaf:givenName": ["Voornaam"]}})


@test
def combine_properties():
    object = expand(
        {
            "dcterms:creator": {
                "foaf:givenName": ["Voornaam"],
                "foaf:familyName": "Achternaam",
            }
        }
    )
    result = walk_one(object[0])
    test.eq(
        {
            "http://purl.org/dc/terms/creator": [
                {"http://schema.org/name": [{"@value": "Voornaam Achternaam"}]}
            ]
        },
        result,
    )


@test
def split_properties():
    result = walk_one(
        {dcterms + "creator": [{dcterms + "name": [{"@value": "Voornaam Achternaam"}]}]}
    )
    test.eq(
        {
            dcterms
            + "creator": [
                {
                    foaf + "givenName": [{"@value": "Voornaam"}],
                    foaf + "familyName": [{"@value": "Achternaam"}],
                }
            ]
        },
        result,
    )


### old stuff with index
def node_index(j):
    # from jsonld2document from metastreams.index
    """index all (top level) nodes by their @id"""
    if "@graph" in j:
        j = j["@graph"]
    return {m["@id"]: m for m in j if "@id" in m}


#    class accu:
#        subject: dict = field(default_factory=dict)
#        index: dict = field(default_factory=dict)


@test
def test_flatten_expanded_round_trip():
    """flatten -> expand introduces blank nodes
    we make an index of all nodes so we can detect and recur into them
    """
    doc = {f"{dcterms}creator": {f"{foaf}name": "Piet Pietersen"}}
    flt = jsonld.flatten(
        doc, {}
    )  # this does not work => {'@graph': {'@container': '@id'}})
    exp = jsonld.expand(doc, {})
    flt_exp = jsonld.expand(flt, {})
    # print(json.dumps(flt, indent=2))
    # print(json.dumps(exp, indent=2))
    # print(json.dumps(flt_exp, indent=2))
    test.eq(
        {
            "_:b0": {
                "@id": "_:b0",
                "http://purl.org/dc/terms/creator": {"@id": "_:b1"},
            },
            "_:b1": {"@id": "_:b1", "http://xmlns.com/foaf/0.1/name": "Piet Pietersen"},
        },
        node_index(flt),
    )
    test.eq({}, node_index(exp))
    test.eq(
        {
            "_:b0": {
                "@id": "_:b0",
                "http://purl.org/dc/terms/creator": [{"@id": "_:b1"}],
            },
            "_:b1": {
                "@id": "_:b1",
                "http://xmlns.com/foaf/0.1/name": [{"@value": "Piet Pietersen"}],
            },
        },
        node_index(flt_exp),
    )


def l2t_fn(a, s, p, os):
    a[p] = tuple(list2tuple(o) for o in os) if type(os) is list else os
    return a


l2t_walk = walk({"*": l2t_fn})


def list2tuple(d):
    return l2t_walk(d) if type(d) is dict else d


@test
def list2tuple_basics():
    test.eq({}, list2tuple({}))
    test.eq({1: (1,)}, list2tuple({1: [1]}))
    test.eq({1: ({2: ()}, {3: (2, 3)})}, list2tuple({1: [{2: []}, {3: [2, 3]}]}))
    test.eq(
        {
            "http://schema.org/identifier": (
                {"@id": "urn:nbn:nl:hs:25-20.500.12470/10"},
            ),
            "http://schema.org/dateModified": (
                {"@value": "2020-08-15T01:50:06.598316Z"},
            ),
        },
        list2tuple(
            {
                schema + "identifier": [{"@id": "urn:nbn:nl:hs:25-20.500.12470/10"}],
                schema + "dateModified": [{"@value": "2020-08-15T01:50:06.598316Z"}],
            }
        ),
    )


def t2l_fn(a, s, p, os):
    a[p] = list(tuple2list(o) for o in os) if isinstance(os, (tuple, list)) else os
    return a


t2l_walk = walk({"*": t2l_fn})


def tuple2list(d):
    return t2l_walk(d) if isinstance(d, dict) else d


@test
def tuple2list_basics():
    d = {}
    d1 = tuple2list(d)
    test.eq({}, d1)
    test.ne(id(d), id(d1))

    d = {1: (1,), 3: ["iets"]}
    td = tuple2list(d)
    d[3].append("anders")
    test.eq({1: [1], 3: ["iets"]}, td)
    test.eq({1: [1]}, tuple2list({1: (1,)}))
    test.eq({1: [{2: []}, {3: [2, 3]}]}, tuple2list({1: ({2: ()}, {3: (2, 3)})}))
    test.eq(
        {
            "http://schema.org/identifier": [
                {"@id": "urn:nbn:nl:hs:25-20.500.12470/10"}
            ],
            "http://schema.org/dateModified": [
                {
                    "@value": "2020-08-15T01:50:06.598316Z",
                    "@type": "dateString",
                    "@language": "nl",
                }
            ],
            "http://schema.org/object": [{"@type": ["http://schema.org/Thing"]}],
        },
        tuple2list(
            {
                schema + "identifier": ({"@id": "urn:nbn:nl:hs:25-20.500.12470/10"},),
                schema
                + "dateModified": (
                    {
                        "@value": "2020-08-15T01:50:06.598316Z",
                        "@type": "dateString",
                        "@language": "nl",
                    },
                ),
                schema + "object": ({"@type": (schema + "Thing",)},),
            }
        ),
        diff=test.diff2,
    )


@test
def tuple2list_subclass():
    class D(dict):
        pass

    test.eq({"a": [{"b": []}]}, tuple2list(D(a=(D(b=()),))))


@test
def map_predicate2_normalize():
    mp = map_predicate2("new_p")
    test.eq(
        {"a": ({"@value": "A"},), "new_p": ({"@value": "p"},)},
        mp(
            {
                "a": ({"@value": "A"},),
            },
            "s",
            "p",
            [{"@value": "p"}],
        ),
    )
    mp = map_predicate2(
        "new_p", lambda os: tuple({"@value": "Changed:" + w["@value"]} for w in os)
    )
    test.eq(
        {"a": ({"@value": "A"},), "new_p": ({"@value": "Changed:p"},)},
        mp(
            {
                "a": ({"@value": "A"},),
            },
            "s",
            "p",
            [{"@value": "p"}],
        ),
    )


@test
def use_with_non_ld_json():
    se = []
    w = walk(
        {
            "a": {"b": lambda *a: se.append(a)},
        }
    )
    r = w({"a": {"b": 42}})
    test.eq(None, r)
    test.eq([({}, {"b": 42}, "b", 42)], se)


__all__ = [
    "walk",
    "ignore_assert",
    "ignore_silently",
    "unsupported",
    "map_predicate2",
    "map_predicate",
    "identity",
    "all_values_in",
    "list2tuple",
    "node_index",
    "tuple2list",
]
