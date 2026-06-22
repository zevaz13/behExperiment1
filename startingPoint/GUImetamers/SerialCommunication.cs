using System;
using System.IO.Ports;

public class SerialCommunication
{
    private SerialPort _serialPort;

    public string COMPort { get; set; }
    public int BaudRate { get; private set; } = 38400;

    public SerialCommunication(string comPort)
    {
        COMPort = comPort;
        _serialPort = new SerialPort(COMPort, BaudRate);
    }

    public void OpenConnection()
    {
        if (!_serialPort.IsOpen)
        {
            _serialPort.Open();
        }
    }

    public void CloseConnection()
    {
        if (_serialPort.IsOpen)
        {
            _serialPort.Close();
        }
    }

    public void SendCommand(string command)
    {
        if (_serialPort.IsOpen)
        {
            _serialPort.WriteLine(command);
        }
    }
}
