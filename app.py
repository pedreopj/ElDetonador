import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
from datetime import timedelta, datetime

# Configuración de conexión a InfluxDB
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET

# Función para obtener datos desde InfluxDB
def query_data(measurement, field, range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    start_time = f"-{range_minutes}m"
    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {start_time})
      |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")
      |> sort(columns: ["_time"])
    '''

    tables = query_api.query(query)
    results = []
    for table in tables:
        for record in table.records:
            results.append((record.get_time(), record.get_value()))
    
    df = pd.DataFrame(results, columns=["time", field])
    return df

# Título y descripción
st.set_page_config(page_title="Koru 🌿", layout="wide")
st.title("🌿 Koru – Jardín Inteligente para la Calma")
st.markdown("Visualiza en tiempo real el estado de tu planta: temperatura, humedad y movimiento.")

# Selección de rango de tiempo
range_minutes = st.slider("Selecciona el rango de tiempo (minutos)", 10, 180, 60)

# Consulta de datos
temp_df = query_data("clima", "temperature", range_minutes)
hum_df = query_data("clima", "humidity", range_minutes)
accel_df = query_data("movimiento", "accel_magnitude", range_minutes)

# Layout de columnas
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Temperatura (°C)")
    if not temp_df.empty:
        fig_temp = px.line(temp_df, x="time", y="temperature", title="Temperatura")
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.warning("No hay datos de temperatura disponibles.")

with col2:
    st.subheader("💧 Humedad (%)")
    if not hum_df.empty:
        fig_hum = px.line(hum_df, x="time", y="humidity", title="Humedad")
        st.plotly_chart(fig_hum, use_container_width=True)
    else:
        st.warning("No hay datos de humedad disponibles.")

st.subheader("📈 Movimiento (magnitud del acelerómetro)")
if not accel_df.empty:
    fig_accel = px.line(accel_df, x="time", y="accel_magnitude", title="Movimiento")
    st.plotly_chart(fig_accel, use_container_width=True)
else:
    st.warning("No hay datos de movimiento disponibles.")
