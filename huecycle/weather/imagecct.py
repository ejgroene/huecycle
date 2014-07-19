from PIL import Image, ImageStat
from xyz2cct import XYZtoCCT
from sys import argv
from subprocess import Popen, PIPE
from StringIO import StringIO
from time import sleep

def capture_image(f=None):
    if not f:
        p = Popen(["fswebcam", "-"], stdout=PIPE, stderr=PIPE)
        data, errs = p.communicate()
        f = StringIO(data)
    rgb = Image.open(f)
    print "Captured:", rgb
    return rgb


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

rgb2xyz = ( 0.412453, 0.357580, 0.180423, 0,
            0.212671, 0.715160, 0.072169, 0,
            0.019334, 0.119193, 0.950227, 0)

def convert_to_xyz(rgb):
    xyz = rgb.convert("RGB", rgb2xyz)
    return xyz


# use http://www.brucelindbloom.com/index.html?Eqn_XYZ_to_T.html to find CCT

def analyze_sky():
    rgb = capture_image(argv[1] if len(argv) > 1 else None)
    xyz = convert_to_xyz(rgb)
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
    avg_t = sum_t / i
    print "%d; %d" % (i, avg_t)

while True:
    analyze_sky()
    sleep(1200)
