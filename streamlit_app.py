import altair as alt
import pandas as pd
import streamlit as st
from pengolahan_duplikasi import process_deduplication, BASE_NAMA_COL, BASE_EMAIL_COL, BASE_NIB_COL
from pengolahan_matching import process_matching_file

st.set_page_config(page_title='Monitoring App', page_icon='🎯', layout='wide')

st.title('🎈 Monitoring App')
st.write('Gunakan tombol di bawah untuk menjalankan proses monitoring. Berikut adalah tabel berisi daftar perusahaan yang sudah mengisi Form.')

excel_path = 'data/hasil_fasih_api dan target.xlsx'

if st.button('Mulai Pengecekan'):
    with st.spinner('Memproses data usaha...'):
        try:
            # Step 1: Deduplication
            st.info('📋 Step 1: Menghapus duplikasi data base...')
            df_base_deduplicated, df_duplicates_info = process_deduplication(excel_path)
            duplicates_count = len(df_duplicates_info)
            st.success(f'✓ Duplikasi dihapus: {duplicates_count} baris')
            
            if duplicates_count > 0:
                with st.expander(f'Lihat detail {duplicates_count} duplikasi yang dihapus'):
                    df_display = df_duplicates_info[['baris_dihapus', 'baris_referensi', 'nama_dihapus', 'nama_referensi', 'skor_kemiripan']].copy()
                    df_display.columns = ['Baris Dihapus', 'Baris Referensi', 'Nama Dihapus', 'Nama Referensi', 'Skor (%)']
                    df_display.index = range(1, len(df_display) + 1)
                    st.dataframe(df_display, height=400, use_container_width=True)

            # Step 2: Matching
            st.info('🔗 Step 2: Melakukan matching...')
            df_match, total_target = process_matching_file(
                excel_path, 
                df_base_deduplicated=df_base_deduplicated
            )
            matched_count = len(df_match)
            not_filled_count = max(total_target - matched_count, 0)
            st.success(f'✓ Pengecekan selesai. Ditemukan {matched_count} usaha yang sudah mengisi Form dari total {total_target} usaha.')

            chart_data = pd.DataFrame({
                'status': ['Sudah Mengisi', 'Belum Mengisi'],
                'count': [matched_count, not_filled_count],
            })
            chart_data['percentage'] = (chart_data['count'] / chart_data['count'].sum() * 100).round(1)

            pie_chart = alt.Chart(chart_data).mark_arc(innerRadius=60, stroke='#ffffff', strokeWidth=2).encode(
                theta=alt.Theta(field='count', type='quantitative'),
                color=alt.Color(
                    field='status',
                    type='nominal',
                    scale=alt.Scale(domain=['Sudah Mengisi', 'Belum Mengisi'], range=['#1f77b4', '#d62728']),
                    legend=alt.Legend(title='Status')
                ),
                tooltip=[
                    alt.Tooltip('status:N', title='Status'),
                    alt.Tooltip('count:Q', title='Jumlah'),
                    alt.Tooltip('percentage:Q', title='Persentase', format='.1f')
                ]
            )

            label_chart = alt.Chart(chart_data).mark_text(radiusOffset=30, size=14, color='white', fontWeight='bold').encode(
                theta=alt.Theta(field='count', type='quantitative'),
                text=alt.Text('percentage:Q', format='.1f')
            )

            st.altair_chart((pie_chart + label_chart).properties(height=400), use_container_width=True)

            if matched_count > 0:
                df_display = df_match[['target_nama', 'matched_email']].rename(
                    columns={'target_nama': 'Nama Usaha', 'matched_email': 'Email Usaha'}
                ).reset_index(drop=True)
                df_display.index = range(1, len(df_display) + 1)
                st.dataframe(df_display, height=500)
            else:
                st.info('Tidak ada hasil usaha yang sudah mengisi Form.')
        except Exception as error:
            st.error(f'Gagal memproses file: {error}')
