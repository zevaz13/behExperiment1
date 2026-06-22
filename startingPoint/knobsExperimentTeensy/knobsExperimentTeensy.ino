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

// bounce object. From library. This controls the interruption for the push button.
Bounce pushbutton = Bounce();

// flashing information for frequency
int timeFlash10 = 50; // 50 = 10HZ, 
int flash10T = 30;
int D = 12; // This selects the resolution 

// ***** randomWalk 
const int numVals = 12; //This should be done for the combination in Random Mode

int redVals[numVals];       
int greenVals[numVals]; 

struct Pair {
  int red;
  int green;
};


unsigned int maxRed         = 3000;
unsigned int minRed         = 300;
unsigned int maxGreen       = 2400;
unsigned int minGreen       = 300;

// ***** linear wallk parameters

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
unsigned int trialLength      = 1000; // lenght of the trial (ms)
unsigned int interTrialWait   = 50; // wait between trials (ms)

volatile int outputValueRed   = 0;       // Adjusted value for RED
volatile int outputValueGreen = 0;     // Adjusted value for GREEN

volatile unsigned int mode    = 0;

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

const int numSamples = 10;  // Number of samples for averaging
const int sampleInterval = 5;  // Time between samples in milliseconds

// // Smoothing factor (0 < alpha < 1), closer to 1 updates faster
const float alpha = 0.5;

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
// ********* Definition of functions ********* //
// interruption handler. does this have to be managed with an interrupt, or can it be its own thread? 
void handleButtonPress() 
{
  unsigned long currentMillis = millis();
  if (currentMillis - timeBounc > 250)
  {
    switch (mode){
      case 0:
        currRED   = 0;
        currGREEN = 0;
        currAMBER = 0;
        //Serial.println("MEHHH");
      break;

      case 1: //random walk mode
        Serial.println("boing");
      break;

      case 2: //variable resistorMode
        currRED   = 0;
        currGREEN = 0;
        currAMBER = 0;
        
        print_varResmode();

      break;

      case 3: // linear walk red 2 green EEG
        Serial.println("boing");
      break;

      case 4: // linear walk green 2 red EEG
        Serial.println("boing");
      break;

      case 5: // linear walk red 2 green, behavioral
        Serial.println("boing");
      break;

      case 6: // linear walk green 2 red, behavioral
        Serial.println("boing");
      break;

      default:
        Serial.println("invalid");
      break;
    }
    timeBounc = millis();
  }
}
void print_varResmode(){
  // Once the participant presses the button, we stop excecution and record the current values
  String dataFrame = String(0) + "@" + 
                        String(0) + "@" + 
                        String(amberVal) + "@" + 
                        String(outputValueRed) + "@" + 
                        String(outputValueGreen) + "@" + 
                        String(0);
  //String dataFrame = "0 @ 0 @ 0 @ " + String(outputValueRed) + " @ " + String(outputValueGreen) + "@ 0 ";
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
  Serial.println(dataFrame);
                      // Send the data frame via Serial
  Serial.println(endOfFrame);
  started = false; 
  mode    = 0;
}
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
        case 1:
        Serial.println("boing");
        break;

        case 2:
          REDState    = true;
          GREENState  = true;
          AMBERState  = false;
          currAMBER   = amberVal;
          var_nob_exp();
        break;

        case 3:
          Serial.println("boing");
        break;

        case 4:
          Serial.println("boing");
        break;

        case 5:
          Serial.println("boing");
        break;

        case 6:
          Serial.println("boing");
        break;

        case 7:
          Serial.println("boing");
        break;

        default:
          Serial.println("paila, bebe");
        break;
      }
    started = false;
    }
  }     
}


void var_nob_exp () {
// Read the analog inputs
  controlTimerAmber(true);
  controlTimerRed(true);
  controlTimerGreen(true);

  while(true)
  {
    if (started == false) 
    {
    mode      = 0;
    currAMBER = 0;
    currRED   = 0;
    currGREEN = 0;
    break;}

   unsigned long startTime = millis();
unsigned long lastSampleTime = startTime;
int sampleCount = 0;
int sumRed = 0, sumGreen = 0;

int sensorValueRed   = 0;
int sensorValueGreen = 0;

while (millis() - startTime < 50) {
    if (millis() - lastSampleTime >= sampleInterval) {
        lastSampleTime = millis();  // Update the last sample time

        sensorValueRed   = analogRead(AIred);
        sensorValueGreen = analogRead(AIgreen);

        sumRed   += sensorValueRed;
        sumGreen += sensorValueGreen;
        sampleCount++;

        if (sampleCount >= numSamples) {
            break;  // Stop sampling once we've collected numSamples
        }
    }
}

// Compute the average values if at least one sample was taken
if (sampleCount > 0) {
    int avgRed   = sumRed / sampleCount;
    int avgGreen = sumGreen / sampleCount;

    // Adjust red sensor value
    int adjustedValueRed = avgRed + initialOffsetRed;
    //int adjustedValueRed = avgRed + 0;

    if (adjustedValueRed > 4095) {
        adjustedValueRed -= 4095;
    }

    // Adjust green sensor value
    int adjustedValueGreen = avgGreen + initialOffsetGreen;
    //int adjustedValueGreen = avgGreen + 0;

    if (adjustedValueGreen > 4095) {
        adjustedValueGreen -= 4095;
    }

    // Map the averaged and adjusted values
    outputValueRed   = map(adjustedValueRed, 0, 4095, 0, maxRed);
    outputValueGreen = map(adjustedValueGreen, 0, 4095, 0, maxGreen);

    // Update current values
    currRED   = outputValueRed;
    currGREEN = outputValueGreen;


    // currRED = (alpha * outputValueRed) + ((1 - alpha) * currRED);
    // currGREEN = (alpha * outputValueGreen) + ((1 - alpha) * currGREEN);

}
    // Serial.print(" Adjusted GREEN: ");
    // Serial.print(outputValueGreen);
    // Serial.print("  GREEN: ");
    // Serial.print(currGREEN);

    // Serial.print(" Adjusted RED: ");
    // Serial.print(outputValueRed);
    // Serial.print("  RED: ");
    // Serial.println(currRED);

    }
  }


// ******************** Manage the serial port to file ****************** // 
// Function to send serial data at 50 Hz
void sendSerialData() 
{ 
  // This mode is only uysed in R2G and G2R 
  unsigned long serialPeriod = (1000 / SERIAL_FREQ);  
  while (true) 
  {
    if (mode == 3 || mode ==4)
    {
      if (started == true) 
      {
      // Construct the data frame, using "@" as a separator
      String dataFrame = String(trigFlag) + "@" + 
                        String(trCnt) + "@" + 
                        String(currentAmberTri) + "@" + 
                        String(currentRedTri) + "@" + 
                        String(currentGreenTri) + "@" + 
                        String(pressFlag);
                        // Send the data frame via Serial
    Serial.println(dataFrame);
    // Delay for 50 Hz (non-blocking delay)
    threads.delay(serialPeriod);
      }
    }
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

//////// **************************** config chunk

void setup() {
  Serial.begin(38400);
  // Here we set up the pins as outputs. This is what we will be controlling.
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // This is the configuration required to get the button ready
  pushbutton.attach(BUTTON_PIN); 
  pushbutton.interval(200);

  // attach an interrupt to the button pin, triggered by a falling edge, since we are using a pull up resistor
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN),handleButtonPress, FALLING);

  // init pins for other LEDs
  pinMode(AMBER, OUTPUT);
  pinMode(RED, OUTPUT);
  pinMode(GREEN, OUTPUT);
  pinMode(trigger, OUTPUT); // Not sure what this does

  // set the PWM resolution to 4096 
  analogWriteResolution(12);
  analogReadResolution(12); // Values range from 0 to 2047

  // // thread to handle button press
  timeBounc = millis();
  while (!Serial);  // Wait for serial connection
  Serial.println("Teensy is ready and waiting for the start number...");
  // Create a thread to control LED 
  threads.addThread(amber_red_green,1);
  //threads.addThread(adc_reads,2);
    // Create a thread for sending serial data
  threads.addThread(sendSerialData,2);
}
void loop() 
{
  pushbutton.update();  

  if (started == false) 
  {
    if (Serial.available() > 0) 
    {    
      String command = Serial.readStringUntil('\n');  // Read command until newline
      Serial.print("Received command: ");  // Print received command for debugging
      Serial.println(command);

      if (command == "1789") // variable resistor experiment. Dials 
      {  
        reset_board();

        threads.delay(10);
        //initialOffsetRed    = analogRead(AIred);
        //threads.delay(10);
        //initialOffsetGreen  = analogRead(AIgreen);
        initialOffsetRed    = random(0, 1500);
        initialOffsetGreen  = random(0, 500);


        mode = 2; // Var random expt. stops at button press.
        started   = true;
        Serial.println("Starting execution of variable resistor experiment");
      }
      // Command 2789 = Random walk experiment 
      else if (command == "2789") 
      {
        Serial.println("Starting execution of rand Walk experiment");
      } 
      else if (command == "3789") // linear EEG R2G
      {
        Serial.println("Starting execution of lin Walk EEG experiment R2G");
      } 

      else if (command == "4789") // linear EEG Green2Red
      {
        Serial.println("Starting execution lin Walk EEG experiment G2R");
      } 

      else if (command == "5789") // linear R2G beh
      {
        Serial.println("Starting execution of lin Walk beh experiment R2G, stops at button press");
      }

      else if (command == "6789") // linear beh Green2Red
      {
        Serial.println("Starting execution of lin Walk beh experiment G2R, stops at button press");
      }  
      else if (command == "7789") // set constant values for RED and Green
      {
        // Using a loop to copy the elements
        Serial.println("provide values for red and green separated by @, RED@green");
      }  
    }  
  }  
  // This is the code for stopping the excecution. 
    else 
    {
      if (Serial.available() > 0) 
      {
      String command = Serial.readStringUntil('\n');  // Read command until newline

        if (command == "6969")
        {
          mode = 0;
          reset_board();
          started   = false;
          Serial.println("Stopping, senpaii...");
        }   
        
        }
      }
}
