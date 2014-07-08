from misc import gtest, autostart

def interpolate(lo, hi, x, lo2, hi2):
    return int(0.5 + lo2 + (float(x) - lo) * (hi2 - lo2) / (hi - lo))

@autostart
def extend_cct(lamp):
    HUE_AT_1000K = 0     # follow the Planckian locus as close as possible towards the lower-right
    SAT_AT_1000K = 255
    HUE_AT_1500K = 10500 # roughly where the Plackian locus exits Hue's gamut (y=0.4)
    SAT_AT_1500K = 255   # keep lowering hue until you get y=0.4 (and x=?), then get hue and sat
    HUE_AT_2000K = 12521 # set lamp to ct=1000000/2000, wait and get and sat hue from lamp
    SAT_AT_2000K = 225
    HUE_AT_6500K = 34534 # set lamp to ct=1000000/6500, wait and get hue and sat from lamp
    SAT_AT_6500K = 240
    HUE_AT_10000K = 46920 # lower left corner of gamut, see http://developers.meethue.com/coreconcepts.html
    SAT_AT_10000K = 255

    while True:
        args = yield
        ct = args["ct"]
        if not 1000 <= ct <= 10000:
            raise ValueError("CT value not supported: %d" % ct)
        if ct < 1500:
            hue = interpolate(1000, 1500, ct, HUE_AT_1000K, HUE_AT_1500K)
            lamp.send(dict(hue=hue, sat=SAT_AT_1500K))
        elif ct < 2000:
            hue = interpolate(1500, 2000, ct, HUE_AT_1500K, HUE_AT_2000K)
            sat = interpolate(HUE_AT_2000K, HUE_AT_1500K, hue, SAT_AT_2000K, SAT_AT_1500K)
            lamp.send(dict(hue=hue, sat=sat))
        elif ct < 6501:
            lamp.send(dict(ct=1000000/ct))
        else:
            hue = interpolate(6500, 10000, ct, HUE_AT_6500K, HUE_AT_10000K)
            sat = interpolate(6500, 10000, ct, SAT_AT_6500K, SAT_AT_10000K)
            lamp.send(dict(hue=hue, sat=sat))

class MockLamp(object):
    def send(self, args):
        self.args = args

l = MockLamp()

@gtest
def testCheckUpperBoundary():
    ex_cct = extend_cct(None)
    yield
    try:
        ex_cct.send(dict(ct=10001))
        raise Exception("must raise")
    except Exception, e:
        assert "CT value not supported: 10001" == str(e), str(e)
    yield
    
@gtest
def testSuperHueRange_6500_10000K():
    ex_cct = extend_cct(l)
    yield
    ex_cct.send(dict(ct=6501))
    assert l.args == dict(hue=34538, sat=240), l.args
    ex_cct.send(dict(ct=10000))
    assert l.args == dict(hue=46920, sat=255), l.args
    yield
    del ex_cct

@gtest
def testNormalHueRange_2000_6500K():
    ex_cct = extend_cct(l)
    yield
    ex_cct.send(dict(ct=2000))
    assert l.args == dict(ct=500), l.args
    ex_cct.send(dict(ct=6500))
    assert l.args == dict(ct=153), l.args
    ex_cct.send(dict(ct=3750))
    assert l.args == dict(ct=266), l.args
    yield
    del ex_cct

@gtest
def testSubHueRange_1500_2000K():
    ex_cct = extend_cct(l)
    yield
    ex_cct.send(dict(ct=1500))
    assert l.args == dict(hue=10500, sat=255), l.args
    ex_cct.send(dict(ct=1999))
    assert l.args == dict(hue=12517, sat=225), l.args
    ex_cct.send(dict(ct=1750))
    assert l.args == dict(hue=11511, sat=240), l.args
    yield
    del ex_cct

@gtest
def testSubHueRange_1000_1500K():
    ex_cct = extend_cct(l)
    yield
    ex_cct.send(dict(ct=1000))
    assert l.args == dict(hue=0, sat=255), l.args
    ex_cct.send(dict(ct=1500))
    assert l.args == dict(hue=10500, sat=255), l.args
    ex_cct.send(dict(ct=1250))
    assert l.args == dict(hue=5250, sat=255), l.args
    yield
    del ex_cct

@gtest
def testCheckLowerBoundary():
    ex_cct = extend_cct(None)
    yield
    try:
        ex_cct.send(dict(ct=999))
        raise Exception("must raise")
    except Exception, e:
        assert "CT value not supported: 999" == str(e), str(e)
    yield

if __name__ == "__main__":
    testSubHueRange_1000_1500K()
    testCheckLowerBoundary()
    testSubHueRange_1500_2000K()
    testNormalHueRange_2000_6500K()
    testSuperHueRange_6500_10000K()
    testCheckUpperBoundary()
