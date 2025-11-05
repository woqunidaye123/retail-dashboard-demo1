
# ==========================
# 零售深度分析 BI 仪表盘（人 / 货 / 场）
# 支持线路所属部门 + 渠道 + 返货率 + 同比 / 环比 + 目标达成率
# ==========================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="零售深度分析 BI 仪表盘", layout="wide")
st.title("零售深度分析 BI 仪表盘（人 / 货 / 场）")

st.markdown("请上传包含销售明细的 Excel 文件，字段需包含："
            "`Date, Store, Channel, Region, SKU, Category, Quantity, Sales, Discount, OrderID, "
            "Dept, ReturnAmount, TargetSales`")

uploaded_file = st.file_uploader("上传 Excel 数据文件", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    required_columns = [
        'Date','Store','Channel','Region','SKU','Category',
        'Quantity','Sales','Discount','OrderID',
        'Dept','ReturnAmount','TargetSales'
    ]
    if not all(col in df.columns for col in required_columns):
        st.error(f"缺少必要字段：{required_columns}")
    else:
        df['Date'] = pd.to_datetime(df['Date'])
        for col in ['Quantity','Sales','Discount','ReturnAmount','TargetSales']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df[(df['Sales']>0) & (df['Quantity']>0)]
        df['YearMonth'] = df['Date'].dt.to_period('M')
        df['Discount'] = df['Discount'].fillna(0)
        df['ReturnAmount'] = df['ReturnAmount'].fillna(0)
        df['TargetSales'] = df['TargetSales'].fillna(0)

        # =====================
        # 筛选器
        # =====================
        st.sidebar.header("筛选条件")
        months = df['YearMonth'].astype(str).unique()
        selected_months = st.sidebar.multiselect("选择月份", months, default=list(months))
        depts = df['Dept'].unique()
        selected_depts = st.sidebar.multiselect("选择分销站", depts, default=list(depts))
        channels = df['Channel'].unique()
        selected_channels = st.sidebar.multiselect("选择渠道", channels, default=list(channels))
        stores = df['Store'].unique()
        selected_stores = st.sidebar.multiselect("选择门店", stores, default=list(stores))

        df_filtered = df[
            df['YearMonth'].astype(str).isin(selected_months) &
            df['Dept'].isin(selected_depts) &
            df['Channel'].isin(selected_channels) &
            df['Store'].isin(selected_stores)
        ].copy()

        if df_filtered.empty:
            st.warning("筛选条件下无数据")
            st.stop()

        # =====================
        # 整体 KPI
        # =====================
        kpi_month = df_filtered.groupby('YearMonth').agg(
            GMV=('Sales','sum'),
            Orders=('OrderID','nunique'),
            Qty=('Quantity','sum'),
            Returns=('ReturnAmount','sum'),
            Target=('TargetSales','sum')
        ).reset_index()

        kpi_month['ATV'] = kpi_month['GMV']/kpi_month['Orders']
        kpi_month['UPT'] = kpi_month['Qty']/kpi_month['Orders']
        kpi_month['ReturnRate'] = kpi_month['Returns']/kpi_month['GMV']
        kpi_month['TargetAch'] = kpi_month['GMV']/kpi_month['Target']
        kpi_month['YearMonth_str'] = kpi_month['YearMonth'].astype(str)

        latest = kpi_month.iloc[-1]

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("GMV 总销售额", f"{latest['GMV']:.2f}")
        c2.metric("客单价 ATV", f"{latest['ATV']:.2f}")
        c3.metric("件单价 UPT", f"{latest['UPT']:.2f}")
        c4.metric("返货率", f"{latest['ReturnRate']:.2%}")
        c5.metric("目标达成率", f"{latest['TargetAch']:.2%}")
        c6.metric("订单数", f"{latest['Orders']}")

        # =====================
        # 按线路部门 + 渠道分析
        # =====================
        st.subheader("按线路所属部门 + 渠道 KPI")

        dept_df = df_filtered.groupby(['Dept','Channel','YearMonth']).agg(
            GMV=('Sales','sum'),
            Return=('ReturnAmount','sum'),
            Target=('TargetSales','sum')
        ).reset_index()

        dept_df['ReturnRate'] = dept_df['Return']/dept_df['GMV']
        dept_df['TargetAch'] = dept_df['GMV']/dept_df['Target']

        latest_month = dept_df['YearMonth'].max()
        current = dept_df[dept_df['YearMonth']==latest_month]

        current['ReturnRate%'] = (current['ReturnRate']*100).round(2).astype(str)+'%'
        current['TargetAch%'] = (current['TargetAch']*100).round(2).astype(str)+'%'
        st.dataframe(current[['Dept','Channel','GMV','ReturnRate%','TargetAch%']], use_container_width=True)

        # =====================
        # 趋势图
        # =====================
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=kpi_month['YearMonth_str'], y=kpi_month['GMV'], name="GMV"))
        fig.add_trace(go.Scatter(x=kpi_month['YearMonth_str'], y=kpi_month['ATV'], name="ATV", yaxis="y2"))
        fig.update_layout(
            title="GMV 与 ATV 趋势",
            xaxis_title="月份",
            yaxis_title="GMV",
            yaxis2=dict(title="ATV", overlaying="y", side="right")
        )
        st.plotly_chart(fig, use_container_width=True)

        # =====================
        # 渠道饼图 / 门店排行
        # =====================
        col1, col2 = st.columns(2)
        with col1:
            channel_sales = df_filtered.groupby('Channel')['Sales'].sum().reset_index()
            fig_pie = px.pie(channel_sales, values='Sales', names='Channel', title='各渠道销售额占比')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            store_sales = df_filtered.groupby('Store')['Sales'].sum().sort_values(ascending=False).head(5)
            fig_bar = px.bar(x=store_sales.index, y=store_sales.values, title='TOP5 门店销售额')
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("请上传 Excel 文件开始分析。")
