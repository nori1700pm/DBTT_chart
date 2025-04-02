#!/bin/sh

# Start Flask app in the background
python app.py &

# Wait for 10 seconds to let Flask initialize
sleep 10

# Start Streamlit app
streamlit run streamlit/app2.py
