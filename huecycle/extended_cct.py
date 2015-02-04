from misc import autotest, autostart, interpolate

MIREK = 1000000

@autostart
def extend_cct(lamp):
    """ Extends Hue's CT range by simulating very low or high CT's with the nearest hue and saturation.
        Color Temperatures are in Kelvin and translated to hue/sat or to ct in Mired.
        See http://developers.meethue.com/coreconcepts.html for the color space, gammut and locus."""
    HUE_AT_1000K = 0     # follow the Planckian locus as close as possible towards the lower-right
    SAT_AT_1000K = 255
    HUE_AT_1500K = 10500 # roughly where the Planckian locus exits Hue's gamut (y=0.4)
    SAT_AT_1500K = 255   # keep lowering hue until you get y=0.4 (and x=?), then get hue and sat
    HUE_AT_2000K = 12521 # set lamp to ct=1000000/2000, wait and get and sat hue from lamp
    SAT_AT_2000K = 225
    HUE_AT_6500K = 34534 # set lamp to ct=1000000/6500, wait and get hue and sat from lamp
    SAT_AT_6500K = 240
    HUE_AT_10000K = 46920 # lower left corner of gamut.
    SAT_AT_10000K = 255
    while True:
        args = yield
        ct = args.pop("ct")
        if not 100 <= ct <= 10000:
            raise ValueError("CT value not supported: %d" % ct)
        if ct < 1000:
            ct = MIREK/ct
        if ct < 1500:
            args["hue"] = int(0.5 + interpolate(1000, 1500, ct, HUE_AT_1000K, HUE_AT_1500K))
            args["sat"] = SAT_AT_1000K
        elif ct < 2000:
            args["hue"] = int(0.5 + interpolate(1500, 2000, ct, HUE_AT_1500K, HUE_AT_2000K))
            args["sat"] = int(0.5 + interpolate(2000, 1500, ct, SAT_AT_2000K, SAT_AT_1500K))
        elif ct < 6501:
            args["ct"] = MIREK/ct
        else:
            args["hue"] = int(0.5 + interpolate(6500, 10000, ct, HUE_AT_6500K, HUE_AT_10000K))
            args["sat"] = int(0.5 + interpolate(6500, 10000, ct, SAT_AT_6500K, SAT_AT_10000K))
        lamp.send(args)

class MockLamp(object):
    def send(self, args):
        self.args = args

mock = MockLamp()

@autotest
def testPassOtherParameters():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=6501, bri=15, on=False))
    assert mock.args == dict(hue=34538, sat=240, bri=15, on=False), mock.args
    
@autotest
def testCheckUpperBoundary():
    ex_cct = extend_cct(None)
    try:
        ex_cct.send(dict(ct=10001))
        raise Exception("must raise")
    except Exception, e:
        assert "CT value not supported: 10001" == str(e), str(e)
    
@autotest
def testSuperHueRange_6500_10000K():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=6501))
    assert mock.args == dict(hue=34538, sat=240), mock.args
    ex_cct.send(dict(ct=10000))
    assert mock.args == dict(hue=46920, sat=255), mock.args

@autotest
def testNormalHueRange_2000_6500K():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=2000))
    assert mock.args == dict(ct=500), mock.args
    ex_cct.send(dict(ct=6500))
    assert mock.args == dict(ct=153), mock.args
    ex_cct.send(dict(ct=3750))
    assert mock.args == dict(ct=266), mock.args

@autotest
def testSubHueRange_1500_2000K():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=1500))
    assert mock.args == dict(hue=10500, sat=255), mock.args
    ex_cct.send(dict(ct=1999))
    assert mock.args == dict(hue=12517, sat=225), mock.args
    ex_cct.send(dict(ct=1750))
    assert mock.args == dict(hue=11511, sat=240), mock.args

@autotest
def testSubHueRange_1000_1500K():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=1000))
    assert mock.args == dict(hue=0, sat=255), mock.args
    ex_cct.send(dict(ct=1500))
    assert mock.args == dict(hue=10500, sat=255), mock.args
    ex_cct.send(dict(ct=1250))
    assert mock.args == dict(hue=5250, sat=255), mock.args

@autotest
def testInterpretLowValuesAsMirek():
    ex_cct = extend_cct(mock)
    ex_cct.send(dict(ct=500))
    assert mock.args == dict(ct=500), mock.args
    ex_cct.send(dict(ct=100))
    assert mock.args == dict(hue=46920, sat=255), mock.args
    ex_cct.send(dict(ct= 999))
    assert mock.args == dict(hue=21, sat=255), mock.args
    ex_cct.send(dict(ct=1000))
    assert mock.args == dict(hue=0, sat=255), mock.args
    ex_cct.send(dict(ct=1001))
    assert mock.args == dict(hue=21, sat=255), mock.args

@autotest
def testCheckUpperBoundary():
    ex_cct = extend_cct(None)
    try:
        ex_cct.send(dict(ct=99))
        raise Exception("must raise")
    except Exception, e:
        assert "CT value not supported: 99" == str(e), str(e)
