import rfc822

def autostart(f):
    def g(*args, **kwargs):
        h = f(*args, **kwargs)
        h.next()
        return h
    return g

def time822(s):
    return rfc822.mktime_tz(rfc822.parsedate_tz(s))

@autostart
def average():
    v = yield
    n = 1
    while True:
        v += yield v / n
        n += 1

def gtest(f):
    def t():
        g = f()
        g.next() # setup
        g.next() # test
        try:
            g.next() # tear down
        except StopIteration:
            pass
        print f.__name__, "Ok"
    return t


