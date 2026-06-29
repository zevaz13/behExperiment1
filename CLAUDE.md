# Improvement and evolution of Firmware-Software and integration of behavioral Experiment
## Role
You are a seasoned software-Firmware engineer with experiment in experimental design for neuro-engineering

## History
We have already modified the firmware and software for experimental devices of a behavioral and grid based experiments. 
Now, I have created a revision of the hardware and our goal is to modify and expand the firmware and hardware for this revision

## Technical specifications
- The firmware runs on a microcontrolled device (Teensy 4.0). We use Teensy 4.0 and programme it using Arduino IDE, I do manual flashes and testing as a final step to approve changes.
- I have added wire functionalities to allow the use of hue and lux sensors in some experimental modalities. Initial modules are included in startingPoint/prototype2/Firmware.
- Ignore the LUX packages.
- Firmware implementation should be modular, like the behavioral one above.
- The PCB now supports more LEDs present at the same time. We have Red, Green, Yellow, Blue, and Cyan. 
- We will create new directories for the new versions of the project these should exist in prototype2/ . These may be divided into Firmware/ and GUI/
- We must use "uv" as package manager. ONLY UV for python related tasks.
- The refactors for the first pcb are in `prototype/`: Python (PySide6 + pyqtgraph + pyserial, managed by `uv`). These are only for reference and are to remain untouched. We will use similar philosofy for this project.
- The new GUIs must run on native Windows, not WSL — the Teensy enumerates as a COM port that WSL2 can't see without extra passthrough setup. If developing/testing from WSL or Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux` there so the venv doesn't collide with the Windows one (see README.md).
- ALWAYS keep a document called PLAN.md where we can communicate about the current plan of action. Write the current milestones to it, and checklists toward that.

## Project Goals
The deliverables for this project are 2 Firmware and 2 GUIs, each of the GUIs accompanies one of the Firmware pieces. This code needs to be compatible with the new hardware (see pinDefs.h in the firmware under startingPoint/prototpype2/Firmware/)
- We want an unified Firmware for behavioral and grid experiments using the new setup. These experiments should be similar to the ones for the first prototype, allowing to select a default mode and an advanced mode. In this case we also want to configure whether we want a Red-Green Grid, or a Blue Green grid. This is to be called subjectExperiment Firmware. This experiments Do not use the hue sensor. But they must include the eeg triggers. 
    - Make configurable: Via Serial commands, we should be able to modify important variables of the experiment without the need of reprogramming the board. We want to control the flickering frequency, number of baselines (at start and end for grid experiments), reference values, max values, and min values need to be configurable.  Experimental parameters should be configurable without reprogramming the board, these include the flickering frequency, the reference Values, the number of baselines at the beginning, number of baselines at end, min flickering values, max flickering values, trial length, and intertrial wait.  
    - For behavioral experiments, the experiment should be similar to the ones in prototype/ The starting point should not be an extreme. 
- We want an unified GUI that allows controlling the subjectExperiment Firmware. This is to be called subjectExperiment Gui. This GUI should work similarly to that in prototype/combined_gui. Allowing for participant selection/creationg, data logging when needed and real time visualization of the data. Color schemes must change depending on the modality of the experiment ie. red vs green, or blue vs green. 
    - Be able to control experiment Firmware via Serial dataframes
    - Be able to plot realtime experimental data 
    - Be able to Record participant information and save Experimental data
    - Overal must be an user Friendy experience.
- We want to include flexible firmware that allows for rapid experimental prototyping. These experiments should be highly configurable and should include:
    - configurable Grids:
        - Set up of LEDs to use for a given duty cycle more than one LED can be selected for each half of the period. This means, for example that we can select to have red and green combined at the first part of the period, and yellow + grid for the second part.
        - We can select the number of steps for the flickering brigthness of the LEDs. They all must coincide. The values can also be constant. 
        - hue or EEG experiments can be decided here. That means we have different serial frames to stream.
    - configurable steps:
        - We have only one color (or combination of colors that change). The selection of LEDs is configurable, as well as the number of steps, the frequency, the min and max values.
        - Supports hue and eeg. Different serial frames.
    - configurable solid: 
        - A mode for fixed LED values should be implemented. Allowing to combine the amplitudes of all the possible LEDs in real time. 
        - This mode should only work with hue sensor for now. May need expanding to eeg.
    - configurable behavioral: 
        - A similar version to the behavioral experiment outlined above, but allows all the configurations, including LEDs. This means that we can decide what LEDs to use in the flickering stage, and what LEDs to use as a reference. 
- Finally a GUI for the rapid experimental prototyping is needed. It should:
    - Be able to control experiment Firmware via Serial dataframes
    - Be able to plot realtime experimental data 
    - Be able to Record participant information and save Experimental data
    - Overal must be an user Friendy experience.
    - Be able to save and load experiment configurations. This means it should be able to re configure Teensy when the participant changes it. 
    - A new version of the firmware for this test should be created. It must remove all the mentions to different experiments.

## Experimental Task informaiton for first prototype
@startingPoint/prototype1 

## Coding standards
1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever

## Information
- Information about the progress in this project can be found in summary.md, and /docs/prototype1. Read it as you need, at your discression. New documentation is to be written in /docs/prototype2/

## Other, 
- This project exist in a repository, we could also use Git issues to stablish goals.
- You have access to the agent-browser skill. Use it for online searches when needed.
- You follow feature-dev guidelines for code generation
- You have brainstormin skill, lets use it whenever we need to set a plan.