using System.Windows.Forms;

namespace GUImetamers
{
    partial class Screen2
    {
        private System.ComponentModel.IContainer components = null;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.labelFolder        = new System.Windows.Forms.Label();
            this.subjectIDTextBox   = new System.Windows.Forms.TextBox();
            this.labelSubjectID     = new System.Windows.Forms.Label();
            this.folderTextBox      = new System.Windows.Forms.TextBox();
            this.setButton          = new System.Windows.Forms.Button();
            this.setFolder          = new System.Windows.Forms.Button();
            this.exp1Button         = new System.Windows.Forms.Button();
            this.exp2Button         = new System.Windows.Forms.Button();
            this.exp3Button         = new System.Windows.Forms.Button();
            this.exp4Button         = new System.Windows.Forms.Button();
            this.exp5Button         = new System.Windows.Forms.Button();

            this.SuspendLayout();

            // 
            // labelFolder
            // 
            this.labelFolder.AutoSize = true;
            this.labelFolder.Location = new System.Drawing.Point(30, 20);
            this.labelFolder.Name = "labelFolder";
            this.labelFolder.Size = new System.Drawing.Size(42, 15);
            this.labelFolder.TabIndex = 0;
            this.labelFolder.Text = "Folder:"; 
            
            // subjectIDTextBox
            this.subjectIDTextBox.Location = new System.Drawing.Point(100, 60);
            this.subjectIDTextBox.Name = "subjectIDTextBox";
            this.subjectIDTextBox.Size = new System.Drawing.Size(200, 20); // Increased width
            this.subjectIDTextBox.TabIndex = 0;

            // 
            // labelSubjectID
            // 
            this.labelSubjectID.AutoSize = true;
            this.labelSubjectID.Location = new System.Drawing.Point(30, 60);
            this.labelSubjectID.Name = "labelSubjectID";
            this.labelSubjectID.Size = new System.Drawing.Size(66, 15);
            this.labelSubjectID.TabIndex = 2;
            this.labelSubjectID.Text = "Subject ID:";

            // folderTextBox
            this.folderTextBox.Location = new System.Drawing.Point(100, 20);
            this.folderTextBox.Name = "folderTextBox";
            this.folderTextBox.Size = new System.Drawing.Size(200, 20); // Increased width
            this.folderTextBox.TabIndex = 1;

            // setButton
            this.setButton.Location = new System.Drawing.Point(310, 20);
            this.setButton.Name = "setButton";
            this.setButton.Size = new System.Drawing.Size(100, 60); // Increased size
            this.setButton.TabIndex = 2;
            this.setButton.Text = "Set ID";
            this.setButton.UseVisualStyleBackColor = true;
            this.setButton.Click += new System.EventHandler(this.SetButton_Click);

            // setButton folder
            this.setFolder.Location = new System.Drawing.Point(420, 20);
            this.setFolder.Name = "setFolder";
            this.setFolder.Size = new System.Drawing.Size(100, 60); // Increased size
            this.setFolder.TabIndex = 2;
            this.setFolder.Text = "Set Folder";
            this.setFolder.UseVisualStyleBackColor = true;
            this.setFolder.Click += new System.EventHandler(this.setFolder_Click);

            // Experiment Buttons
            this.exp1Button.Location = new System.Drawing.Point(30, 100);
            this.exp1Button.Name = "exp1Button";
            this.exp1Button.Size = new System.Drawing.Size(115, 30); // Increased size
            this.exp1Button.TabIndex = 3;
            this.exp1Button.Text = "Beh Random";
            this.exp1Button.UseVisualStyleBackColor = true;
            this.exp1Button.Enabled = false; // Initially disabled
            this.exp1Button.Click += new System.EventHandler(this.Exp1Button_Click); // Link the event handler

            this.exp2Button.Location = new System.Drawing.Point(150, 100);
            this.exp2Button.Name = "exp2Button";
            this.exp2Button.Size = new System.Drawing.Size(115, 30); // Increased size
            this.exp2Button.TabIndex = 4;
            this.exp2Button.Text = "Beh Linear";
            this.exp2Button.UseVisualStyleBackColor = true;
            this.exp2Button.Enabled = false; // Initially disabled
            this.exp2Button.Click += new System.EventHandler(this.exp2Button_Click); // Link the event handler

            this.exp3Button.Location = new System.Drawing.Point(270, 100);
            this.exp3Button.Name = "exp3Button";
            this.exp3Button.Size = new System.Drawing.Size(115, 30); // Increased size
            this.exp3Button.TabIndex = 5;
            this.exp3Button.Text = "EEG linear";
            this.exp3Button.UseVisualStyleBackColor = true;
            this.exp3Button.Enabled = false; // Initially disabled
            this.exp3Button.Click += new System.EventHandler(this.exp3Button_Click); // Link the event handler

            this.exp4Button.Location = new System.Drawing.Point(390, 100);
            this.exp4Button.Name = "exp4Button";
            this.exp4Button.Size = new System.Drawing.Size(115, 30); // Increased size
            this.exp4Button.TabIndex = 6;
            this.exp4Button.Text = "Beh Variable";
            this.exp4Button.UseVisualStyleBackColor = true;
            this.exp4Button.Enabled = false; // Initially disabled
            this.exp4Button.Click += new System.EventHandler(this.exp4Button_Click); // Link the event handler
    
            this.exp5Button.Location = new System.Drawing.Point(510, 100);
            this.exp5Button.Name = "exp5Button";
            this.exp5Button.Size = new System.Drawing.Size(115, 30); // Increased size
            this.exp5Button.TabIndex = 6;
            this.exp5Button.Text = "Constant";
            this.exp5Button.UseVisualStyleBackColor = true;
            this.exp5Button.Enabled = false; // Initially disabled
            this.exp5Button.Click += new System.EventHandler(this.exp5Button_Click); // Link the event handler

            // Screen2
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(650, 140); // Increased form size
            this.Controls.Add(this.subjectIDTextBox);
            this.Controls.Add(this.folderTextBox);
            this.Controls.Add(this.setButton);
            this.Controls.Add(this.setFolder);
            this.Controls.Add(this.exp1Button);
            this.Controls.Add(this.exp2Button);
            this.Controls.Add(this.exp3Button);
            this.Controls.Add(this.exp4Button);
            this.Controls.Add(this.exp5Button);
            this.Controls.Add(this.labelFolder);
            this.Controls.Add(this.labelSubjectID);
            this.Name = "Screen2";
            this.Text = "Screen 2";
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        private System.Windows.Forms.TextBox subjectIDTextBox;
        private System.Windows.Forms.TextBox folderTextBox;
        private System.Windows.Forms.Button setButton;
        private System.Windows.Forms.Button setFolder;
        private System.Windows.Forms.Button exp1Button;
        private System.Windows.Forms.Button exp2Button;
        private System.Windows.Forms.Button exp3Button;
        private System.Windows.Forms.Button exp4Button;
        private System.Windows.Forms.Button exp5Button;
        private System.Windows.Forms.Label labelFolder;
        private System.Windows.Forms.Label labelSubjectID;
    }
}
