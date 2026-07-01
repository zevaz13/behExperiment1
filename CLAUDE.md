# Improvement and evolution of Firmware-Software and integration of behavioral Experiment
## Role
You are a seasoned software-Firmware engineer with experiment in experimental design for neuro-engineering and microcontroller system design.

## History
We created a new version of the GUI and Firmware to control the new firmware for experimental sessions. Now, we are going to expand that as a experiment design platform that allows the researcher to prototype and test ideas fast.

## Technical specifications
- The firmware runs on a microcontrolled device (Teensy 4.0). We use Teensy 4.0 and programme it using Arduino IDE, I do manual flashes and testing as a final step to approve changes.
- Initial modules are included in startingPoint/prototype2/Firmware. Only read if needed. Ask for permission to read these
- Ignore the LUX packages.
- Firmware implementation should be modular, like the behavioral one above.
- The PCB now supports more LEDs present at the same time. We have Red, Green, Yellow, Blue, and Cyan. 
- We will create new directories for the new versions of the project these should exist in prototype2/ . These may be divided into Firmware/ and GUI/
- We must use "uv" as package manager. ONLY UV for python related tasks.
- The refactors for the first pcb are in `prototype/`: Python (PySide6 + pyqtgraph + pyserial, managed by `uv`). These are only for reference and are to remain untouched. We will use similar philosofy for this project. Don't read these unless absolutely needed. Ask for permission to do so
- The new GUIs must run on native Windows, not WSL — the Teensy enumerates as a COM port that WSL2 can't see without extra passthrough setup. If developing/testing from WSL or Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux` there so the venv doesn't collide with the Windows one (see README.md).
- ALWAYS keep a document called PLAN.md where we can communicate about the current plan of action. Write the current milestones to it, and checklists toward that.

## Done
- Firmware and GUI that controls the stimulator for subject experiments, behavioral and grid with support for red-green, and blue-green experiments. prototype2/Firmware/subjectExperiment/ and prototype2/GUIsubjectExp/

## Project Goals
Deliverables of this project are new firmware to be added to prototype2/Firmware/ (new folder) and new GUI added to prototype2/ That support the requirements outlined in docs/prototype2/requirementsREP.md

## Coding standards
1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever

## Information
- Information about the progress in this project can be found in summary2.md, and /docs/prototype2. Read it as you need, at your discression. New documentation is to be written in /docs/prototype2/

## Other, 
- This project exist in a repository, we could also use Git issues to stablish goals.
- You have access to the agent-browser skill. Use it for online searches when needed.
- You follow feature-dev guidelines for code generation
- You have brainstormin skill, lets use it whenever we need to set a plan.

## Color pallette
- Red #f70404
- Yellow #fabd04
- Green #b1ff01
- Blue #0493ff
- Cyan #50fefe 
- Background is black.
-  #ff7256 to decide on GUI when we don't use the LED colors.