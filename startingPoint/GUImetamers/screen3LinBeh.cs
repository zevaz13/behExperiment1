
using System;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using RJCP.IO.Ports;

namespace GUImetamers
{
    public partial class screen3LinBeh : Form
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
        
        public screen3LinBeh(Screen2 screen2, int expMode, string subjectID, string Folder, SerialPortStream port)
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
                    expType = "LinBeh";
                    this.labelHeader.Text = "Linear Behavioral Experiment";
                    break;
                case 2:
                    expType = "LinEEG";
                    this.labelHeader.Text = "Linear EEG Experiment";
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
            ConfigureAction("R2G", expFlag == 1 ? "5789" : "3789");
        }

        private void ActionButton3_Click(object sender, EventArgs e)
        {
            ConfigureAction("G2R", expFlag == 1 ? "6789" : "4789");
        }

        private void ActionButton4_Click(object sender, EventArgs e)
        {
            StopDataCollection();
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
            this.actionButton4.Enabled = !enable;
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
