import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px

# --- Streamlit UI Config ---
st.set_page_config(layout='wide', page_title='Energy Dashboard')
st.title("Energy Usage Dashboard")

# --- DB Connection ---
def get_data():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=43.204.185.146,1433;'
        'DATABASE=SizeChangeEQA;'
        'UID=KimbalUser;'
        'PWD=i63VX8D6lNFC'
    )

    query = """
    WITH LatestRTC AS (
        SELECT MAX(RTCdateTime) AS recent_time
        FROM singlephase.BlockLoadProfile
        WHERE CAST(createddate AS DATE) = CAST(GETUTCDATE() AS DATE)
    ),
    MeterStats AS (
        SELECT 
            d.category,
            COUNT(DISTINCT d.meterno) AS total_meters,
            COUNT(DISTINCT md.meterno) AS received_data
        FROM dash d
        LEFT JOIN singlephase.BlockLoadProfile md
            ON d.meterno = md.meterno
            AND md.RtcDateTime = (SELECT recent_time FROM LatestRTC)
            AND CAST(md.createddate AS DATE) = CAST(GETUTCDATE() AS DATE)
        GROUP BY d.category
    )
    SELECT 
        category,
        total_meters,
        received_data,
        total_meters - received_data AS missed_data
    FROM MeterStats;
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- Fetch Data ---
final_df = get_data()

if final_df.empty:
    st.warning("No data found.")
else:
    categories = final_df['category'].unique()
    cols = st.columns(len(categories))  # One column per category

    for i, category in enumerate(categories):
        category_data = final_df[final_df['category'] == category]
        plot_df = pd.melt(
            category_data,
            id_vars=['category'],
            value_vars=['total_meters', 'received_data', 'missed_data'],
            var_name='Status',
            value_name='Count'
        )

        # Friendly label mapping
        plot_df['Status'] = plot_df['Status'].replace({
            'total_meters': 'Total Meters',
            'received_data': 'Received Data',
            'missed_data': 'Missed Data'
        })

        # Add percentage
        total = plot_df.loc[plot_df['Status'] == 'Total Meters', 'Count'].values[0]
        plot_df['Percentage'] = plot_df.apply(
            lambda row: 100 if row['Status'] == 'Total Meters'
            else round((row['Count'] / total) * 100, 2) if total > 0 else 0,
            axis=1
        )

        # Colors
        color_map = {
            'Total Meters': '#FDB45C',      # blue
            'Received Data': '#76D7C4',     # green
            'Missed Data': '#E74C3C'        # red
        }

        fig = px.bar(
            plot_df,
            x='Status',
            y='Count',
            color='Status',
            color_discrete_map=color_map,
            title=f'Category: {category}',
            custom_data=['Count', 'Percentage']
        )

        fig.update_traces(
            text=None,  # Removes visible bar labels
            hovertemplate='<b>%{x}</b><br>Count: %{customdata[0]}<br>Percentage: %{customdata[1]:.2f}%'
        )

        fig.update_layout(
            yaxis_title='Meters',
            xaxis_title='',
            showlegend=False,
            height=400,
            margin=dict(t=30, b=20)
        )

        cols[i].plotly_chart(fig, use_container_width=True)
