huecycle
========

Philips Hue day light tracker.

Also known as:

1. Natural Lighting (Philips Hue),
2. Adaptive Lighting (Apple Home)
3. Biodynamic Lighting (other marketeers),
4. Circadian Lighting (again others)

This piece of software makes it actually work.

Finalizing v2 is in progress....


Problems it solves:
-------------------

Hue performs 5 discrete steps and changes the lights abrupty 4 times a day. It also has no other way of enabling natural lighting than via the App; switches are not programmable to this. The 'Magic' button, supposedly sold to solve this problem, does not enable natural lighting at all. Instead it puts the lights at a fixed scene, depending on the time you press the button. It never changes this scene unless you press the button again, twice, tor turn it off and then on again. Besides that the 5 default scenes and times are choosen to mimic the dynamic natural lighting scene, the magic button has nothing to do with it.

Apple does it slightly better, but also has the problem that the dynamic scene cannot be invoked with a button. It uses more gradual color temperature changes during the day though. Their choice of color temperature is different from Hue and cannot be choosen.


The solution:
------------

Huecycle allows you to create and mix two different cycles and updates the lights whenever there is a change in one of them, usually everug few minutes:

1. Solar Cycle: the transition of the sun across the sky controls the color temperature. At sunrise and sunset, the color temperature is low (2000K), and at transit (noon), it will be high (4000K - 5000K). The color temperature follows a half sinusoidal curve both during the day and during the night. During the night, you could choose to go to higher temperature such as 10,000K or 20,000K as to emulate moonlight. You can also leave it low, like 2000k during the night to have a night light. Both moonlight as nightlight combine nicely with the wake/sleep cycle.

2. Your daily wake/sleep routine controls the brightness of the lights. Lights are low when you wake or go to sleep, and high in between. During the night, lights remain steady at the same (low) level. Huscycle is smart enough to recognize that sleep and wake times can be on either sides of sunrise or sunset.

Although color temparature cycling is the main goal, Huecycle offers a neat API to combine color cycling with very flexible programming of buttons and sensors.


The problem behind the problem
------------------------------

Dynamic scenes are way more difficult than just following up on events and switching. The main difference is that events happen once in a moments time, during which the world does not change.  A dynamic scene becomes an active agent doing its work in the background. These agents cannot be fired and forgotten, they have to be registered, mananged and, when times comes, be stopped. While they work, the world changes. They can make fewer assumptions about the world, they can easily crash, and last but not least, the can interfere with each other.  This makes dynamic scenes incredibly more difficult to test and deploy, let alone allowing end users to create them.

In Huecycle, a nice solution is present to solve many of the problems above, on a technical level. On a functional level problems remain: light can be part of groups (zones or rooms in Hue lingo) and groups are controllable by dynamic scenes as well. That means that one light van be controlled by different controllers at the samen time, one for each group it is in, and one for the light itself. This problem cannot be solved on a technical level, as it is fundamentally an end-user functionality. Huecycle could howver detect conficling cases and warn about it. That is on my wishlist.


Version 2
---------
Version 2 works with Hue Bridge v2 and Hue API v2, and Python 3.
Version 1 for Hue Bridge v1 and Python 2 is gone.


random notes
============
http://stackoverflow.com/questions/11884545/setting-color-temperature-for-a-given-image-like-in-photoshop
http://dsp.stackexchange.com/questions/8949/how-do-i-calculate-the-color-temperature-of-the-light-source-illuminating-an-ima
