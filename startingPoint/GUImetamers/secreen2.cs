using System;
using System.Windows.Forms;
using RJCP.IO.Ports; // Ensure you have the correct namespace for SerialPortStream

namespace GUImetamers
{
    public partial class Screen2 : Form
    {
        public string SubID;
        public string folderName = "";

        private SerialPortStream serialPort;
        public Screen2(SerialPortStream port)
        {
            InitializeComponent();
            serialPort = port;
        }

        private void SetButton_Click(object sender, EventArgs e)
        {
            // Validate folder and subject ID, then enable experiment buttons
            
            if (!string.IsNullOrWhiteSpace(folderTextBox.Text) && !string.IsNullOrWhiteSpace(subjectIDTextBox.Text))
            {
                exp1Button.Enabled = true;
                exp2Button.Enabled = true;
                exp3Button.Enabled = true;
                exp4Button.Enabled = true;
                exp5Button.Enabled = true;
                SubID = subjectIDTextBox.Text;
            }
            else
            {
                MessageBox.Show("Please fill in both folder and subject ID.");
            }
        }

        private void setFolder_Click(object sender, EventArgs e){
        using (FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog())
            {
                // Show the folder browser dialog and check if the user selected a folder
                if (folderBrowserDialog.ShowDialog() == DialogResult.OK)
                {
                    // Set the selected folder path in the folderTextBox
                    folderTextBox.Text = folderBrowserDialog.SelectedPath;
                    folderName = folderTextBox.Text;
                }
            }
        }
        private void Exp1Button_Click(object sender, EventArgs e)
        { 
            // Behavioral Experiment Random. Needs 3 buttons
                screen3RandBeh screen3RandBeh = new screen3RandBeh(this,1,SubID,folderName,serialPort); // Create an instance of Screen2
                //this.Hide(); // Hide the current form
                screen3RandBeh.Show(); // Show Screen3
        }

        private void exp2Button_Click(object sender, EventArgs e)
        { 
            // Behavioral Experiment Linear. Needs 4 buttons
                screen3LinBeh screen3LinBeh = new screen3LinBeh(this,1,SubID,folderName,serialPort); // Create an instance of Screen2
                //this.Hide(); // Hide the current form
                screen3LinBeh.Show(); // Show Screen3
        }

        private void exp3Button_Click(object sender, EventArgs e)
        { 
            // EEG experiment Linear. needs 4 buttons
                screen3LinBeh screen3LinBeh = new screen3LinBeh(this,2,SubID,folderName,serialPort); // Create an instance of Screen2
                screen3LinBeh.Show(); // Show Screen3
        }

        private void exp4Button_Click(object sender, EventArgs e)
        { 
            // Behavioral experiment variable pots. needs 3 buttons
                screen3RandBeh screen3RandBeh = new screen3RandBeh(this,2,SubID,folderName,serialPort); // Create an instance of Screen2
                this.Hide(); // Hide the current form
                screen3RandBeh.Show(); // Show Screen3
        }

        private void exp5Button_Click(object sender, EventArgs e)
        { 
            // Behavioral experiment variable pots. needs 3 buttons
                Form3_Constant Form3_Constant = new Form3_Constant(this,serialPort); // Create an instance of Screen2
                Form1.serialPort.WriteLine("7789");
                this.Hide(); // Hide the current form
                Form3_Constant.Show(); // Show Screen3
        }
    }
}
