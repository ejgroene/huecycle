from PIL import Image, ImageStat
from xyz2cct import XYZtoCCT # Robertson
from sys import argv
from subprocess import Popen, PIPE
from io import StringIO
from time import sleep
from math import sqrt
import pathlib

import autotest
test = autotest.get_tester(__name__)

# from https://en.wikipedia.org/wiki/Standard_illuminant
illuminantA = 2856
illuminantB = 4874
illuminantC = 6774


#http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html
#sRGB?
rgb2xyz = ( 0.412453, 0.357580, 0.180423, 0,
            0.212671, 0.715160, 0.072169, 0,
            0.019334, 0.119193, 0.950227, 0)

#https://www.color.org/chardata/rgb/srgb.xalter
rgb2xyz = ( 0.64, 0.30, 0.15, 0,
            0.33, 0.60, 0.06, 0,
            0.03, 0.10, 0.79, 0 )


def toCIE1931(rgb):
    assert rgb.getbands() == ('R', 'G', 'B'), rgb.getbands()
    return rgb.convert("RGB", rgb2xyz)


def prepare(p, cie=True):
    p = pathlib.Path(p)
    i = Image.open(p)
    if i.getbands() != ('R', 'G', 'B'):
        i = i.convert('RGB')
    return toCIE1931(i) if cie else i


def color_balance(p):
    i = prepare(p, cie=False)
    #print(i.histogram())
    l = sqrt(sum(map(lambda p: p[1]**2, i.getextrema())))
    return int(l*10)


@test
def color_balance_test():
    test.eq(3100, color_balance('./images/sample-2500K.png'))
    test.eq(3969, color_balance('./images/sample-9500K.png'))
    test.eq(2679, color_balance('./images/sample-light-gray.png'))
    test.eq(2627, color_balance('./images/sample-dark-gray.png'))
    test.eq(4416, color_balance('./images/sample-kitchen-2700K.png'))



# convert to XYZ: http://effbot.org/imagingbook/image.htm#tag-Image.Image.convert

kelvin_table = {
    1000: (255,56,0),
    1500: (255,109,0),
    2000: (255,137,18),
    2500: (255,161,72),
    3000: (255,180,107),
    3500: (255,196,137),
    4000: (255,209,163),
    4500: (255,219,186),
    5000: (255,228,206),
    5500: (255,236,224),
    6000: (255,243,239),
    6500: (255,249,253),
    7000: (245,243,255),
    7500: (235,238,255),
    8000: (227,233,255),
    8500: (220,229,255),
    9000: (214,225,255),
    9500: (208,222,255),
    10000: (204,219,255)}


# use http://www.brucelindbloom.com/index.html?Eqn_XYZ_to_T.html to find CCT

def analyze_sky(xyz):
    stats = ImageStat.Stat(xyz)
    min_y = stats.extrema[1][1] - stats.stddev[1]
    sum_t = 0
    i = 0
    for p in (p for p in xyz.getdata() if p[1] > min_y):
        try:
            t = XYZtoCCT(p)
        except ValueError:
            continue
        sum_t += t
        i += 1
    avg_t = sum_t // i
    print("%d; %d" % (i, avg_t))
    return avg_t

def robertson(p):
    i = prepare(p)
    return analyze_sky(i)

#@test
def robertson_test():
    test.eq(3643, robertson('./images/sample-2500K.png'))
    test.eq(6870, robertson('./images/sample-9500K.png'))
    test.eq(6793, robertson('./images/sample-light-gray.png'))
    test.eq(6212, robertson('./images/sample-dark-gray.png'))
    test.eq(5355, robertson('./images/sample-kitchen-2700K.png'))

def radiance(p):
    i = prepare(p)
    s = 0
    c = 0
    for x, y, _ in i.getdata():
        c += 1
        M1 = (-1.3515- 1.7703 * x +  5.9114 * y)/(0.0241 + 0.2562 * x - 0.7341 * y)
        M2 = ( 0.03  -31.4424 * x + 30.0717 * y)/(0.0241 + 0.2562 * x - 0.7341 * y)
        S = 0
        for WL, S0, S1, S2 in S_table:
            S += S0 + S1 * M1 + S2 * M2
        s += S
    return s // c

#wl   S0      S1     S2
S_table = [
    (380,  63.40,  38.50,  3.00),
    (385,  64.60,  36.75,  2.10),
    (390,  65.80,  35.00,  1.20),
    (395,  80.30,  39.20,  0.05),
    (400,  94.80,  43.40, -1.10),
    (405,  99.80,  44.85, -0.80),
    (410, 104.80,  46.30, -0.50),
    (415, 105.35,  45.10, -0.60),
    (420, 105.90,  43.90, -0.70),
    (425, 101.35,  40.50, -0.95),
    (430,  96.80,  37.10, -1.20),
    (435, 105.35,  36.90, -1.90),
    (440, 113.90,  36.70, -2.60),
    (445, 119.75,  36.30, -2.75),
    (450, 125.60,  35.90, -2.90),
    (455, 125.55,  34.25, -2.85),
    (460, 125.50,  32.60, -2.80),
    (465, 123.40,  30.25, -2.70),
    (470, 121.30,  27.90, -2.60),
    (475, 121.30,  26.10, -2.60),
    (480, 121.30,  24.30, -2.60),
    (485, 117.40,  22.20, -2.20),
    (490, 113.50,  20.10, -1.80),
    (495, 113.30,  18.15, -1.65),
    (500, 113.10,  16.20, -1.50),
    (505, 111.95,  14.70, -1.40),
    (510, 110.80,  13.20, -1.30),
    (515, 108.65,  10.90, -1.25),
    (520, 106.50,   8.60, -1.20),
    (525, 107.65,   7.35, -1.10),
    (530, 108.80,   6.10, -1.00),
    (535, 107.05,   5.15, -0.75),
    (540, 105.30,   4.20, -0.50),
    (545, 104.85,   3.05, -0.40),
    (550, 104.40,   1.90, -0.30),
    (555, 102.20,   0.95, -0.15),
    (560, 100.00,   0.00,  0.00),
    (565,  98.00,  -0.80,  0.10),
    (570,  96.00,  -1.60,  0.20),
    (575,  95.55,  -2.55,  0.35),
    (580,  95.10,  -3.50,  0.50),
    (585,  92.10,  -3.50,  1.30),
    (590,  89.10,  -3.50,  2.10),
    (595,  89.80,  -4.65,  2.65),
    (600,  90.50,  -5.80,  3.20),
    (605,  90.40,  -6.50,  3.65),
    (610,  90.30,  -7.20,  4.10),
    (615,  89.35,  -7.90,  4.40),
    (620,  88.40,  -8.60,  4.70),
    (625,  86.20,  -9.05,  4.90),
    (630,  84.00,  -9.50,  5.10),
    (635,  84.55, -10.20,  5.90),
    (640,  85.10, -10.90,  6.70),
    (645,  83.50, -10.80,  7.00),
    (650,  81.90, -10.70,  7.30),
    (655,  82.25, -11.35,  7.95),
    (660,  82.60, -12.00,  8.60),
    (665,  83.75, -13.00,  9.20),
    (670,  84.90, -14.00,  9.80),
    (675,  83.10, -13.80, 10.00),
    (680,  81.30, -13.60, 10.20),
    (685,  76.60, -12.80,  9.25),
    (690,  71.90, -12.00,  8.30),
    (695,  73.10, -12.65,  8.95),
    (700,  74.30, -13.30,  9.60),
    (705,  75.35, -13.10,  9.05),
    (710,  76.40, -12.90,  8.50),
    (715,  69.85, -11.75,  7.75),
    (720,  63.30, -10.60,  7.00),
    (725,  67.50, -11.10,  7.30),
    (730,  71.70, -11.60,  7.60),
    (735,  74.35, -11.90,  7.80),
    (740,  77.00, -12.20,  8.00),
    (745,  71.10, -11.20,  7.35),
    (750,  65.20, -10.20,  6.70),
    (755,  56.45,  -9.00,  5.95),
    (760,  47.70,  -7.80,  5.20),
    (765,  58.15,  -9.50,  6.30),
    (770,  68.60, -11.20,  7.40),
    (775,  66.80, -10.80,  7.10),
    (780,  65.00, -10.40,  6.80)]


#@test  # SLOW
def analyze_image_1():
    test.eq(5963, radiance('./images/sample-2500K.png'))
    test.eq(3637, radiance('./images/sample-9500K.png'))
    test.eq(5353, radiance('./images/sample-light-gray.png'))
    test.eq(5138, radiance('./images/sample-dark-gray.png'))
    test.eq(5693, radiance('./images/sample-kitchen-2700K.png'))

def mccamy(p):
    i = prepare(p)
    cct = 0
    c = 0
    for x, y, z in i.getdata():
        c += 1
        n = (x - 0.3320) / (0.1858 - y)   # wikipedia
        #n = (x - 0.3320) / (y - 0.1858)  # article
        #CCT = 437 * n**3 + 3601 * n**2 + 6861 * n + 5517
        CCT = 449 * n**3 + 3525 * n**2 + 6823.3 * n + 5520.33
        cct += CCT
    return cct // c

#@test
def analyze_image_mccamy():
    test.eq(1859, mccamy('./images/sample-2500K.png'))
    test.eq(2029, mccamy('./images/sample-9500K.png'))
    test.eq(1826, mccamy('./images/sample-light-gray.png'))
    test.eq(1840, mccamy('./images/sample-dark-gray.png'))
    test.eq(1831, mccamy('./images/sample-kitchen-2700K.png'))
    #test.eq(15427, mccamy('./images/sample-2500K.png'))
    #test.eq(14023, mccamy('./images/sample-9500K.png'))
    #test.eq(15655, mccamy('./images/sample-light-gray.png'))
    #test.eq(15499, mccamy('./images/sample-dark-gray.png'))
    #test.eq(15614, mccamy('./images/sample-kitchen-2700K.png'))


def hernandez(p):
    from math import exp
    i = prepare(p)
    cct = 0
    c = 0
    for x, y, z in i.getdata():
        #n = (x - 0.3366) / (0.1735 - y)   # wikipedia
        n = (x - 0.3320) / (y - 0.1858)  # article
        CCT =  -949.86315 + \
               6253.80338 * exp(-n/0.92159) + \
                 28.70599 * exp(-n/0.20039) + \
                  0.00004 * exp(-n/0.07125)
        if 100 < CCT < 20000:
            c += 1
            cct += CCT
    return cct // c


@test
def analyze_image_hernandez():
    test.eq(877, hernandez('./images/sample-2500K.png'))
    test.eq(1187, hernandez('./images/sample-9500K.png'))
    test.eq( 940, hernandez('./images/sample-light-gray.png'))
    test.eq( 966, hernandez('./images/sample-dark-gray.png'))
    test.eq( 902, hernandez('./images/sample-kitchen-2700K.png'))


def gimp_like(p):
    import numpy as np
    i = prepare(p)
    def wb(channel, perc = 0.05):
        mi, ma = (np.percentile(channel, perc), np.percentile(channel,100.0-perc))
        channel = np.uint8(np.clip((channel-mi)*255.0/(ma-mi), 0, 255))
        return channel
    #image = cv2.imread("foo.jpg", 1) # load color
    imWB  = np.dstack([wb(channel, 0.05) for channel in i.split()] )
    print(">>>", imWB)
    return imWB

#@test
def gimp_like_test():
    test.eq(1859, gimp_like('./images/sample-2500K.png'))
    test.eq(2055, gimp_like('./images/sample-9500K.png'))
    test.eq(1867, gimp_like('./images/sample-light-gray.png'))
    test.eq(1880, gimp_like('./images/sample-dark-gray.png'))
    test.eq(1871, gimp_like('./images/sample-kitchen-2700K.png'))
