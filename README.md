
<img height="700" src="https://github.com/c0le/INetSimAnalyzer/blob/master/INetSimAnalyzerGui.png" />

## Synopsis

INetSimAnalyzer is a software tool to ease the analyzation of INetSim log files and reports and provides
a function to send alarms to another INetSimAnalyzer instance. It allows to filter log files by service,
time, or keywords.

## Motivation

In the context of a student research project, the software INetSim was used as a honeypot and the created 
log files should be analyzed. It turned out that it´s very difficult to find special entries in big log 
files and that´s why INetSimAnalyzers was developed.

## Installation

System requirements:
	-INetSimViewer (Not mandatory if you just want to analyse existing logs or run the software in watch mode)
	-Python 3
	-PyQt5

## Start
If you want to control INetSim with INetSimAnalyzer you have to start the software with admin rights

## Command Line options
	-s  or  --start		INetSimAnalyzer starts INetSim at startup
	-h  or  --host		Alarm message target ip address (Default: 127.0.0.1)
	-p  or  --port		Alarm message target port (Default: 46000)
	-d  or  --dark		Disable Dark Theme
	
## Watch Mode
The WatchMode helps the administrator to monitor a system running InetSimAnalyzer and INetSim. The admin starts 
the INetSimViwer first on his system and activates WatchMode. Then he starts the INetSimAnalyzer instance on the 
system to monitor with the IP of the administrator pc as parameter. Now every new entry in the Service.log file 
will be send as an alarm to the admins instance.	

## License

A short snippet describing the license (MIT, Apache, etc.)