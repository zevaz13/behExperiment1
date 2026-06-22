// using System;
// using System.Windows.Forms;
// using RJCP.IO.Ports;

// namespace GUImetamers
// {
//     public partial class screen3RandBeh : Form
//     {
//         private Screen2 previousScreen; // Store a reference to the previous screen
//         private string expType;
//         private string subID;
//         private string command;
//         private string fileName;
//         private int expFlag;
//         private string folderName;
//         private const int samplesToSave = 100;
//         private int sampleCount = 0;

//         private StreamWriter? writer; // Class-level StreamWriter for the data file

//         private string newFileName;

//         private SerialPortStream serialPort;

//         private string currentFileName;
//         public screen3RandBeh(Screen2 screen2, int expMode, string SubjectID , string Folder, SerialPortStream port)
//         {
//             subID = SubjectID;
//             folderName = Folder;
//             InitializeComponent();
//             expFlag = expMode;
//             serialPort = port;
//             previousScreen = screen2; // Initialize the previous screen reference
            
//             switch (expMode)
//             {
//                 case 3:
//                     expType = "BehRandWalk";
//                     this.labelHeader.Text = "Random Behavioral Experiment";
                    
//                 break;
//                 case 4:
//                     expType = "VarTimPots";
//                     this.labelHeader.Text = "Var. Pots Experiment";
//                 break;
//                 default:
//                 break;
//             }
//         }

//         private void ActionButton1_Click(object sender, EventArgs e)
//         {
//             CloseFile();
//             this.Hide(); // Hide Screen 3
//             previousScreen.Show(); // Show Screen 2
//         }

//         private void ActionButton2_Click(object sender, EventArgs e)
//         {
//             this.actionButton1.Enabled = false;
//             this.actionButton2.Enabled = false;
//             this.actionButton3.Enabled = true;

//             fileName = subID + "_" + expType;
//             //this.infoLabel.Text = "Current file: " + fileName;

//             switch (expFlag)
//             {
//                 case 3: // if random Walk
//                     command = "2789";
//                 break;
//                 case 4: // if var pots
//                     command = "1789";
//                 break;
//                 default:
//                 break;
//             }
//             Form1.serialPort.Close();
//             Form1.serialPort.Open();
            
//             Form1.serialPort.WriteLine(command);
//             CreateTextFileWithHeader();
//             this.infoLabel.Text = "Current file: " + newFileName;
//             serialPort.DataReceived += DataReceivedHandler;
//         }

//         private void ActionButton3_Click(object sender, EventArgs e)
//         {
//             command = "6969";
//             Form1.serialPort.WriteLine(command);
//             this.actionButton1.Enabled = true;
//             this.actionButton2.Enabled = true;
//             this.actionButton3.Enabled = false;
//             //CloseFile();
//             this.infoLabel.Text = "Select an action above to proceed.";
//         }

//  private void CreateTextFileWithHeader()
//         {
//             try
//             {
//                 string fileName2 = GetNextFileName(); // Get a unique file name
//                 newFileName = GetNextFileName();
//                 string filePath = Path.Combine(folderName, fileName2); // Combine folder path and file name
//                 StartNewFile(filePath);
//                 if (writer != null)
//                 {
//                     try
//                     {
//                         writer.WriteLine("TriggerCue TrialNumber Amber red green Press"); // Write data to file
//                     }
//                     catch (Exception ex)
//                     {
//                         this.Invoke((MethodInvoker)delegate
//                         {
//                             infoLabel.Text += $"\nFile Error: {ex.Message}";
//                         });
//                     }
//                 }
//             }
//             catch (Exception ex)
//             {
//                 MessageBox.Show($"Error creating file: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
//             }
//         }

//         private string GetNextFileName()
//         {
//             int count = 1;
//             // Check for the next available file name
//             do
//             {
//                 newFileName = $"{fileName}_R{count}.txt"; // For example: baseFileNameRx1.txt
//                 count++;
//             } while (File.Exists(Path.Combine(folderName, newFileName))); // Check if the file already exists
            
//             currentFileName = Path.Combine(folderName, newFileName);
//             return newFileName; // Return the unique file name
//         }
//         private void DataReceivedHandler(object sender, RJCP.IO.Ports.SerialDataReceivedEventArgs e)
//                 {
//                     try
//                     {
//                         string data = serialPort.ReadLine(); // Read data from the serial port
//                         if (data.Contains('@'))
//                         {
//                         // Split the data using '@' as the delimiter
//                         string[] frames = data.Split(new[] { '@' }, StringSplitOptions.RemoveEmptyEntries);
        
//                         // Prepare a string to hold the combined data
//                         string combinedData = string.Join(" ", frames.Select(frame => frame.Trim()));

//                         SaveDataToFile(combinedData);
//                         }
//                     }
//                     catch (Exception ex)
//                     {
//                         // Handle any errors in reading the data
//                         this.Invoke((MethodInvoker)delegate
//                         {
//                             infoLabel.Text += $"\nError: {ex.Message}"; // Display error in the label
//                         });
//                     }
//                 }
                
//           private void SaveDataToFile(string data)
//             {
//                 if (writer != null)
//                 {
//                     try
//                     {
//                         writer.WriteLine(data); // Write data to file
//                         //writer.Flush(); // Ensure data is written to the file immediately

//                     }
//                     catch (Exception ex)
//                     {
//                         this.Invoke((MethodInvoker)delegate
//                         {
//                             infoLabel.Text += $"\nFile Error: {ex.Message}";
//                         });
//                     }
//                 }
//             }
//             private void StartNewFile(string fileName)
//         {
//             CloseFile();  // Ensure any previously open file is closed
//             // Initialize the writer with the new file name
//             writer = new StreamWriter(new FileStream(fileName, FileMode.Create, FileAccess.Write)); 

//         }

//         private void CloseFile()
//             {
//                 if (writer != null)
//                 {
//                     writer.Flush();
//                     writer.Close(); // Close the file
//                     writer = null;  // Set writer to null to ensure it can be re-initialized if needed
//                 }
//             }
//     }
// }
using System;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using RJCP.IO.Ports;

namespace GUImetamers
{
    public partial class screen3RandBeh : Form
    {
        private Screen2 previousScreen; // Store a reference to the previous screen
        private string expType = "";
        private string subID = "";
        private string fileName = "";
        private int expFlag = 0;
        private string command = "";
        private string folderName;
        private string newFileName;

        private string currentFileName;
        private StreamWriter? writer; // Class-level StreamWriter for the data file
        private SerialPortStream serialPort;
        
        public screen3RandBeh(Screen2 screen2, int expMode, string subjectID, string Folder, SerialPortStream port)
        {
            subID = subjectID;
            expFlag = expMode;
            folderName = Folder;
            InitializeComponent();
            serialPort = port;
            previousScreen = screen2; // Initialize the previous screen reference

            switch (expMode)
            {
                case 1:
                    expType = "BehRandWalk";
                    this.labelHeader.Text = "Random Behavioral Experiment";
                    //expFlag = 2;
                break;
                case 2:
                    expType = "VarTimPots";
                    this.labelHeader.Text = "Var. Pots Experiment";
                    //expFlag = 1;
                break;
                default:
                break;
            }
        }

        private void ActionButton1_Click(object sender, EventArgs e)
        {
            CloseFile();
            this.Hide();
            previousScreen.Show();
        }

        private void ActionButton2_Click(object sender, EventArgs e)
        {
            ConfigureAction("", expFlag == 1 ? "2789" : "1789");
            this.actionButton1.Enabled = false;
            this.actionButton3.Enabled = true;
            this.actionButton2.Enabled = false;
        }

        private void ActionButton3_Click(object sender, EventArgs e)
        {
            StopDataCollection();
            this.actionButton1.Enabled = true;
            this.actionButton2.Enabled = true;
            this.actionButton3.Enabled = false;
        }


        private void ConfigureAction(string actionSuffix, string commandCode)
        {
            ToggleButtons(false);
            fileName = $"{subID}_{expType}_{actionSuffix}";
            command = commandCode;
            Form1.serialPort.WriteLine(command);
            CreateTextFileWithHeader();
            this.infoLabel.Text = "Current file: " + newFileName;
            serialPort.DataReceived += DataReceivedHandler;
        }

        private void ToggleButtons(bool enable)
        {
            this.actionButton1.Enabled = enable;
            this.actionButton3.Enabled = enable;
            this.actionButton2.Enabled = enable;
        }

        private void StopDataCollection()
        {
            ToggleButtons(true);
            this.infoLabel.Text = "Select an action above to proceed.";
            Form1.serialPort.WriteLine("6969");
            serialPort.DataReceived -= DataReceivedHandler; // Unsubscribe from event to prevent further data capture
            CloseFile();
        }

        private void CreateTextFileWithHeader()
        {
            try
            {
                newFileName = GetNextFileName();
                string filePath = Path.Combine(folderName, newFileName);
                StartNewFile(filePath);

                if (writer != null)
                {
                    try
                    {
                        writer.WriteLine("TriggerCue TrialNumber Amber red green Press");
                    }
                    catch (Exception ex)
                    {
                        DisplayError("File Error: " + ex.Message);
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error creating file: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private string GetNextFileName()
        {
            int count = 1;
            do
            {
                newFileName = $"{fileName}_R{count}.txt";
                count++;
            } while (File.Exists(Path.Combine(folderName, newFileName)));
            currentFileName = Path.Combine(folderName, newFileName);
            return newFileName;
        }

        private void DataReceivedHandler(object sender, SerialDataReceivedEventArgs e)
        {
            try
            {
                while (serialPort.BytesToRead > 0)
                {
                    string data = serialPort.ReadLine();
                    if (data.Contains('@'))
                    {
                        string[] frames = data.Split(new[] { '@' }, StringSplitOptions.RemoveEmptyEntries);
                        string combinedData = string.Join(" ", frames.Select(frame => frame.Trim()));
                        SaveDataToFile(combinedData);
                    }
                }
            }
            catch (Exception ex)
            {
                DisplayError("Error: " + ex.Message);
            }
        }

        private void SaveDataToFile(string data)
        {
            if (writer != null)
            {
                try
                {
                    writer.WriteLine(data);
                    writer.Flush();
                }
                catch (Exception ex)
                {
                    DisplayError("File Error: " + ex.Message);
                }
            }
        }

        private void StartNewFile(string fileName)
        {
            CloseFile();
            writer = new StreamWriter(new FileStream(fileName, FileMode.Create, FileAccess.Write));
        }

        private void CloseFile()
        {
            if (writer != null)
            {
                writer.Flush();
                writer.Close();
                writer = null;
            }
        }

        private void DisplayError(string message)
        {
            this.Invoke((MethodInvoker)delegate
            {
                infoLabel.Text += "\n" + message;
            });
        }
    }
}
