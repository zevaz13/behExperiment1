# Requirements for Rapid Experimental Prototyping
## Deliverable 3 — Configurable Firmware (rapid experimental prototyping)

**Output path:** `prototype2/Firmware/configurableFirmware/`

Highly flexible firmware for rapid prototyping of new stimulus designs. Four sub-modes, all
configurable via serial without reprogramming. This Firmware should:
- be modular, as in previous iterations.
- Add support for hue sensor via I2C (see example firmware for module and implementation startingPoint/prototype2/Firmware/GRIDHUESENSOR_10JUN26/)
- ADC and pwm resolution of 12 bits
- The experiments will have the possibility to work with and without the hue sensor, so the sensor configuration is not imperative for the firmware to work. Instead, if the user tries to start a hue-experiment. An error should be returned telling them that the Hue sensor is not connected, or configured.
- Flickering will be done using the hardware timer, just like it has been done so far. The big change here is that the LED assign to the flickering is configurable. The user can select any of the 5 LEDs to flicker.
- Hardware timer used to stream data via serial port to a GUI. This GUI will allow the user to control and configure the behavior of Teensy in execution time. 
  - Teensy sends data to GUI every 100 ms. 
  - Data frame shared among all modes. Something like: `TriggerCue@TrialNumber@Amber@Red@Green@BBlue@Cyan@HUE_R@HUE_G@HUE_B@HUE_CT@HUE_L@LEDA@LEDB@Press@Trigger` [might need extra thinking]
  - When some of these elements not in use, they will be written as -99
- Get command should get current configuration. 
- Get param_name should return the current value for that param.
### Sub-mode A — Solid
The simplest experiment, does not Flicker. This means it only uses digitalwrite to set the values to the LEDS in a static manner:
  - LEDs change their behavior after receving a command from the user looking like "REDLED 300"
  - Multiple LEDs can be set at the same time "REDLED 3600, GREENLED 2000, CYANLED 780"
  - These values will be controlled from a GUI using sliders. one per LED. 
  - values per LED constrained from [0 4095]
  - Works with and without Hue sensor. 
  - If in Hue sensor mode. If the users presses the push button, or a GUI button, a complete dataframe with the stimulatort's current state (regular data frame) will be send via serial (with Press = 1)
  - Need a command to stop the test. 
  - TrialNumber only updated if the user presses the button, or uses the GUI button to check the hue data.
  - trigger not set in this mode. 

### Sub-mode B — Linear 
This is an experimental modality that flickers. one LED changes in linear steps with a predefined range (range and number of steps are configurable) plus a background value (LED and intensities configurable), against a reference value (LED and intensities configurable) with a given configurable frequency (freq). The Stimulus flickers for a configurable time, with configuralbe intertrial wait periods:
- The flickering LED in this experiment will be called LEDA happens on the first part of the period the stim period (controlled by the hardware timer). The user configures One of the LED to flicker (out of the 5), they can also add 2 constant values out of the other 4 LEDs. 
- The second part of the period (controlled by hardware timer) will be called the reference period. for this one, the user has the ability to set up to 3 LEDs with fixed values. 
- This means that this experiment will have steps changes of LEDA. The behavior at flickering will be currentValLEDA, BackgroundStim1 (LED, intensity defined by user), BackgroundStim2 (LED, intensity defined by user) on the first half of the period. Then Ref1 (LED, intensity Ref2 (LED, intensity defined by user), Ref3 (LED, intensity defined by user)
- The BackgroundStim1, BackgroundStim2, Ref1, Ref2, Ref3 could all be undefined. This means that the behavior is just LEDA flickering at current step amplitude, against nothing
- This mode can be run with and without hue sensor. 
- In both cases it will send periodical dataframes to the GUI. The difference is that for the hue exp, it should check for the hue sensor, and change the values in the dataframe.
- Baseline periods can be added similar to what is done in the prototype2 grid experiments. This means, the Stim Does not flicker during this period, but it present solid values during the trialLength, for a number of times. In this case, the user can decide what LEDs to use for the reference, and their brightness. The user configures the number of baselines at start and at end. 
- Baseline trials use the stimulusPeriods, and intertrialWaits as 
- TrialNumber starts at 1001 for baseline periods and at 1 for stimulus trials.
- Configurable parameters: steps [2 50],LEDA (one of the 5 LEDs), maxA=<int>, minA=<int>,BackgroundStim1LED (one of remaining four), BackgroundStim1INT ([0 4095]),  BackgroundStim2LED (one of remaining 3), BackgroundStim2INT ([0 4095]), Ref1LED (one of 5 LEDs), Ref2LED (one of 4 LEDs), Ref3LED (one of 4 LEDs), Ref1INT ([0 4095]), Ref2INT ([0 4095]), Ref1INT ([0 4095]), BaselineLEDs (can be nothing, or all of them), baselineIntensities (value for [0 4095] for the selected baseline LEDs) [This needs to be defined better], nBaselinesStart=<int>
nBaselinesEnd=<int>, freq, trialLength [200 30000], interTrialWait [50 30000], hue (bool) [This behavior most be better defined]
- A set of default values should be chosen, so they don't all need to be defined when testing.
- The trigger signal must always be sent. It defines the start and end of stimulus periods and intertrialWaits. In the firmware the accompaning signal should also be used as it is used to interact with EEG recording devices. 

### Sub-mode C — Grid 
This is an experimental modality that flickers. Two LED change in linear steps with a predefined range (range and number of steps are configurable for both) plus a background value (LED and intensities configurable), against a reference value (LED and intensities configurable) with a given configurable frequency (freq). The Stimulus flickers for a configurable time, with configuralbe intertrial wait periods:
- The flickering LEDs in this experiment will be called LEDA and LEDB, happens on the first part of the period the stim period (controlled by the hardware timer). The user configures LEDA (out of the 5), LEDB (other 4) they can also add 2 constant values out of the other 3 LEDs. 
- The second part of the period (controlled by hardware timer) will be called the reference period. for this one, the user has the ability to set up to 3 LEDs with fixed values. 
- This means that this experiment will have steps changes of LEDA, LEDB (forming a grid of steps by steps size). The behavior at flickering will be currentValLEDA, currentValLEDB, BackgroundStim1 (LED, intensity defined by user), BackgroundStim2 (LED, intensity defined by user) on the first half of the period. Then Ref1 (LED, intensity Ref2 (LED, intensity defined by user), Ref3 (LED, intensity defined by user)
- The BackgroundStim1, BackgroundStim2, Ref1, Ref2, Ref3 could all be undefined. This means that the behavior is just LEDA flickering at current step amplitude, against nothing
- This mode can be run with and without hue sensor. 
- This grid uses the same order value for selecting the sequence to use in the experiment. To be implemented as in prototype2/Firmware/subjectExperiment. 
- In both cases (hue vs. no hue) it will send periodical dataframes to the GUI. The difference is that for the hue exp, it should check for the hue sensor, and change the values in the dataframe.
- Baseline periods can be added similar to what is done in the prototype2 grid experiments. This means, the Stim Does not flicker during this period, but it present solid values during the trialLength, for a number of times. In this case, the user can decide what LEDs to use for the reference, and their brightness. The user configures the number of baselines at start and at end. 
- Baseline trials use the stimulusPeriods, and intertrialWaits as 
- TrialNumber starts at 1001 for baseline periods and at 1 for stimulus trials.
- Configurable parameters: steps [2 50],LEDA (one of the 5 LEDs), maxA=<int>, minA=<int>, LEDB (one of other 4 LEDs), maxB=<int>, minB=<int>,BackgroundStim1LED (one of remaining 3), BackgroundStim1INT ([0 4095]),  BackgroundStim2LED (one of remaining 2), BackgroundStim2INT ([0 4095]), Ref1LED (one of 5 LEDs), Ref2LED (one of 4 LEDs), Ref3LED (one of 4 LEDs), Ref1INT ([0 4095]), Ref2INT ([0 4095]), Ref1INT ([0 4095]), BaselineLEDs (can be nothing, or all of them), baselineIntensities (value for [0 4095] for the selected baseline LEDs) [This needs to be defined better], nBaselinesStart=<int>, nBaselinesEnd=<int>, freq, trialLength [200 30000], interTrialWait [50 30000], hue (bool) [This behavior most be better defined], order [0 4]
- A set of default values should be chosen, so they don't all need to be defined when testing.
- The trigger signal must always be sent. It defines the start and end of stimulus periods and intertrialWaits. In the firmware the accompaning signal should also be used as it is used to interact with EEG recording devices. 

### Sub-mode D —  Behavioral

- Like the subjectExperiment behavioral mode but all LED selections are configurable.
- The configuration for flickering is stimulation is similar to that of the Grid mode.
- The flickering LEDs in this experiment will be called LEDA and LEDB, happens on the first part of the period the stim period (controlled by the hardware timer). The user configures LEDA (out of the 5), LEDB (other 4) they can also add 2 constant values out of the other 3 LEDs. 
- The second part of the period (controlled by hardware timer) will be called the reference period. for this one, the user has the ability to set up to 3 LEDs with fixed values. 
- knobs (ADCs) Control the intensity of LEDA, LEDB. 
- variability, trial count, pushbutton, should follow the guidelines in prototype2/Firmware/behavioralExperiment.{cpp,h}
- Serial printing to be done every 100 ms. This will be used by the GUI to plot the location of information in real time. 
- Participant pushes a button when they feel they have reached a metamer. This is registered by press (and the GUI).
- Configurable parameters: LEDA (one of the 5 LEDs), maxA=<int>, minA=<int>, LEDB (one of other 4 LEDs), maxB=<int>, minB=<int>,BackgroundStim1LED (one of remaining 3), BackgroundStim1INT ([0 4095]),  BackgroundStim2LED (one of remaining 2), BackgroundStim2INT ([0 4095]), Ref1LED (one of 5 LEDs), Ref2LED (one of 4 LEDs), Ref3LED (one of 4 LEDs), Ref1INT ([0 4095]), Ref2INT ([0 4095]), Ref1INT ([0 4095]), freq.
- No support for hue sensor in this experiment. 

### Serial configurability

All sub-modes accept runtime configuration commands for [See firmware requirements above]

---

## Deliverable 4 — Configurable Firmware GUI

**Output path:** `prototype2/GUI/configurableFirmware/`

Same stack and features as the subjectExperiment GUI, plus:

- Save and load experiment configurations (JSON or similar).
  - Saving captures all current parameter settings.
  - Loading restores them and re-sends all configuration commands to the Teensy.
- Sub-mode selector (Grid / Steps / Solid / Behavioral).
- Selection of hue vs normal for modes that support it.
- LED assignment controls for each phase [Baselines, Stimulation, Reference] these are LEDA, LEDB, backgroundSTim1, backgroundSTim2, Ref1LED, Ref2LED, Ref3LED. Must avoid selecting the same LED for the same phase.  
  This means that Red LED cannot be chosen twice in the baselines, or references. However, it can be used for Baselines, stimulation, and reference. 
- All other configurable parameters exposed in the UI, depending on the experimental mode selected. This means, just expose the configurable parameters pertinent to a given experiment. 
- We will Add spport for saving data later in the process
---


## Constraints and conventions

- Firmware: Teensy 4.0, Arduino IDE, manual flash + test cycle.
- Python: `uv` only for all package management.
- Modular firmware: no experiment-specific names in shared modules.
- Lux is included in hue-mode serial frames (from TCS34725); no standalone lux sensor.
- No over-engineering: match the simplicity level of prototype1 code.
- Documentation in `docs/prototype2/`.
- PLAN.md tracks milestones and checklists.

### Sub-mode A — Solid
Upon selection of solid mode and hue, the experiment screen appears. It should be 5 sliding bars side to side. Each of these bars controls the brightness of an LED. Each will have a square on top or under with the corresponding color (LED they control)
  - Red #f70404
  - Yellow #fabd04
  - Green #b1ff01
  - Blue #0493ff
  - Cyan #50fefe 
The current value of the slider should be also seen in a text box, the participant can interact and change values in this text box. 
  - If the hue sensor is active, on the right panel of the screen we can show the current value of the hue sensor Red, green and blue channels (maybe as a bar plot.)
  - If the hue sensor is active, and the participant presses the button, a row with the data of the current setup is appended (similar to what we do with the behavioral experiment in prototype2)
    - This will used for saving data later.
No saving/loading configuration needed here.
We need buttons to return to the experiment selection screen.

### Sub-mode B — Linear 
- Upon selection of linear experiment, user is asked whether they want to start the experiment with loading experimental setup, or configure it themseleves:
- If configuration is selected, we can decide to save it, files should have "linearParamCongif_" in the name
- Hue activation is one of the parameters to select.
- LEDs show color when selected for the different experimental phases Red #f70404, Yellow #fabd04, Green #b1ff01, Blue #0493ff, Cyan #50fefe 
- The Linear experiment screen should show a progress bar, as well as currentrepetition/total number of repetition label. 
- Important experiment configuration should be shown (similar to what the subjectExperiment Gui already does in the bottom of the screen).
- If the hue is selected. We show cummulative plots on the screen for the red, green and blue channel (all in the same plot) [must define what to do with the y axis limits]. A plot that shows what were the mean red, mean green and mean blue values for each step.
- hue data should be saved as Linearhue_exp_timeStamp, as a .txt file. This means if we are saving data ALL time stamps sent by teensy must be logged to a .txt file This also includes current LED values.
- we will show data as LEDA ("Selected LED") when needed. That way the user is clear what LED is being used.

### Sub-mode C — Grid 
- Upon selection of grid experiment, user is asked whether they want to start the experiment with loading experimental setup, or configure it themseleves:
- If configuration is selected, we can decide to save it, files should have "gridParamCongif_" in the name
- Hue activation is one of the parameters to select.
- LEDs show color when selected for the different experimental phases Red #f70404, Yellow #fabd04, Green #b1ff01, Blue #0493ff, Cyan #50fefe 
- The Linear experiment screen should show a progress bar, as well as currentrepetition/total number of repetition label. 
- The grid is displayed as it is done in the current prototype2 grid experiments that shows current point, and visited points.  
- Important experiment configuration should be shown (similar to what the subjectExperiment Gui already does in the bottom of the screen).
- If the hue is selected. We show cummulative plots on the screen for the red, green and blue channel (all in the same plot) [must define what to do with the y axis limits]. A plot that shows what were the mean red, mean green and mean blue values for each step.
- hue data should be saved as Gridhue_exp_timeStamp, as a .txt file. This means if we are saving data ALL time stamps sent by teensy must be logged to a .txt file This also includes current LED values.
- x axis of the grid should be (LEDA ("SelectedLED"))
- y axis of the grid should be (LEDB ("SelectedLED"))

### Sub-mode D —  Behavioral

- No hue support.
- Configuration should adopt all the changes for the firmware to work.
- Plotting should be done like it is in prototype2/GUIsubjectExp.
  - Real time plotting of x coordinate (LEDA intensity), vs. y coordinate (LEDB intensity)
  - x axis of the grid should be (LEDA ("SelectedLED"))
  - y axis of the grid should be (LEDB ("SelectedLED"))
- When presses happen, it adds rows to a table on the right 
- it keeps a rolling median of the values and presents it on screen.
- To do later, we will save data with the stimulator status at button presses.
