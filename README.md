<div align="center">

# 🏃‍♂️ Smart Multi-Stage Fitness Test System

### *Award-Winning Sports Science Innovation*

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MQTT](https://img.shields.io/badge/MQTT-Enabled-orange.svg)](https://mqtt.org/)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()

**🏆 2nd Place Winner** - Sport Science Innovation Competition  
*Department of Physical Education, Thailand*

---

![Award Badge](https://img.shields.io/badge/Award-Runner--Up-gold?style=for-the-badge)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Demo Video](#-demo-video)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Components](#-components)
- [Awards & Recognition](#-awards--recognition)
- [Technology Stack](#-technology-stack)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

The **Smart Multi-Stage Fitness Test System** is a comprehensive, IoT-based solution designed for accurate and automated fitness testing in sports science applications. This system enables real-time monitoring, data collection, and analysis of athlete performance through multiple testing protocols including RAST (Running Anaerobic Sprint Test), multi-stage timing gates, and heart rate variability monitoring.

### Key Highlights

- ⚡ **Real-time Performance Tracking** - Instant timing and data collection
- 📊 **Comprehensive Analytics** - Detailed performance metrics and visualizations
- 🔌 **Wireless Sensor Network** - MQTT-based IoT architecture
- 👥 **Multi-Athlete Support** - Individual and team testing modes
- 📈 **Data Export** - JSON, CSV, and PDF report generation
- 💓 **HRV Monitoring** - Heart rate variability analysis with Polar H10

---

## 🎥 Demo Video

<div align="center">

### 📺 Watch the System in Action

[![Smart Multi-Stage Fitness Test System Demo](https://img.youtube.com/vi/a3_Rm-xb4SM/0.jpg)](https://www.youtube.com/watch?v=a3_Rm-xb4SM&t=8s)

**Click the image above to watch the demonstration video**

*This video showcases the system's features, setup process, and real-world usage scenarios.*

</div>

---

## ✨ Features

### 🏃 Running Anaerobic Sprint Test (RAST)
- Automated 6-sprint protocol with configurable recovery periods
- Real-time sprint timing with millisecond precision
- Automatic calculation of power, fatigue index, and performance metrics
- Support for multiple sensor configurations (A/B, C/D, etc.)
- Historical results viewing and comparison

### ⏱️ Multi-Stage Timing Gates
- Configurable timing gates (up to 10 sensors: A-J)
- Single, dual, and multi-sensor split timing modes
- Customizable distance settings between gates
- Team testing mode with sequential athlete tracking
- Real-time timer display with visual feedback

### 💓 Heart Rate Variability (HRV) Monitoring
- Bluetooth Low Energy (BLE) integration with Polar H10
- Real-time ECG-like RRi visualization
- HRV metrics calculation (RMSSD, SDNN, pNN50, LF/HF ratio)
- Frequency domain analysis with FFT
- Performance interpretation and recommendations

### 📊 Data Management
- Athlete database with profile management
- Team creation and management
- Results storage in JSON format
- Export to CSV for spreadsheet analysis
- PDF report generation with charts and statistics

### 🎨 User Interface
- Modern Tkinter-based GUI
- Full-screen display mode
- Large, readable timer displays
- Color-coded performance indicators
- Intuitive menu system

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │  RAST    │  │  Gates   │  │   HRV    │  │ Results ││
│  │  Tests   │  │  Timing  │  │ Monitor  │  │ Manager ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
└─────────────────────────────────────────────────────────┘
                        ↕ MQTT Protocol
┌─────────────────────────────────────────────────────────┐
│                    Communication Layer                   │
│              MQTT Broker (Mosquitto)                     │
│                 192.168.100.189:1883                    │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                      Sensor Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │  Gate A  │  │  Gate B  │  │  Gate C  │  │   ...   ││
│  │ (Arduino)│  │ (Arduino)│  │ (Arduino)│  │         ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Polar H10 Heart Rate Monitor (BLE)         │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- Python 3.7 or higher
- Windows 10/11 (or compatible OS)
- MQTT Broker (Mosquitto)
- Arduino-compatible sensors (for timing gates)
- Polar H10 heart rate monitor (optional, for HRV features)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/SmartMultiStage_FitnessTest_Sys.git
cd SmartMultiStage_FitnessTest_Sys
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `paho-mqtt` - MQTT client library
- `Pillow` - Image processing
- `matplotlib` - Data visualization
- `bleak` - Bluetooth Low Energy support (for HRV)
- `numpy` - Numerical computations
- `scipy` - Signal processing
- `pyttsx3` - Text-to-speech (for beep test)
- `pygame` - Audio playback

### Step 3: Install MQTT Broker

1. Download and install Mosquitto from the `setup/mqtt_broker/` directory
2. Configure the broker IP address in the application settings
3. Default broker IP: `192.168.100.189`

### Step 4: Configure Arduino Sensors

1. Upload the appropriate Arduino sketch to your sensors
2. Available sketches in `firmware/sensors/`:
   - `Player1_Sensor_A_v3/Player1_Sensor_A_v3.ino`
   - `Player1_Sensor_B_v3/Player1_Sensor_B_v3.ino`
   - `Player2_Sensor_C_v3/Player2_Sensor_C_v3.ino`
   - `Player2_Sensor_D_v3.txt/Player2_Sensor_D_v3.txt.ino`

---

## 📖 Usage

### Running RAST Test

```bash
python src/rast_test.py
```

1. Select an athlete from the database
2. Configure MQTT broker IP (if different from default)
3. Connect to MQTT broker
4. Click "Start Test" to begin the 6-sprint protocol
5. Results are automatically saved and can be exported

### Running Multi-Stage Timing Gates

```bash
python src/timing_gate_system.py
```

1. Select athlete or team mode
2. Configure active sensors (A-J)
3. Set running distance
4. Configure split distances (if using multi-sensor mode)
5. Start timing and collect results

### Heart Rate Variability Monitoring

```bash
python src/heart_rate_monitor.py
```

1. Ensure Polar H10 is powered on and nearby
2. Click "Scan" to discover the device
3. Connect and start monitoring
4. View real-time HRV metrics and ECG-like visualization

### Multi-Stage Beep Test

```bash
python src/multi_stage_beep_test.py
```

1. Select multiple athletes (up to 10 players)
2. Configure test parameters
3. Start the beep test protocol
4. Monitor real-time heart rate and performance

---

## 🔧 Project Structure

```
SmartMultiStage_FitnessTest_Sys/
├── src/                          # Main application source code
│   ├── rast_test.py             # RAST (Running Anaerobic Sprint Test)
│   ├── timing_gate_system.py    # Multi-stage timing gate system
│   ├── heart_rate_monitor.py    # HRV monitoring (Polar H10)
│   ├── heart_rate_monitor_v2.py # Alternative HRV interface
│   └── multi_stage_beep_test.py # Multi-stage beep test
│
├── firmware/                     # Arduino sensor firmware
│   └── sensors/                 # Sensor firmware files
│       ├── Player1_Sensor_A_v3/
│       ├── Player1_Sensor_B_v3/
│       ├── Player2_Sensor_C_v3/
│       └── Player2_Sensor_D_v3.txt/
│
├── data/                        # Data storage (JSON files)
│   ├── athletes.json           # Athlete database
│   ├── teams.json              # Team configurations
│   ├── rast_results.json       # RAST test results
│   ├── timing_gate_results.json # Timing gate results
│   └── team_results.json       # Team test results
│
├── assets/                      # Media and resource files
│   ├── images/                 # Image files
│   ├── *.mp3                   # Audio files (beeps, etc.)
│   └── *.jpg, *.png            # Additional images
│
├── awards/                      # Award documentation
│   ├── award.jpg               # Award ceremony photo
│   ├── award1.jpg              # Award recognition photo
│   └── award2.jpg              # Official certificate
│
├── docs/                        # Documentation
│   ├── spec_sheet/             # Specification sheets
│   └── *.pdf, *.doc            # Official documents
│
├── setup/                       # Setup and installation files
│   └── mqtt_broker/            # MQTT broker installation
│
├── README.md                    # This file
└── LICENSE                      # MIT License
```

### Main Applications

| File | Description |
|------|-------------|
| `src/rast_test.py` | RAST test application with full features |
| `src/timing_gate_system.py` | Advanced multi-stage timing gate system |
| `src/heart_rate_monitor.py` | Heart rate variability monitor (Polar H10) |
| `src/heart_rate_monitor_v2.py` | Alternative HRV monitoring interface |
| `src/multi_stage_beep_test.py` | Multi-stage beep test with HR monitoring |

### Data Files

All data files are stored in the `data/` directory:
- `athletes.json` - Athlete database
- `teams.json` - Team configurations
- `rast_results.json` - RAST test results
- `timing_gate_results.json` - Timing gate results
- `team_results.json` - Team test results

### Arduino Firmware

Sensor firmware is located in `firmware/sensors/`:
- Sensor A/B/C/D firmware for timing gates
- MQTT-enabled sensor communication

---

## 🏆 Awards & Recognition

<div align="center">

### 🥈 **2nd Place Winner**
#### Sport Science Innovation Competition
#### Department of Physical Education, Thailand

---

<div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin: 30px 0;">

<div style="flex: 1; min-width: 300px; text-align: center;">
  <h4>🏆 Award Ceremony</h4>
  <img src="awards/award.jpg" alt="Award Ceremony" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
</div>

<div style="flex: 1; min-width: 300px; text-align: center;">
  <h4>🎖️ Award Recognition</h4>
  <img src="awards/award1.jpg" alt="Award Recognition" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
</div>

</div>

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; margin: 20px 0; text-align: center;">
  <h4>📜 Official Award Certificate</h4>
  <img src="awards/award2.jpg" alt="Official Award Certificate" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
  <p style="margin-top: 15px; color: white; font-weight: bold;">Official confirmation document from Department of Physical Education</p>
</div>

---

This project was recognized for its **innovative approach** to sports science testing, combining modern IoT technologies with practical fitness assessment needs.

**Competition Highlights:**
- ✅ **Innovative Technology** - MQTT-based wireless sensor communication
- ✅ **Comprehensive System** - Multi-protocol testing capabilities
- ✅ **User-Friendly Design** - Intuitive interface for sports professionals
- ✅ **Real-Time Analytics** - Instant data collection and analysis
- ✅ **Practical Application** - Ready-to-use solution for fitness testing

**Impact:**
This award-winning system demonstrates how modern technology can enhance sports science research and practical fitness assessment, making advanced testing protocols accessible to coaches, researchers, and sports professionals.

</div>

---

## 🛠️ Technology Stack

### Programming Languages
- **Python 3.7+** - Main application development
- **Arduino C++** - Sensor firmware

### Libraries & Frameworks
- **Tkinter** - GUI framework
- **Paho MQTT** - MQTT client
- **Matplotlib** - Data visualization
- **Pillow (PIL)** - Image processing
- **Bleak** - Bluetooth Low Energy
- **NumPy & SciPy** - Scientific computing

### Hardware
- Arduino-compatible microcontrollers
- IR/Laser sensors for timing gates
- Polar H10 heart rate monitor
- MQTT-enabled network infrastructure

### Protocols
- **MQTT** - Message queuing telemetry transport
- **Bluetooth Low Energy (BLE)** - HRV device communication

---

## 📝 Configuration

### MQTT Settings

Default broker configuration:
```python
BROKER_DEFAULT_IP = "192.168.100.189"
MQTT_PORT = 1883
```

### Sensor Topics

- `fitness_test/athlete_status_A` - Sensor A trigger
- `fitness_test/athlete_status_B` - Sensor B trigger
- `fitness_test/athlete_status_C` - Sensor C trigger
- ... (up to J)

### Test Parameters

**RAST Test:**
- Default sprints: 6
- Recovery time: 10 seconds
- Distance: 35 meters (configurable)

**Timing Gates:**
- Maximum sensors: 10 (A-J)
- Default distance: 100 meters
- Split distances: Configurable per segment

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Contribution Guidelines

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Development Team** - *Initial work and innovation*

---

## 🙏 Acknowledgments

- Department of Physical Education, Thailand
- Sport Science Innovation Competition organizers
- Open-source community for excellent libraries and tools
- All contributors and testers

---

## 📞 Support

For questions, issues, or feature requests, please open an issue on GitHub.

---

<div align="center">

**Made with ❤️ for Sports Science**

⭐ Star this repo if you find it helpful!

[⬆ Back to Top](#-smart-multi-stage-fitness-test-system)

</div>
