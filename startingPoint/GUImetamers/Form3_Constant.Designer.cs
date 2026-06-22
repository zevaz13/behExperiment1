namespace GUImetamers
{
    partial class Form3_Constant
    {
        // Required designer variable.
        private System.ComponentModel.IContainer components = null;

        private System.Windows.Forms.TextBox redValTextBox;
        private System.Windows.Forms.TextBox greenValTextBox;
        private System.Windows.Forms.Button backButton;
        private System.Windows.Forms.Button stopButton;
        private System.Windows.Forms.Button sendCommandButton;
        private System.Windows.Forms.Label redValLabel;
        private System.Windows.Forms.Label greenValLabel;

        /// <summary>
        ///  Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.redValTextBox = new System.Windows.Forms.TextBox();
            this.greenValTextBox = new System.Windows.Forms.TextBox();
            this.backButton = new System.Windows.Forms.Button();
            this.stopButton = new System.Windows.Forms.Button();
            this.sendCommandButton = new System.Windows.Forms.Button();
            this.redValLabel = new System.Windows.Forms.Label();
            this.greenValLabel = new System.Windows.Forms.Label();

            // 
            // redValLabel
            // 
            this.redValLabel.AutoSize = true;
            this.redValLabel.Location = new System.Drawing.Point(20, 20);
            this.redValLabel.Name = "redValLabel";
            this.redValLabel.Size = new System.Drawing.Size(55, 15);
            this.redValLabel.Text = "Red Value:";
            // 
            // redValTextBox
            // 
            this.redValTextBox.Location = new System.Drawing.Point(100, 20);
            this.redValTextBox.Name = "redValTextBox";
            this.redValTextBox.Size = new System.Drawing.Size(100, 23);
            // 
            // greenValLabel
            // 
            this.greenValLabel.AutoSize = true;
            this.greenValLabel.Location = new System.Drawing.Point(20, 60);
            this.greenValLabel.Name = "greenValLabel";
            this.greenValLabel.Size = new System.Drawing.Size(66, 15);
            this.greenValLabel.Text = "Green Value:";
            // 
            // greenValTextBox
            // 
            this.greenValTextBox.Location = new System.Drawing.Point(100, 60);
            this.greenValTextBox.Name = "greenValTextBox";
            this.greenValTextBox.Size = new System.Drawing.Size(100, 23);
            // 
            // backButton
            // 
            this.backButton.Location = new System.Drawing.Point(20, 100);
            this.backButton.Name = "backButton";
            this.backButton.Size = new System.Drawing.Size(75, 23);
            this.backButton.Text = "Back";
            this.backButton.Click += new System.EventHandler(this.BackButton_Click);
            CO
            // 
            // stopButton
            // 
            this.stopButton.Location = new System.Drawing.Point(100, 100);
            this.stopButton.Name = "stopButton";
            this.stopButton.Size = new System.Drawing.Size(75, 23);
            this.stopButton.Text = "Stop";
            this.stopButton.Click += new System.EventHandler(this.StopButton_Click);
            // 
            // sendCommandButton
            // 
            this.sendCommandButton.Location = new System.Drawing.Point(180, 100);
            this.sendCommandButton.Name = "sendCommandButton";
            this.sendCommandButton.Size = new System.Drawing.Size(100, 23);
            this.sendCommandButton.Text = "Send Command";
            this.sendCommandButton.Click += new System.EventHandler(this.SendCommandButton_Click);
            // 
            // Form3_Constant
            // 
            this.ClientSize = new System.Drawing.Size(300, 150);
            this.Controls.Add(this.redValTextBox);
            this.Controls.Add(this.greenValTextBox);
            this.Controls.Add(this.backButton);
            this.Controls.Add(this.stopButton);
            this.Controls.Add(this.sendCommandButton);
            this.Controls.Add(this.redValLabel);
            this.Controls.Add(this.greenValLabel);
            this.Text = "Form3 Constant";
        }

        #endregion
    }
}