# 零售深度分析 BI 仪表盘（完整部署版）
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="零售深度分析 BI 仪表盘", layout="wide")
st.title("零售深度分析 BI 仪表盘（人 / 货 / 场）")

uploaded_file = st.file_uploader("上传 Excel 数据文件", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    required_columns = ['Date','Store','Channel','Region','SKU','Category','Quantity','Sales','Discount','OrderID','Dept','ReturnAmount','TargetSales']
    if not all(col in df.columns for col in required_columns):
        st.error(f"缺少字段：{required_columns}")
        st.stop()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['YearMonth'] = df['Date'].dt.to_period('M')
    st.sidebar.header("筛选条件")
    months = sorted(df['YearMonth'].astype(str).unique())
    selected_months = st.sidebar.multiselect("选择月份", months, default=months)
    depts = sorted(df['Dept'].astype(str).unique())
    selected_depts = st.sidebar.multiselect("选择分销站", depts, default=depts)
    channels = sorted(df['Channel'].astype(str).unique())
    selected_channels = st.sidebar.multiselect("选择渠道", channels, default=channels)
    df_filtered = df[df['YearMonth'].astype(str).isin(selected_months) & df['Dept'].astype(str).isin(selected_depts) & df['Channel'].astype(str).isin(selected_channels)]
    if df_filtered.empty:
        st.warning("筛选条件下无数据"); st.stop()
    kpi = df_filtered.groupby('YearMonth').agg(GMV=('Sales','sum'), Orders=('OrderID','nunique'), Qty=('Quantity','sum'), Returns=('ReturnAmount','sum'), Target=('TargetSales','sum')).reset_index()
    kpi['ATV'] = kpi['GMV']/kpi['Orders']; kpi['UPT'] = kpi['Qty']/kpi['Orders']
    kpi['ReturnRate'] = kpi['Returns']/kpi['GMV']; kpi['TargetAch'] = kpi['GMV']/kpi['Target']
    latest = kpi.iloc[-1]
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("GMV", f"{latest['GMV']:.2f}"); c2.metric("ATV", f"{latest['ATV']:.2f}"); c3.metric("UPT", f"{latest['UPT']:.2f}")
    c4.metric("返货率", f"{latest['ReturnRate']:.2%}"); c5.metric("目标达成率", f"{latest['TargetAch']:.2%}"); c6.metric("订单数", f"{latest['Orders']}")
    st.subheader("线路 + 渠道表现")
    dept_df = df_filtered.groupby(['Dept','Channel']).agg(GMV=('Sales','sum'),ReturnAmount=('ReturnAmount','sum'),Target=('TargetSales','sum')).reset_index()
    dept_df['返货率'] = dept_df['ReturnAmount']/dept_df['GMV']; dept_df['目标达成率'] = dept_df['GMV']/dept_df['Target']
    st.dataframe(dept_df, use_container_width=True)
    st.subheader("趋势图")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=kpi['YearMonth'].astype(str), y=kpi['GMV'], name='GMV'))
    fig.add_trace(go.Scatter(x=kpi['YearMonth'].astype(str), y=kpi['ATV'], name='ATV', yaxis='y2'))
    fig.update_layout(yaxis2=dict(title='ATV', overlaying='y', side='right'))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("请上传 Excel 文件开始分析。")
