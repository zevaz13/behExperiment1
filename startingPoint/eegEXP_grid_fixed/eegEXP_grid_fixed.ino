#include <Bounce2.h>
#include <TeensyThreads.h>
#include <IntervalTimer.h>

IntervalTimer timerAmber;
IntervalTimer timerRed;
IntervalTimer timerGreen;

// LED and pin definitions
#define BUTTON_PIN  20 //pin where button is connected
#define AMBER       0 
#define RED         3
#define GREEN       1
#define trigger     13

#define AIred       19
#define AIgreen     22

// configuration definitions for frequency
#define SQUARE_FREQ 10
#define SERIAL_FREQ 50

#define NUM_STEPS 10
#define NUM_STIMS (NUM_STEPS * NUM_STEPS)

const int greenMin = 0, greenMax = 2000;
const int redMin = 0, redMax = 3200;

float greenArray[NUM_STEPS];
float redArray[NUM_STEPS];
int coordinates[NUM_STIMS][2];
int newcoordinates[NUM_STIMS][2];
int expSequence[NUM_STIMS][2];

// bounce object. From library. This controls the interruption for the push button.
Bounce pushbutton = Bounce();

// flashing information for frequency
int timeFlash10 = 50; // 50 = 10HZ, 
int flash10T = 30;
int D = 12; // This selects the resolution 

unsigned int numBaselineTr = 1;
volatile int order = 0; //sizeof(redVals); size of doesn't return the number of elements, does number of bytes...

volatile int numValsLW = 20; //sizeof(redVals); size of doesn't return the number of elements, does number of bytes...

// So, depending on the command, redVals and greenVals are set. Start with default.
unsigned long halfPeriod = (1000 / (2 * SQUARE_FREQ));  // Calculate half period (50ms for 10 Hz) for blinking
// ****** Serial variables
// declare variables to send via serial. These might need to be volatile variables
unsigned int pressFlag        = 0;
unsigned int currentGreenTri  = 0;
unsigned int currentRedTri    = 0;
unsigned int currentAmberTri  = 0; 
unsigned int trCnt            = 0;
unsigned int trigFlag         = 0;

volatile bool started         = false;  // To track if the Teensy execution should start
unsigned long timeBounc       = 0.0;
unsigned int trialLength      = 3000; // lenght of the trial (ms)
unsigned int interTrialWait   = 750; // wait between trials (ms)

volatile int outputValueRed   = 0;       // Adjusted value for RED
volatile int outputValueGreen = 0;     // Adjusted value for GREEN

volatile unsigned int mode    = 0;

volatile unsigned int constantRed   = 0;
volatile unsigned int constantGreen = 0;

int initialOffsetRed    = 0;           // Initial random offset
int initialOffsetGreen  = 0;           // Initial random offset

volatile int currRED    = 0;
volatile int currGREEN  = 0;
volatile int currAMBER  = 0;
unsigned int amberVal   =  2400;

String endOfFrame = "~~~";
// this is a test for the timer controlling the amber thing

volatile bool AMBERState  = false;
volatile bool REDState    = true;
volatile bool GREENState  = true;

int state = 0;
// Function to toggle the AMBER LED
void toggleAmber() {
    AMBERState = !AMBERState;
    analogWrite(AMBER, AMBERState ?  currAMBER: 0);
}

// Function to start or stop the timer
void controlTimerAmber(bool enable) {
    if (enable) {
        timerAmber.begin(toggleAmber, halfPeriod*1000); // Start timer with 50 ms interval (10 Hz)
    } else {
        timerAmber.end(); // Stop the timer
    }
}

// Function to toggle the RED lED
void toggleRed() {
    REDState = !REDState;
    analogWrite(RED, REDState ?  currRED: 0);
}

// Function to start or stop the timer
void controlTimerRed(bool enable) {
    if (enable) {
        timerRed.begin(toggleRed, halfPeriod*1000); // Start timer with 50 ms interval (10 Hz)
    } else {
        timerRed.end(); // Stop the timer
    }
}

// Function to toggle the RED lED
void toggleGreen() {
    GREENState = !GREENState;
    analogWrite(GREEN, GREENState ?  currGREEN: 0);
}

// Function to start or stop the timer
void controlTimerGreen(bool enable) {
    if (enable) {
        timerGreen.begin(toggleGreen, halfPeriod*1000); // Start timer with 50 ms interval (10 Hz)
    } else {
        timerGreen.end(); // Stop the timer
    }
}
// ********* operational functions   ********* // 
void getLinSpacedArrays() {
      for (int i = 0; i < NUM_STEPS; i++) {
        greenArray[i] = greenMin + (greenMax - greenMin) * i / (NUM_STEPS - 1);
        redArray[i] = redMin + (redMax - redMin) * i / (NUM_STEPS - 1);
    }
}

void produceSequence() {
    // Generate diagonal coordinates
    int count = 0;
    int d = 2; // Diagonal index

    while (count < NUM_STIMS) {
        if (d % 2 == 1) {
            // Odd diagonal: move downward (increasing x, decreasing y)
            for (int x = 1; x <= min(d - 1, NUM_STEPS); x++) {
                int y = d - x;
                if (y > 0 && y <= NUM_STEPS) {
                    coordinates[count][0] = x;
                    coordinates[count][1] = y;
                    count++;
                }
                if (count >= NUM_STIMS) break;
            }
        } else {
            // Even diagonal: move upward (increasing y, decreasing x)
            for (int y = 1; y <= min(d - 1, NUM_STEPS); y++) {
                int x = d - y;
                if (x > 0 && x <= NUM_STEPS) {
                    coordinates[count][0] = x;
                    coordinates[count][1] = y;
                    count++;
                }
                if (count >= NUM_STIMS) break;
            }
        }
        d++; // Move to the next diagonal
    }
}

void modSeqOrder(int order) {

    switch (order){
    
    // order 1 starts from 1,1
    case 1:
      for (int i = 0; i < NUM_STIMS; i++) {
        newcoordinates[i][0] = coordinates[i][0]; // Keep X
        newcoordinates[i][1] = coordinates[i][1]; // Keep Y
      }
      
    break;

    // order 2 starts from 1, Maxy
    case 2:
      for (int i = 0; i < NUM_STIMS; i++) {
        newcoordinates[i][0] = coordinates[i][0]; // Keep X
        newcoordinates[i][1] = NUM_STEPS + 1 - coordinates[i][1]; // Flip Y
      }
    break;
    // order 3 starts from MaxX, 1
    case 3:
      for (int i = 0; i < NUM_STIMS; i++) {
        newcoordinates[i][0] = NUM_STEPS + 1 - coordinates[i][0]; // Flip X
        newcoordinates[i][1] = coordinates[i][1]; // Keep Y
      }
      
    break;
    // order 4 starts from MaxX, MaxY
    case 4: 
      for (int i = 0; i < NUM_STIMS; i++) {
        newcoordinates[i][0] = NUM_STEPS + 1 - coordinates[i][0]; // Flip X
        newcoordinates[i][1] = NUM_STEPS + 1 - coordinates[i][1]; // Flip Y
      }
    default:

    break;
    }

    Serial.print(" Coordinates Order "); Serial.println(order);
    for (int i = 0; i <= NUM_STIMS - 1; i++) {
      Serial.print(newcoordinates[i][0]);
      Serial.print(", ");
      Serial.println(newcoordinates[i][1]);
  }
}

void getExpSequence(int order) {
    modSeqOrder(order);
    for (int i = 0; i < NUM_STIMS; i++) {
      expSequence[i][0] = redArray[newcoordinates[i][0] -1]; 
      expSequence[i][1] = greenArray[newcoordinates[i][1] -1]; 
    }

    Serial.print(" Exp Sequence Order "); Serial.println(order);
    for (int i = 0; i < NUM_STIMS; i++) {
      Serial.print(expSequence[i][0]);
      Serial.print(", ");
      Serial.println(expSequence[i][1]);
  }
}

// ********* Definition of functions ********* //
// interruption handler. does this have to be managed with an interrupt, or can it be its own thread? 

// ********* Functions for printing and stoping excecution ********* //

// Function to control LED brightness with square wave. This function presents the experiment 
void amber_red_green() 
{
  while (true) 
  {
    if (started == true)
    {
      switch (mode){
        case 0:
          currRED   = 0;
          currGREEN = 0;
          currAMBER = 0;
          controlTimerAmber(false); // Start the LED blinking
          controlTimerRed(false);
          controlTimerGreen(false);
        break;
        // grid experiment 
        case 1:
          REDState = true;
          GREENState = true;
          AMBERState = false;

          blink_red_green(); // red to green EEG
        break;
        // fixed experiment 
        case 2:
          REDState = true;
          GREENState = true;
          AMBERState = false;

          blink_red_green_fixed(); // red to green EEG

        break;

        default:
          Serial.println("paila, bebe");
        break;
      }
    started = false;
    }
  }     
}

void blink_red_green() 
{
  if (started == true)
  {
    // Present baseline trials
    baseline_trial(numBaselineTr);
    
    // Keep the LED pulsing at 10 Hz for x seconds
    for (int i = 0; i < NUM_STIMS; i++) 
    {
      if (started==false) {break;
      currAMBER = 0;
      currRED   = 0;
      currGREEN = 0;
      mode      = 0;}

      trCnt           = i+2;
      Serial.print("Stim No: "); Serial.print(i+1); Serial.print(" red: "); Serial.print(expSequence[i][0]);  Serial.print(" green: "); Serial.println(expSequence[i][1]); 

      currentRedTri   = expSequence[i][0];
      currentGreenTri = expSequence[i][1];
      currentAmberTri =0;
      // Keep the LED pulsing at 10 Hz for 3 seconds
      controlTimerAmber(true);
      controlTimerRed(true);
      controlTimerGreen(true);
      digitalWrite(trigger, HIGH);

      unsigned long startTime = millis();
      while (millis() - startTime < trialLength) 
      {  // Loop for 3 seconds
        currentAmberTri = amberVal;
        currAMBER       = amberVal;
        currRED         = currentRedTri;
        currGREEN       = currentGreenTri;
      }
      digitalWrite(trigger, LOW);
      currRED         = 0;
      currGREEN       = 0;
      currAMBER       = 0;
      currentRedTri   = 0;
      currentGreenTri = 0;
      //set_trigVal(0);
      // now it is intertrial wait time
      threads.delay(interTrialWait);  // Wait 400 ms before moving to the next brightness level
    }
    baseline_trial(numBaselineTr);
    reset_board();
  started = false;
  }     
}

void blink_red_green_fixed() 
{
  if (started == true)
  {
    // Present baseline trials
    baseline_trial(numBaselineTr);
    
    // Keep the LED pulsing at 10 Hz for x seconds
    for (int i = 0; i < numValsLW; i++) 
    {
      if (started==false) {break;
      currAMBER = 0;
      currRED   = 0;
      currGREEN = 0;
      mode      = 0;}

      trCnt           = i+2;
      currentRedTri   = constantRed;
      currentGreenTri = constantGreen;
      currentAmberTri =0;
      // Keep the LED pulsing at 10 Hz for 3 seconds
      controlTimerAmber(true);
      controlTimerRed(true);
      controlTimerGreen(true);
      digitalWrite(trigger, HIGH);

      unsigned long startTime = millis();
      while (millis() - startTime < trialLength) 
      {  // Loop for 3 seconds
        currentAmberTri = amberVal;
        currAMBER       = amberVal;
        currRED         = currentRedTri;
        currGREEN       = currentGreenTri;
      }
      digitalWrite(trigger, LOW);
      currRED         = 0;
      currGREEN       = 0;
      currAMBER       = 0;
      currentRedTri   = 0;
      currentGreenTri = 0;
      //set_trigVal(0);
      // now it is intertrial wait time
      threads.delay(interTrialWait);  // Wait 400 ms before moving to the next brightness level
    }
    reset_board();
  started = false;
  }     
}
// Function for selecting the number of baseline trials of interest
void baseline_trial(unsigned int reps) 
{
  controlTimerRed(false);
  controlTimerGreen(false);
  controlTimerAmber(false);
  for (unsigned int ri = 0; ri <= reps; ri ++) 
  {
    analogWrite(AMBER, amberVal);
    digitalWrite(trigger, HIGH);
    // Consider getting these in a function
    currentAmberTri   = amberVal;
    trCnt             = ri + 1;
    trigFlag          = 1;
    threads.delay(trialLength);
    digitalWrite(trigger, LOW);
    analogWrite(AMBER, 0);
    currentAmberTri   = 0;
    trigFlag          = 0;
    trCnt             = ri + 1;
    threads.delay(interTrialWait);
  }
}

// *********** operative functions ************//
void reset_board() 
{
    // zero the hardware
    currRED   = 0;
    currGREEN = 0; 
    currAMBER = 0;
    // zero the variables 
    currentGreenTri   = 0;
    currentRedTri     = 0;
    pressFlag         = 0;
    currentAmberTri   = 0; 
    trCnt             = 0;
    trigFlag          = 0;
    delay(50); // pause for a brief moment
    Serial.println("Board was reset");
}
// Function to generate and scramble an array with values up to maxValue

//////// **************************** config chunk

void setup() {
  Serial.begin(38400);
  // Here we set up the pins as outputs. This is what we will be controlling.
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // This is the configuration required to get the button ready
  pushbutton.attach(BUTTON_PIN); 
  pushbutton.interval(200);

  // attach an interrupt to the button pin, triggered by a falling edge, since we are using a pull up resistor

  // init pins for other LEDs
  pinMode(AMBER, OUTPUT);
  pinMode(RED, OUTPUT);
  pinMode(GREEN, OUTPUT);
  pinMode(trigger, OUTPUT); // Not sure what this does

  // set the PWM resolution to 4096 
  analogWriteResolution(12);

  // // thread to handle button press
  timeBounc = millis();
  while (!Serial);  // Wait for serial connection
  Serial.println("Provide the experiment type: fixed or grid");
  // Create a thread to control LED 
  threads.addThread(amber_red_green,1);
  //threads.addThread(adc_reads,2);
}
void loop() 
{

  if (started == false) 
  {
    if (Serial.available() > 0) 
    {    
      String command = Serial.readStringUntil('\n');  // Read command until newline
      Serial.print("Received command: ");  // Print received command for debugging
      Serial.println(command);

      if (command == "fixed") {
        state = 1;
        Serial.println("Provide the experiment setting with the following format reps@RED!green");
      }
      else if (command == "grid") {
        state = 2;
        Serial.println("Provide the experiment setting (order) with the following format @order!");
      }
      switch (state){
        case 0:
          
        break;
        // state 1 checks experiment type = fixed
        case 1:{
          int atIndex = command.indexOf('@');
          int virgIdx = command.indexOf('!');

          if (atIndex == -1) {Serial.println("No @ detected");
          break;}
          if (virgIdx == -1) {Serial.println("No ! detected");
          break;}

          Serial.println(atIndex);
          Serial.println(virgIdx);

          String numReps      = command.substring(0, atIndex);            // Extract the part before '@'
          String redString    = command.substring(atIndex + 1, virgIdx);         // Extract the part after '@', before '!'
          String greenString  = command.substring(virgIdx + 1);

          Serial.println(numReps);

          numValsLW     = numReps.toInt();
          constantRed   = redString.toInt();     // Convert to integer and assign to constantRed
          constantGreen = greenString.toInt();

          mode    = 2;
          state   = 0;
          started = true;
          break;  
        }
        // state = 2 checks for experiment type = grid
        case 2:{
          int atIndex = command.indexOf('@');
          int virgIdx = command.indexOf('!');

          if (atIndex == -1) {Serial.println("No @ detected");break;}
          if (virgIdx == -1) {Serial.println("No ! detected");break;}

          Serial.println(atIndex);
          Serial.println(virgIdx);

          String orderString    = command.substring(atIndex + 1, virgIdx);         // Extract the part after '@', before '!'

          Serial.println(orderString);

          order     = orderString.toInt();

          // produce the sequences to test
          getLinSpacedArrays();
          produceSequence();
          getExpSequence(order);

          delay(1000);

          mode    = 1;
          state   =0;
          started = true;
          break;  
        }
      }
    }
  }
  else{
    if (Serial.available() > 0) 
    {    
      String command = Serial.readStringUntil('\n');  // Read command until newline
      Serial.print("Received command: ");  // Print received command for debugging
      Serial.println(command);

      if (command == "stop") {
        state   = 0;
        reset_board();
        started = false;
        Serial.println("stopping experiment");
      }
    }
  }
}

    
 