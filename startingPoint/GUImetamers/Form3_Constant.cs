using System;
using System.Windows.Forms;
using RJCP.IO.Ports;

namespace GUImetamers
{
    public partial class Form3_Constant : Form
    {
        private SerialPortStream serialPort;
                
        private Screen2 previousScreen; // Store a reference to the previous screen

        public Form3_Constant(Screen2 screen2,SerialPortStream port)
        {
            InitializeComponent();
            serialPort = port;
            previousScreen = screen2; // Initialize the previous screen reference
            this.backButton.Enabled = false;
        }

        // Event handler for Back button
        private void BackButton_Click(object sender, EventArgs e)
        {
            // Code to navigate back to the previous screen
            this.Hide();
            previousScreen.Show();
        }

        // Event handler for Stop button
        private void StopButton_Click(object sender, EventArgs e)
        {
            Form1.serialPort.WriteLine("6969");
            this.backButton.Enabled = true;
            this.sendCommandButton.Enabled = false;
            
        }

        // Event handler for Send Command button
        private void SendCommandButton_Click(object sender, EventArgs e)
        {
            
            string redVal = redValTextBox.Text;
            string greenVal = greenValTextBox.Text;
            string command = $"{redVal}@{greenVal}";
            Form1.serialPort.WriteLine(command);
            // Send the command to the device or handle it as needed
        }
    }
}
