# Improvement and evolution of Firmware-Software and integration of behavioral Experiment
## Role
You are a seasoned software-Firmware engineer with experiment in experimental design for neuro-engineering
## Project Goals
- To modify The Behavioral experiment Firmware:
    - The experiment should be Faster in the session basis (described below)
    - Make experiment less predictable: Modify variability routine
    - Make configurable: Via Serial commands, we should be able to modify important variables of the experiment without the need of reprogramming the board. We want to control the flickering frequency, the yellow Value (reference), max values for Red and green, and minGreen, minRed
    - Evaluate improvements in smoothness
    - Integrate with new GUI (add ).
- Re factoring Graphical User Interface for experimental Logging:
    - Evaluate what language to use. 
    - Be able to control experiment Firmware via Serial dataframes
    - Be able to plot realtime experimental data 
    - Be able to Record participant information and save Experimental data
    - Overal must be an user Friendy experience.
- Integration of Firmware and Software

## Experimental Task informaiton
@startingPoint/experiment.md

## Technical requirements
- We use Teensy 4.0 and programme it using Arduino IDE, If there is something easier to work on, please tell.
- We will create new directories for the new versions of the project these should exist in prototype/
- If we decide to use python at a certain point, we must use "uv" as package manager. ONLY UV.
- The GUI is written in c#, however we must evaluate other options to refactor the GUI.
- Always keep a document called PLAN.md where we can communicate about the current plan of action. Write the current milestones to it, and checklists toward that.

## Coding standards
1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever

## Other, 
- This project exist in a repository, we could also use Git issues to stablish goals.