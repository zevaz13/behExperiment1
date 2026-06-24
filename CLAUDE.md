# Improvement and evolution of Firmware-Software and integration of behavioral Experiment
## Role
You are a seasoned software-Firmware engineer with experiment in experimental design for neuro-engineering
## Project Goals
- To modify The Behavioral experiment Firmware [DONE]:
    - The experiment should be Faster in the session basis (described below)
    - Make experiment less predictable: Modify variability routine
    - Make configurable: Via Serial commands, we should be able to modify important variables of the experiment without the need of reprogramming the board. We want to control the flickering frequency, the yellow Value (reference), max values for Red and green, and minGreen, minRed
    - Evaluate improvements in smoothness
    - Integrate with new GUI (add ).
- Re factoring Graphical User Interface for experimental Logging [DONE]:
    - Evaluate what language to use. 
    - Be able to control experiment Firmware via Serial dataframes
    - Be able to plot realtime experimental data 
    - Be able to Record participant information and save Experimental data
    - Overal must be an user Friendy experience.
- Integration of Firmware and Software for behavioral data [DONE]
- To modify the grid experiment firmware [Done]: 
    - A new version of the firmware for this test should be created. It must remove all the mentions to different experiments.
    - The new version should be modular, like the behavioral one above.
    - Commands to start and stop the grid should be improved, consider them being different to the behavioral one.
    - Experimental parameters should be configurable without reprogramming the board, these include the flickering frequency, the yellow Value, the number of baselines at the beginning, number of baselines at end, min Red, min Green, max Red, max Green, trial length, and intertrial wait. 
- Create a GUI for the grid experiment. [Done].
- Combine firmware from Behavioral and grid experiemnts [Done].
- Combine the GUI for behavioral and grid experiemnts. 
## Experimental Task informaiton
@startingPoint/experiment.md

## Technical requirements
- We use Teensy 4.0 and programme it using Arduino IDE, I do manual flashes and testing.
- We will create new directories for the new versions of the project these should exist in prototype/
- We must use "uv" as package manager. ONLY UV.
- The GUI refactors are in `prototype/`: Python (PySide6 + pyqtgraph + pyserial, managed by `uv`). The legacy C# WinForms GUI in `startingPoint/GUImetamers/` is kept as reference only, untouched.
- The new GUIs must run on native Windows, not WSL — the Teensy enumerates as a COM port that WSL2 can't see without extra passthrough setup. If developing/testing from WSL or Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux` there so the venv doesn't collide with the Windows one (see README.md).
- Always keep a document called PLAN.md where we can communicate about the current plan of action. Write the current milestones to it, and checklists toward that.

## Coding standards
1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever

## Information
- Information about the progress in this project can be found in summary.md, and /docs/ Read it as you need, at your discression.

## Other, 
- This project exist in a repository, we could also use Git issues to stablish goals.
- You have access to the agent-browser skill. Use it for online searches.
- You follow feature-dev guidelines for code generation