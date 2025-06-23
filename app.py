import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import datetime

st.set_page_config(layout="wide")
st.title("Core2 Event Log Viewer with Summary Table, Date Filter, and PDF Export")

uploaded_files = st.file_uploader("Upload Event*.csv files", type="csv", accept_multiple_files=True)

if uploaded_files:
    summary_data = []
    plots = []

    # Date range selection
    st.markdown("### Optional: Filter Events by Date Range")
    min_date = datetime.date(2023, 1, 1)
    max_date = datetime.date.today()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    for file in uploaded_files:
        try:
            text_io = file.getvalue().decode('mbcs').splitlines()
            meta = { "serialNo": "", "name": "", "ComSW": "", "CtrlSW": "", "SWVersion": "", "PlantName": "", "Gridcode": "" }
            for i, line in enumerate(text_io[:14]):
                if i == 1: meta["serialNo"] = line.split(":")[1].strip()
                if i == 2: meta["name"] = line.split(":")[1].strip()
                if i == 3: meta["ComSW"] = line.split(":")[1].strip()
                if i == 4: meta["CtrlSW"] = line.split(":")[1].strip()
                if i == 8: meta["PlantName"] = line.split(":")[1].strip()
                if i == 9: meta["SWVersion"] = line.split("n:")[1].strip() if "n:" in line else ""
                if i == 11: meta["Gridcode"] = line.split(":")[1].strip()

            df = pd.read_csv(file, encoding='mbcs', skiprows=15)
            df["EDate"] = pd.to_datetime(df["DateTime yyyy-MM-dd hh:mm:ss"])
            df = df[df["EDate"].dt.year > 2022]
            df = df.set_index("EDate").iloc[::-1]

            # Apply date range filter
            df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

            # Categorize events
            contactor = df[df['ID'].isin([213,214,215,216,217,218,219,220,221,362,252,253,254])]
            safety = df[df['ID'].isin([365])]
            pv = df[(df['ID'] >= 100) & (df['ID'] <= 250)]
            failsafe = df[(df['ID'] >= 224) & (df['ID'] <= 249)]
            network = df[(df['ID'] >= 2012) & (df['ID'] <= 2056)]

            # Plotly chart
            fig = go.Figure()
            if not safety.empty:
                fig.add_trace(go.Scatter(x=safety.index, y=safety["Description"], mode='markers', name="Safety", marker=dict(color="red", symbol="x")))
            if not pv.empty:
                fig.add_trace(go.Scatter(x=pv.index, y=pv["Description"], mode='markers', name="PV", marker=dict(color="orange", symbol="x")))
            if not failsafe.empty:
                fig.add_trace(go.Scatter(x=failsafe.index, y=failsafe["Description"], mode='markers', name="Failsafe", marker=dict(color="red", symbol="circle")))
            if not network.empty:
                fig.add_trace(go.Scatter(x=network.index, y=network["Description"], mode='markers', name="Network", marker=dict(color="green", symbol="circle")))
            if not contactor.empty:
                fig.add_trace(go.Scatter(x=contactor.index, y=contactor["Description"], mode='markers', name="Contactor", marker=dict(color="blue", symbol="circle")))

            fig.update_layout(
                title=f"Serial: {meta['serialNo']} | Name: {meta['name']} | Plant: {meta['PlantName']}",
                xaxis_title="Date",
                yaxis_title="Event Description",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            plots.append((fig, meta))  # store for PDF

            # Add to summary
            summary_data.append({
                "Serial No": meta["serialNo"],
                "Name": meta["name"],
                "Plant": meta["PlantName"],
                "Safety Events": len(safety),
                "PV Events": len(pv),
                "Failsafe Events": len(failsafe),
                "Network Events": len(network),
                "Contactor Events": len(contactor),
                "Total Events": len(df)
            })

        except Exception as e:
            st.warning(f"Failed to process {file.name}: {e}")

    # Display summary
    st.markdown("### Summary Table")
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df)

    # PDF Export
    if st.button("Generate PDF Report"):
        buffer = BytesIO()
        with PdfPages(buffer) as pdf:
            for fig, meta in plots:
                fig_mpl, ax = plt.subplots(figsize=(15, 6))
                ax.set_title(f"{meta['serialNo']} | {meta['name']} | {meta['PlantName']}")
                ax.set_xlabel("Date")
                ax.set_ylabel("Event Description")
                ax.grid(True)

                for trace in fig.data:
                    ax.scatter(trace.x, trace.y, label=trace.name, s=50)

                ax.legend(loc='upper right')
                pdf.savefig(fig_mpl, bbox_inches='tight')
                plt.close(fig_mpl)

            # Add summary table
            fig, ax = plt.subplots(figsize=(10, 2 + 0.25 * len(summary_df)))
            ax.axis('off')
            tbl = ax.table(cellText=summary_df.values,
                           colLabels=summary_df.columns,
                           cellLoc='center',
                           loc='center')
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        st.download_button("Download PDF", buffer.getvalue(), "event_summary_report.pdf", mime="application/pdf")

else:
    st.info("Please upload Event*.csv files to begin.")
