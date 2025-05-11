import streamlit as st
import pandas as pd

# Load data
data_files = {
    "All (전체)": None,
    "March (3월)": "3.csv",
    "April (4월)": "4.csv",
    "May (5월)": "5.csv"
}

all_data = []
for label, path in data_files.items():
    if path:
        df = pd.read_csv(path)
        df['월'] = label
        all_data.append(df)
merged_data = pd.concat(all_data, ignore_index=True)

# App title
st.title("월별 거래내역 보기")

# Sidebar for month selection
selected_month = st.sidebar.selectbox("월을 선택하세요:", list(data_files.keys()))

if selected_month == "All (전체)":
    data = merged_data
else:
    data = merged_data[merged_data['월'] == selected_month]

st.write("### 월별 전체 거래내역 보기")
st.dataframe(data)

# 시간 기준으로 함께 구매된 상품 조합 분석 및 단일 구매 분석
if '시간' in data.columns and '상품명' in data.columns:
    df_filtered = data[['시간', '상품명']].dropna()
    grouped = df_filtered.groupby('시간')['상품명'].apply(list)

    # ------------------------------------------------------------
    # Helper function: compute statistics for combos
    # ------------------------------------------------------------
    def compute_combo_stats(grouped_series: pd.Series, min_items: int):
        """
        Returns:
            stats_df : DataFrame with columns
                       [상품조합, 구매횟수, 판매금액, 이익률, 조합태그]
            grouped_filtered : Series filtered to the rows that make up the stats
        """
        # 1️⃣ Filter the grouped series by number of items
        if min_items == 1:
            grp = grouped_series[grouped_series.apply(len) == 1]
        else:
            grp = grouped_series[grouped_series.apply(len) >= min_items]

        # 2️⃣ Normalize order → consistent key
        combos = grp.apply(lambda x: tuple(sorted(x)))

        # 3️⃣ 기본 통계
        stats_df = combos.value_counts().reset_index()
        stats_df.columns = ['상품조합', '구매횟수']

        # 4️⃣ 판매금액과 이익률 계산 함수
        def _times_for(combo):
            return grp[grp.apply(lambda v: tuple(sorted(v)) == combo)].index

        def _sum_sales(combo):
            times = _times_for(combo)
            return data[data['시간'].isin(times)]['판매금액']\
                   .replace(',', '', regex=True).astype(float).sum()

        def _mean_margin(combo):
            times = _times_for(combo)
            sales = data[data['시간'].isin(times)]
            if sales.empty:
                return 0.0
            profit_ratio = (
                (sales['판매단가'].replace(',', '', regex=True).astype(float)
                 - sales['구입단가'].replace(',', '', regex=True).astype(float))
                / sales['판매단가'].replace(',', '', regex=True).astype(float)
            )
            return profit_ratio.mean()

        stats_df['판매금액'] = stats_df['상품조합'].apply(_sum_sales)
        stats_df['이익률']   = stats_df['상품조합'].apply(_mean_margin)
        stats_df['조합태그'] = stats_df['상품조합'].apply(lambda x: ' · '.join(x))
        return stats_df, grp

    st.write("### 상품 구매 분석 (시간 기준)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛍️ 함께 구매된 상품 조합 분석")
        combo_counts_multi, grouped_multi = compute_combo_stats(grouped, 2)

    with col2:
        st.subheader("🧾 단일 구매된 상품 분석")
        combo_counts_single, grouped_single = compute_combo_stats(grouped, 1)

    total_multi_sales = combo_counts_multi['판매금액'].sum()
    total_multi_profit = combo_counts_multi.apply(lambda row: row['판매금액'] * row['이익률'], axis=1).sum()
    total_multi_margin = total_multi_profit / total_multi_sales if total_multi_sales > 0 else 0

    total_single_sales = combo_counts_single['판매금액'].sum()
    total_single_profit = combo_counts_single.apply(lambda row: row['판매금액'] * row['이익률'], axis=1).sum()
    total_single_margin = total_single_profit / total_single_sales if total_single_sales > 0 else 0

    st.write("### 전체 판매 요약 통계")
    st.markdown(f"""
    - 🛍️ **조합 판매**: {len(combo_counts_multi)} 조합  
        - 총 판매금액: **{total_multi_sales:,.0f}원**  
        - 평균 이익률: **{total_multi_margin:.2%}**
    - 🧾 **단일 판매**: {len(combo_counts_single)} 품목  
        - 총 판매금액: **{total_single_sales:,.0f}원**  
        - 평균 이익률: **{total_single_margin:.2%}**
    """)

    with col1:
        st.dataframe(combo_counts_multi[['조합태그', '구매횟수', '판매금액', '이익률']].head(20))

    with col2:
        st.dataframe(combo_counts_single[['조합태그', '구매횟수', '판매금액', '이익률']].head(20))

    st.write("### 조합/단일 구매별 상세 판매 날짜 보기")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("조합 구매 날짜")
        for i in range(min(20, len(combo_counts_multi))):
            조합 = combo_counts_multi.loc[i, '상품조합']
            with st.expander(f"{조합}"):
                matching_times = df_filtered[df_filtered['시간'].isin(
                    grouped_multi[grouped_multi.apply(lambda x: tuple(sorted(x)) == 조합)].index
                )]['시간'].unique()
                날짜목록 = data[data['시간'].isin(matching_times)]['판매일자'].unique()
                for 날짜 in 날짜목록:
                    st.markdown(f"- {날짜}")

    with col4:
        st.subheader("단일 구매 날짜")
        for i in range(min(20, len(combo_counts_single))):
            조합 = combo_counts_single.loc[i, '상품조합']
            with st.expander(f"{조합}"):
                matching_times = df_filtered[df_filtered['시간'].isin(
                    grouped_single[grouped_single.apply(lambda x: tuple(sorted(x)) == 조합)].index
                )]['시간'].unique()
                날짜목록 = data[data['시간'].isin(matching_times)]['판매일자'].unique()
                for 날짜 in 날짜목록:
                    st.markdown(f"- {날짜}")
else:
    st.info("시간 또는 상품명 데이터가 부족하여 분석할 수 없습니다.")