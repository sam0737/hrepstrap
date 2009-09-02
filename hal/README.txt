1. In the repstrap-extruder.hal, changes the absolute path to the repstrap-extruder.py script

2. In the EMC ini, under the [DISPLAY] section, add the PYVCP, like this :-
   [DISPLAY]
   DISPLAY = axis
   ...
   PYVCP = /absolute/path/to/repstrap-extruder.pyvcp

3. In your EMC ini, there should be a POSTGUI_HALFILE in the [HAL] section. If not, create one :-
   [HAL]
   ...
   POSTGUI_HALFILE = custom_postgui.hal

4. In the customZpostgui.hal, include the repstrap-excluder.hal file, like this :-
   source /absolute/path/to/repstrap-extruder.hal

5. Modify RepRapSerialComm.py, make sure the path to your serial device is correct.

6. Hook up your cable and such.

7. Fire up the EMC. Now hopefully you see a green icon for the Connection LED!