
def autotest(f):
    print "%s.%s" % (f.__module__, f.__name__),
    f()
    print " Ok."

