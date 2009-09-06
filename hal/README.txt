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

5. Make a change in the input parameter of "steps_per_mm_cube" in that hal file.
   The value is number of encoder steps representing 1mm cube

6. Modify RepRapSerialComm.py, make sure the path to your serial device is correct.

7. Soft link the mcode-inject.py to M101, M102, M103, say in the shell, you do:
   ln -s mcode-inject.py M101
   ln -s mcode-inject.py M102
   ...
   ln -s mcode-inject.py M108

8. Make sure all of them are marked as executable, say in the shell, you do:
   chmod a+x *.py

9. Hook up your cable and such.

10. Fire up the EMC. Now hopefully you see a green icon for the Connection LED!
