# Behavioral test description and results

## Overview

This document summarizes the structure of the behavioral test of the metamers project. This test is also known as the "knobs test". 
This is a behavioral test that asks the participant to identify the right combination of red and green settings (as D/A units, or LED intensities) that better correspond to the a yellow fixed setting. Multiple runs of the experiment are obtained per session.
In the experiment, each run starts from a random starting position (red, green) coordinate. The participant should use the knobs until they find a metamer (blinkiness reduced and a solid yellow color is achieved):
Once they do, they press a button that logs the data. 

We use Teensy 4.0. to control the stimulator via firmware written in Arduino c (c++) in the Arduino IDE. This device controls LEDs using PWM variables, we record data using ADC from knob-like devices (we like good resolution here) and a push button.
We have a very simple GUI that communicates with Teensy using serial dataframes. This GUI also is used as an experiment logger. Creating particiaptns and saving data in txt files.

## Data Frame Structure

Each repetition of the test produces a serial data stream with the following fields:

| Field | Description |
|---|---|
| `TriggerCue` | Not of interest. |
| `TrialNumber` | Not of interest. |
| `Amber` | Fixed value should be 2400. |
| `red` | result for current trial red dimension. |
| `green` | result for current trial green dimension.|
| `Press` | to reggister the button presses. |

## Firmware

We use a FSM to communicate using the above shown dataframe/  
We use pwms with resolution of 12 bits/  
We use ADC with resolution of 12 bits/  
LEDs are controlled via hardware timers/ 
The button is observed using interruptions/  
The experiment smooths data during 50 ms, producing more stable values for red and green.
I have implemented a system to add variability to the measurements, this is so the participant does not learn the location of final settings/  
The button press ends a trial (meaning that we have to restart from here.)/  
The button press associated print statement is repeated for redundancy and to respond to an already fixed bug./  

##  Experimental variables 

The flicker frequency is **10 Hz**.  
minRed  should be 0 (I know it is 300 now)  
minGreen 0
maxRed 3000 
minGreen 2000 

## Flickering frequency
Each 10 Hz cycle consists of:

* 50% duty cycle red+green combination which changes (The participant controls these with the knobs, independently)
* 50% duty cycle fixed yellow always the same value


## Summary

The knobs experiment produiced a cloud of points in a 2D space (RED, Green) for what are the required amount of green and red components of the LED settings to achieve a metamer with flashing at 10 Hz.
