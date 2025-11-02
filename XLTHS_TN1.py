import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://192.168.1.253:8086"
INFLUX_TOKEN = "YSHMaYi6ZtfwL9j2mGPSlOWa5udBMTPD8J3dX3bz4Ef4LB98205HxIpRQZ_-pb_o_McJU96R-qFtQvDZZaUOfg=="
INFLUX_ORG = "Sky"
INFLUX_BUCKET = "proxmox"

flux_query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -6h)  // Lấy dữ liệu 6 giờ qua
  |> filter(fn: (r) => r._measurement == "cpustat")
  |> filter(fn: (r) => r._field == "avg1")
  |> filter(fn: (r) => r.host == "skymyname")
  |> map(fn: (r) => ({{
      _time: r._time,
      _value: r._value / 4.0 * 100.0,
      _field: "CPU Load %"
  }}))
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false) // Gộp mỗi 1 phút
'''

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
result_tables = query_api.query(flux_query, org=INFLUX_ORG)

data = []
for table in result_tables:
    for record in table.records:
        data.append((record.get_time(), record.get_value()))

df = pd.DataFrame(data, columns=['time', 'cpu_load'])
df = df.set_index('time')

if df.empty:
    print("Không tìm thấy dữ liệu. Hãy kiểm tra lại query hoặc time range.")
else:
    print(f"Đã tải về {len(df)} điểm dữ liệu.")

    df['cpu_ma'] = df['cpu_load'].rolling(window=10).mean()

    if len(df) > 51:
        df['cpu_savgol'] = savgol_filter(df['cpu_load'], 
                                         window_length=51, 
                                         polyorder=3)
    else:
        print("Không đủ dữ liệu để chạy Savitzky-Golay, bỏ qua...")

    plt.figure(figsize=(15, 7))
    plt.plot(df.index, df['cpu_load'], label='Gốc (Nhiễu)', alpha=0.5)
    plt.plot(df.index, df['cpu_ma'], label='Lọc Moving Average (10 min)', linestyle='--', linewidth=2)
    
    if 'cpu_savgol' in df.columns:
        plt.plot(df.index, df['cpu_savgol'], label='Lọc Savitzky-Golay (w=51, p=3)', color='red', linewidth=2)

    plt.title('Phân tích DSP: Làm mịn tín hiệu CPU Load')
    plt.ylabel('CPU Load %')
    plt.xlabel('Thời gian')
    plt.legend()
    plt.grid(True)
    plt.show()