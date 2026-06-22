
using System;
using System.Windows.Forms;
using System.IO;
using RJCP.IO.Ports;

namespace GUImetamers
{
    public partial class Form1 : Form
    {
        private Label? comPortLabel;
        private TextBox? textBox;
        private TextBox? comPortTextBox;
        private Button? connectButton;
        public static SerialPortStream serialPort;

        public Form1()
        {
            InitializeComponent();
            InitializeCustomComponents();

            serialPort = new SerialPortStream();
            this.Size = new Size(250, 300); // Adjusted for better UI
        }

        private void InitializeCustomComponents()
        {
            comPortLabel = new Label();
            comPortLabel.Text = "Enter COM Port:";
            comPortLabel.Location = new System.Drawing.Point(10, 10);
            comPortLabel.Size = new System.Drawing.Size(85, 22);
            this.Controls.Add(comPortLabel);

            comPortTextBox = new TextBox();
            comPortTextBox.Location = new System.Drawing.Point(100, 10);
            comPortTextBox.Size = new System.Drawing.Size(100, 22); // Adjusted height
            this.Controls.Add(comPortTextBox);

            textBox = new TextBox();
            textBox.Multiline = true;
            textBox.Size = new System.Drawing.Size(200, 100); // Adjusted size for more text
            textBox.Location = new System.Drawing.Point(10, 100);
            this.Controls.Add(textBox);

            connectButton = new Button();
            connectButton.Text = "Connect";
            connectButton.Location = new System.Drawing.Point(10, 50);
            connectButton.Size = new System.Drawing.Size(200, 50);
            connectButton.Click += new EventHandler(connectButton_Click);
            this.Controls.Add(connectButton);

            this.Text = "Serial Port Connection";
            this.ClientSize = new System.Drawing.Size(250, 220);
        }

        private void connectButton_Click(object sender, EventArgs e)
        {
            string portName = comPortTextBox.Text.Trim();
            if (string.IsNullOrEmpty(portName))
            {
                textBox.AppendText("Please enter a valid port name\n");
                return;
            }

            // Initialize and configure the SerialPortStream
            serialPort = new SerialPortStream
            {
                PortName = portName,
                BaudRate = 38400
                //Parity = Parity.None,
                //DataBits = 8,
                //StopBits = StopBits.One,
                //ReadTimeout = -1,
                //WriteTimeout = -1
            };

            try
            {
                serialPort.Open();
                // serialPort.DataReceived += DataReceivedHandler; // Attach the event handler
                textBox.AppendText($"Connected to {portName}\n");

                // Adding a small delay to ensure the Teensy is ready
                System.Threading.Thread.Sleep(100);
                Screen2 screen2 = new Screen2(serialPort); // Create an instance of Screen2
                this.Hide(); // Hide the current form
                screen2.Show(); // Show Screen2
            }
            catch (Exception ex)
            {
                textBox.AppendText($"Error opening port: {ex.Message}\n");
            }
        }

        // private void DataReceivedHandler(object sender, SerialDataReceivedEventArgs e)
        // {
        //     try
        //     {
        //         string data = serialPort.ReadLine(); // or ReadExisting() based on your need

        //         // Update UI on the main thread
        //         this.Invoke((MethodInvoker)delegate
        //         {
        //             textBox.AppendText($"Data Received: {data}\n"); // Display received data in the TextBox
        //         });
        //     }
        //     catch (Exception ex)
        //     {
        //         // Handle any errors in reading the data
        //         this.Invoke((MethodInvoker)delegate
        //         {
        //             textBox.AppendText($"Error reading data: {ex.Message}\n");
        //         });
        //     }
        // }
    }
}
