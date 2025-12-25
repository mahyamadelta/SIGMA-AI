# 🌳 SIGMA-AI
SIGMA-AI is an AIoT-based garden monitoring and analytics system designed to monitor environmental conditions and provide intelligent insights using Machine Learning. The project integrates IoT sensors, an AI model, and an interactive dashboard to support smarter garden management.

The dashboard is built using Streamlit, while the Machine Learning model runs on a separate AI server. All system communication is handled using the MQTT protocol, making the architecture modular and scalable.

## 🧠 Technologies 
- `Python`
- `Streamlit for interactive dashboard visualization`
- `Machine Learning (model stored as smart_garden_model.pkl)`
- `MQTT Protocol for IoT communication`
- `Pickle (.pkl) for model serialization`
- `IoT Sensors as data sources`
- `requirements.txt for dependency management`

## ✨ Features
- Real-time IoT sensor data visualization
- Machine Learning-based analysis and prediction
- Decoupled architecture between dashboard and AI server
- MQTT-based data communication
- Easy setup and extensible project structure

## 🔄 System Workflow
1. IoT sensors publish data via MQTT
2. Sensor data is sent to the topic:

   ```text
   iot/sensor/tralalilo_trolia/data
   ```
3. The AI server (`model_server.py`) subscribes to the topic and processes data using the ML model
4. Prediction or control results are published to:

   ```text
   iot/sensor/tralalilo_trolia/control
   ```
5. The Streamlit dashboard (`dashboard.py`) subscribes and displays data and analytics results

## 📚 What I Learned
* Building **IoT dashboards using Streamlit**
* Separating **AI inference servers from frontend applications**
* Integrating **Machine Learning models into IoT systems**
* Implementing real-time communication using **MQTT**
* Managing project dependencies with `requirements.txt`
* Designing a modular and scalable **AIoT system architecture**

## 🚀 How Can This Project Be Improved?
* Deploy the system to cloud or edge environments
* Add user authentication and role-based access
* Replace static models with **online or incremental learning**
* Integrate alert notifications (Telegram, Email, WhatsApp)

## ▶️ How to Run the Project

1. Clone the repository:
   ```bash
   git clone https://github.com/username/SIGMA-AI.git
   cd SIGMA-AI
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the AI model server:
   ```bash
   python model_server.py
   ```
4. Run the Streamlit dashboard:
   ```bash
   streamlit run dashboard.py
   ```
5. Ensure the MQTT broker is running and IoT sensors are publishing data to the correct topics.
