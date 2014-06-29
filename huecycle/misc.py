import rfc822

def autostart(f):
    def g(*args, **kwargs):
        h = f(*args, **kwargs)
        h.next()
        return h
    return g

def time822(s):
    return rfc822.mktime_tz(rfc822.parsedate_tz(s))
