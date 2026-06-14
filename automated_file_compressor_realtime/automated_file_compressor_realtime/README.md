# Real-Time Automated File Compression System
### OS Project – Python Implementation

## Description
This upgraded version automatically tracks real file access (open/edit) in `monitored_folder/` using `watchdog`.  
It compresses infrequently accessed files in real-time using Zlib compression.

## Features
- Monitors folder in real-time for file modifications/accesses
- Tracks access frequency automatically
- Compresses files accessed less than 3 times
- Decompresses automatically when needed
- Background automation every 10 seconds
- Simple console output

## How to Run
1. Install Python (>=3.8) and watchdog:
   ```bash
   pip install watchdog
   ```
2. Extract the ZIP
3. Open terminal in the folder
4. Run:
   ```bash
   python main.py
   ```
5. Open/edit files in `monitored_folder/` to trigger access detection

## Author
Gautam Chand
