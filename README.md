to start:  python app.py

Website Architechture:
- app.py --> Run a replica of the user's dashboard, but with real-time data
- streamlit run app2.py --> AI advice model

- api.py --> Fetches current weather data based on data.gov.sg weather API
- weather_service.py --> where main functions are defined, such as getting data based on filters like user's location

intial html setup credits: https://medium.com/@francesco.saviano87/build-responsive-dashboards-with-chart-js-fc5f7cc42f52
