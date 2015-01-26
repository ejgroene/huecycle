
from datetime import datetime, time, timedelta

class clock(object):

    def __init__(self):
        self.t = None

    def set(self, t):
        self.t = t

    def today(self, h, m, s=0):
        return datetime.combine(datetime.today(), time(h,m,s))

    def tomorrow(self, h, m=0, s=0):
        return datetime.combine(datetime.today() + timedelta(days=1), time(h,m,s))

    def now(self):
        return self.t or datetime.now()

clock = clock()
