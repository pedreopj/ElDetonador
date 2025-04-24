import streamlit as st
import streamlit.components.v1 as components
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración desde archivo local
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET

# Función para consultar múltiples campos de un mismo measurement
def query_accelerometer_data(range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    import "math"
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "accelerometer" and r["_field"] == "ax" or r["_field"] == "ay" or r["_field"] == "az")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(query)
    if result.empty:
        return pd.DataFrame()

    # Renombrar y calcular magnitud
    result = result.rename(columns={"_time": "time"})
    result["accel_magnitude"] = np.sqrt(result["ax"]**2 + result["ay"]**2 + result["az"]**2)
    result["time"] = pd.to_datetime(result["time"])
    return result[["time", "accel_magnitude"]]

# Consulta simple de un solo campo
def query_data(measurement, field, range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query(query)
    data = []

    for table in result:
        for record in table.records:
            data.append({"time": record.get_time(), field: record.get_value()})

    df = pd.DataFrame(data)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    return df

# Configuración de la app
st.set_page_config(page_title="🌿 Koru – Jardín Inteligente", layout="wide")
st.title("🌿 Koru – Jardín Inteligente para la Calma")
st.markdown("Monitorea en tiempo real los datos de tu planta: temperatura, humedad y movimiento.")

# Selector de tiempo
range_minutes = st.slider("Selecciona el rango de tiempo (en minutos):", 10, 180, 60)

# Consultas
temp_df = query_data("airSensor", "temperature", range_minutes)
hum_df = query_data("airSensor", "humidity", range_minutes)
mov_df = query_accelerometer_data(range_minutes)

# Visualización
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Temperatura (°C)")
    if not temp_df.empty:
        st.plotly_chart(px.line(temp_df, x="time", y="temperature", title="Temperatura"), use_container_width=True)
    else:
        st.info("Sin datos de temperatura en este rango.")

with col2:
    st.subheader("💧 Humedad (%)")
    if not hum_df.empty:
        st.plotly_chart(px.line(hum_df, x="time", y="humidity", title="Humedad"), use_container_width=True)
    else:
        st.info("Sin datos de humedad en este rango.")

st.subheader("📈 Movimiento (magnitud del acelerómetro)")
if not mov_df.empty:
    st.plotly_chart(px.line(mov_df, x="time", y="accel_magnitude", title="Movimiento"), use_container_width=True)
else:
    st.info("Sin datos de movimiento en este rango.")


st.subheader("🌿 Estado animado del helecho")

if not hum_df.empty:
    humedad_actual = hum_df.iloc[-1]["humidity"]

    if humedad_actual < 50:
        escala = 0.8
        color = "#A1887F"  # marrón seco
        mensaje = f"Humedad baja ({humedad_actual:.1f}%) – tu planta necesita agua 🥀"
    elif humedad_actual > 75:
        escala = 1.3
        color = "#4CAF50"  # verde exuberante
        mensaje = f"Humedad alta ({humedad_actual:.1f}%) – la planta está muy bien 🌳"
    else:
        escala = 1.0
        color = "#81C784"  # verde saludable
        mensaje = f"Humedad óptima ({humedad_actual:.1f}%) – todo está en equilibrio 🍃"

    fern_svg = f"""
    <div style="text-align: center;">
        <svg width="200" height="200" viewBox="0 0 100 100">
            <g transform="scale({escala}) translate(15,15)">
                <path d="M50,10 Q60,30 50,50 Q40,70 50,90" 
                      fill="none" 
                      stroke="{color}" 
                      stroke-width="5" 
                      stroke-linecap="round">
                    <animate attributeName="stroke-dasharray" from="0,150" to="150,0" dur="1.5s" repeatCount="indefinite"/>
                </path>
            </g>
        </svg>
        <p style="font-size: 18px;">{mensaje}</p>
    </div>
    """
    components.html(fern_svg, height=250)
else:
    st.info("No hay datos recientes de humedad para mostrar el helecho.")
