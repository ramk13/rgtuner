rgtuner
=======

Credit:
Originally forked from https://github.com/Spferical/rgtuner

rgtuner is a program to 'tune' bots for robotgame.org by modifying one variable at a time, throwing versions of a bot with different possible values for the variable against specified bots. rgtuner is not an optimizer in the usual definition. It runs a matrix of variants of the original file and scores each variant by average scoring margin. 

Because of the variance present in Robot Game you'll need to run a decent number of matches (minimum 10, probably closer to 25) for each case to get a reasonable sample. Even with that many matches there is still significant variance in scoring margin. Depending on the options you choose, the tuner can take a VERY long time to run. It gives an indication of this as it's running. Because of the variance, rgtuner won't do a good job of fine tuning for cases that are very similar to each other. It does use the same set of seeds for each case compared, so if you run the whole optimization twice you should get similar results.

Included is an example bot, a version of Sfpar. 

#Requirements
- Python
- rgkit

#Usage
`$ python rgtuner.py [-h] [-p PROCESSES] file_to_optimize`

#In file syntax
Variables to optimize are marked by `#optimize (parameters)` in the line above the value assignment. There are three ways to specify the range of optimization values:

1 - a list of values to use directly:
```python
#optimize = list: 3, 5, 10, 20
opt_variable = 10
```

2 - evenly spaced steps around the original value by multiplication, the multiplier gives the min/max value
```python
#optimize = multsteps: 2, 5
opt_variable = 10
```
is the same as `list: 5, 7.07, 10, 14.14, 20`

3 - evenly spaced steps around the original value by addition, the adder gives the min/max value
```python
#optimize = addsteps: 5, 3
opt_variable = 10
```
is the same as `list:  5,  10,  15`

Enemy robots to match against are listed with `#enemy_file = path_to_enemy_robot`
If no robot is given, the original robot is used

Other options include:
Number of matches to run per enemy robot:
```python
#num_matches = xxx
```
Path to log file (mirrors std_out). If none is given, stdout isn't logged.
```python
#log_file = path_to_log_file
```
Whether to save the best value in the original file. If the option is not specified the default is to overwrite the original file.
```python
#save_optimum = 0
```

example:

```python
#num_matches = 3
#save_optimum = 0
#enemy_file = liquid1.0.py
#enemy_file = RageMK1.py

#optimize = addsteps: 5, 5
COULD_DIE_WEIGHT = 20.0
#optimize = list: 30, 34, 36, 38
ENEMY_IN_LOC_WEIGHT = 34.25
#optimize = multsteps: 2, 3
SURROUND_WEIGHT = 0.5
```

example output:
```
Starting optimization at 15:04:23.
Running 5*3*4 = 60 test cases of 3 matches (180 total) each over 3 processes
COULD_DIE_WEIGHT -  15.00  17.50  20.00  22.50  25.00
SURROUND_WEIGHT -   0.25   0.50   1.00
ENEMY_IN_LOC_WEIGHT -  30.00  34.00  36.00  38.00

           liquid1.0 -   3: [...       ] -    [2, 1, 0] by [43, 38] diff   5.7 std  6.1 in   6.6s
             RageMK1 -   3: [...       ] -    [3, 0, 0] by [44, 25] diff  19.0 std  4.0 in   6.4s
 15.00   0.25  30.00                - avg:  12.3 std:  8.6 in  13.1s. (   1/  60) Done at 15:17:17
           liquid1.0 -   3: [...       ] -    [2, 1, 0] by [42, 39] diff   3.0 std  6.2 in   7.3s
             RageMK1 -   3: [...       ] -    [3, 0, 0] by [42, 31] diff  11.3 std  0.6 in   7.5s
 15.00   0.25  34.00                - avg:   7.2 std:  6.0 in  14.9s. (   2/  60) Done at 15:18:09
           liquid1.0 -   3: [...       ] -    [2, 1, 0] by [42, 41] diff   0.7 std  3.2 in   7.0s
             RageMK1 -   3: [...       ] -    [3, 0, 0] by [42, 30] diff  12.0 std  7.0 in   6.7s
...

Final Results in  758.0s at 16:12:37
Best Result:
 15.00   0.50  30.00                - avg:  13.8 std:  7.9

Sorted Results:
 15.00   0.50  30.00                - avg:  13.8 std:  7.9
 15.00   0.25  30.00                - avg:  12.3 std:  8.6
 17.50   0.25  30.00                - avg:  11.2 std:  6.7
 17.50   0.25  34.00                - avg:  10.8 std:  5.9
 25.00   0.50  36.00                - avg:  10.7 std:  1.9
...
```