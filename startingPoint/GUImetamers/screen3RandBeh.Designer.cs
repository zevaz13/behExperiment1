using System.Windows.Forms;

namespace GUImetamers
{
    partial class screen3RandBeh
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
            this.labelHeader = new System.Windows.Forms.Label();
            this.actionButton1 = new System.Windows.Forms.Button();
            this.actionButton2 = new System.Windows.Forms.Button();
            this.actionButton3 = new System.Windows.Forms.Button();
            this.infoLabel = new System.Windows.Forms.Label();
            this.SuspendLayout();

            // 
            // labelHeader
            // 
            this.labelHeader.AutoSize = true;
            this.labelHeader.Font = new System.Drawing.Font("Arial", 14F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point);
            this.labelHeader.Location = new System.Drawing.Point(30, 20);
            this.labelHeader.Name = "labelHeader";
            this.labelHeader.Size = new System.Drawing.Size(85, 22);
            this.labelHeader.TabIndex = 0;
            this.labelHeader.Text = "Screen 3";

            // 
            // actionButton1
            // 
            this.actionButton1.Location = new System.Drawing.Point(30, 60);
            this.actionButton1.Name = "actionButton1";
            this.actionButton1.Size = new System.Drawing.Size(100, 30);
            this.actionButton1.TabIndex = 1;
            this.actionButton1.Text = "Back";
            this.actionButton1.UseVisualStyleBackColor = true;
            this.actionButton1.Click += new System.EventHandler(this.ActionButton1_Click);

            // 
            // actionButton2
            // 
            this.actionButton2.Location = new System.Drawing.Point(150, 60);
            this.actionButton2.Name = "actionButton2";
            this.actionButton2.Size = new System.Drawing.Size(100, 30);
            this.actionButton2.TabIndex = 2;
            this.actionButton2.Text = "Start";
            this.actionButton2.UseVisualStyleBackColor = true;
            this.actionButton2.Click += new System.EventHandler(this.ActionButton2_Click);

            // 
            // actionButton3
            // 
            this.actionButton3.Location = new System.Drawing.Point(270, 60);
            this.actionButton3.Name = "actionButton3";
            this.actionButton3.Size = new System.Drawing.Size(100, 30);
            this.actionButton3.TabIndex = 3;
            this.actionButton3.Text = "Stop";
            this.actionButton3.UseVisualStyleBackColor = true;
            this.actionButton3.Enabled = false;
            this.actionButton3.Click += new System.EventHandler(this.ActionButton3_Click);

            // 
            // infoLabel
            // 
            this.infoLabel.AutoSize = true;
            this.infoLabel.Location = new System.Drawing.Point(30, 110);
            this.infoLabel.Name = "infoLabel";
            this.infoLabel.Size = new System.Drawing.Size(200, 15);
            this.infoLabel.TabIndex = 4;
            this.infoLabel.Text = "Select an action above to proceed.";

            // 
            // Screen3
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(400, 160);
            this.Controls.Add(this.labelHeader);
            this.Controls.Add(this.actionButton1);
            this.Controls.Add(this.actionButton2);
            this.Controls.Add(this.actionButton3);
            
            this.Controls.Add(this.infoLabel);
            this.Name = "Screen3";
            this.Text = "Screen 3";
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        private System.Windows.Forms.Label labelHeader;
        private System.Windows.Forms.Button actionButton1;
        private System.Windows.Forms.Button actionButton2;
        private System.Windows.Forms.Button actionButton3;
        
        private System.Windows.Forms.Label infoLabel;
    }
}
