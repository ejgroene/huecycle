from autotest import get_tester

test = get_tester(__name__)

MIREK = 1000000
""" Extends Hue's CT range by simulating very low or high CT's with the nearest hue and saturation.
    See http://developers.meethue.com/coreconcepts.html for the color space, gammut and locus.
    NB: this only works for Hue COLOR lamp!
"""

# NEW Philips Hue White and Color 1100 Lumens lamp (with Gamut C)
# API v2 works with Mirek and XY, ct and hue/sat are no longer supported


def ct_to_xy(ct):
    """https://en.wikipedia.org/wiki/Planckian_locus#Approximation"""
    assert 1667 <= ct <= 25000, f"out of range: {ct}"
    T = ct
    if T < 4000:
        x = (
            -0.2661239 * 10**9 / T**3
            - 0.2343589 * 10**6 / T**2
            + 0.8776956 * 10**3 / T
            + 0.179910
        )
    else:
        x = (
            -3.0258469 * 10**9 / T**3
            + 2.1070379 * 10**6 / T**2
            + 0.2226347 * 10**3 / T
            + 0.240390
        )
    if T < 2222:
        y = -1.1063814 * x**3 - 1.34811020 * x**2 + 2.18555832 * x - 0.20219683
    elif T < 4000:
        y = -0.9549476 * x**3 - 1.37418593 * x**2 + 2.09137015 * x - 0.16748867
    else:
        y = +3.0817580 * x**3 - 5.87338670 * x**2 + 3.75112997 * x - 0.37001483
    return round(x, 4), round(y, 4)


@test
def testCheckUpperBoundary():
    with test.raises(AssertionError):
        ct_to_xy(1666)


# {"color": {"xy": {"x": 0.322, "y": 0.3318}}}
# {"color_temperature": {"mirek": 167}}


@test
def some_hand_picked_in_hue_range_values():
    # these xy values do not result in a valid Mirek value in Hue, so we check xy
    test.eq(
        (0.3129, 0.3231), ct_to_xy(6536)
    )  # Hue: 0.3122 (-0.0007), 0.3282 (+0.0051). Hmmm
    test.eq(
        (0.3135, 0.3237), ct_to_xy(6500)
    )  # Hue: 0.3129 (-0.0006), 0.3289 (+0.0052), Hmmm
    test.eq(
        (0.322, 0.3318), ct_to_xy(6000)
    )  # Hue: 0.322  (+0.0000), 0.3368 (+0.0050), OK
    test.eq(
        (0.345, 0.3516), ct_to_xy(5000)
    )  # Hue: 0.3455 (+0.0005), 0.3559 (+0.0043), OK
    test.eq(
        (0.3805, 0.3767), ct_to_xy(4000)
    )  # Hue: 0.3812 (+0.0007), 0.3794 (+0.0027), OK

    # next xy values are checked against Hue's Mirek
    test.eq((0.4366, 0.4042), ct_to_xy(3000))  # Hue: 331 Mirek = 3021 K, OK
    test.eq((0.5269, 0.4133), ct_to_xy(2000))  # Hue: 497 Mirek = 2012 K, OK


@test
def some_higher_values():
    # higher values, just tried in Hue and eyeballed
    test.eq((0.3064, 0.3166), ct_to_xy(7000))  # besomes slightly blueish, as expected
    test.eq((0.2952, 0.3048), ct_to_xy(8000))  # besomes slightly blueish, as expected
    test.eq((0.287, 0.2956), ct_to_xy(9000))  # besomes more blueish, as expected
    test.eq((0.2807, 0.2883), ct_to_xy(10000))  # besomes blueish, as expected
    test.eq((0.2564, 0.2576), ct_to_xy(20000))  # besomes quite blueish, as expected
    test.eq((0.2525, 0.2523), ct_to_xy(25000))  # besomes quite blueish, as expected


@test
def some_lower_values():
    # lower values, just tried in Hue and eyeballed
    test.eq((0.5646, 0.4029), ct_to_xy(1667))  # Eyeballed, seems OK
