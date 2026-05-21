import altair as alt
import base64
import pandas as pd
import streamlit as st
from pengolahan_duplikasi import process_deduplication, BASE_NAMA_COL, BASE_EMAIL_COL, BASE_NIB_COL
from pengolahan_matching import process_matching_file

st.set_page_config(page_title='Ngibar App', page_icon='🎯', layout='wide')

st.markdown(
    """
    <style>
        .stApp {
            background: #f5f7fb;
            color: #0f172a;
        }
        .stButton>button {
            border-radius: 0.75rem;
            padding: 0.85rem 1.25rem;
            font-weight: 600;
        }
        .stAlert {
            border-radius: 1rem;
        }
        .stDataFrame div[role='grid'] {
            width: 100% !important;
        }
        .streamlit-expanderHeader {
            font-size: 1rem;
        }
        .page-title {
            text-align: center;
            margin: 1.25rem auto 0.5rem;
            font-size: 2.5rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.1;
        }
        .page-subtitle {
            text-align: center;
            margin: 0.25rem auto 1.5rem;
            color: #475569;
            font-size: 1rem;
            max-width: 720px;
        }
        .header-image {
            width: 100%;
            max-width: 1200px;
            display: block;
            margin: 0 auto 1.5rem;
            height: auto;
            border-radius: 1rem;
        }
        .header-description {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 1rem;
            padding: 1rem 1.25rem;
            box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
            margin: auto auto 1.5rem;
            max-width: 1200px;
        }
        @media (max-width: 760px) {
            .stApp {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            .stButton>button {
                width: 100% !important;
                min-height: 3rem;
                font-size: 1rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="page-title">Monitoring Progres Ngibar 3600</div>', unsafe_allow_html=True)
# st.markdown('<div class="page-subtitle">Gunakan tombol di bawah untuk menjalankan proses monitoring. Berikut adalah tabel berisi daftar perusahaan yang sudah mengisi Form.</div>', unsafe_allow_html=True)

header_path = 'data/header.png'
with open(header_path, 'rb') as header_file:
    header_base64 = base64.b64encode(header_file.read()).decode('utf-8')

st.markdown(
    f"""
    <img src="data:image/png;base64,{header_base64}" style="width:100%; max-width:100%; height:auto; border-radius:1rem; margin-bottom:1.25rem;" />
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class='header-description'>
        <p style='margin: 0; font-size: 1.05rem;'>Gunakan tombol di bawah untuk menjalankan proses monitoring. Berikut adalah tabel berisi daftar perusahaan yang sudah mengisi Form.</p>
        <p style='margin: 0.5rem 0 0 0; color: #334155;'>Tip: untuk melihat tabel pada layar kecil, gunakan fitur geser horizontal di dalam tabel jika tersedia.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

excel_path = 'data/hasil_fasih_api dan target.xlsx'

if 'checked' not in st.session_state:
    st.session_state.checked = False

button_label = 'Ulang Pengecekan' if st.session_state.checked else 'Mulai Pengecekan'
button_style = '#f6c300' if st.session_state.checked else '#ff8c00'
button_text_color = '#0f172a' if st.session_state.checked else '#ffffff'

st.markdown(
    f"""
    <style>
        .stButton>button {{
            background-color: {button_style} !important;
            color: {button_text_color} !important;
            border: none !important;
            box-shadow: none !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

if st.button(button_label, key='recheck_button', on_click=lambda: st.session_state.update({'checked': True})):
    with st.spinner('Memproses data usaha...'):
        try:
            # Step 1: Deduplication
            st.info('📋 Step 1: Menghapus duplikasi data base...')
            df_base_deduplicated, df_duplicates_info = process_deduplication(excel_path)
            duplicates_count = len(df_duplicates_info)
            st.success(f'✓ Duplikasi dihapus: {duplicates_count} baris')

            if duplicates_count > 0:
                with st.expander(f'Lihat detail {duplicates_count} duplikasi yang dihapus'):
                    df_display = df_duplicates_info[['baris_dihapus', 'baris_referensi', 'nama_dihapus', 'nama_referensi', 'skor_kemiripan', 'duplicate_reason']].copy()
                    df_display.columns = ['Baris Dihapus', 'Baris Referensi', 'Nama Dihapus', 'Nama Referensi', 'Skor (%)', 'Alasan']
                    df_display.index = range(1, len(df_display) + 1)
                    st.dataframe(df_display, height=400)

            # Step 2: Matching
            st.info('🔗 Step 2: Melakukan matching...')
            df_match, total_target = process_matching_file(
                excel_path, 
                df_base_deduplicated=df_base_deduplicated
            )
            matched_count = len(df_match)
            not_filled_count = max(total_target - matched_count, 0)
            score_88_matches = df_match[df_match['final_score'].round(0) == 88]
            score_88_count = len(score_88_matches)
            st.success(f'✓ Pengecekan selesai. Ditemukan {matched_count} usaha yang sudah mengisi Form dari total {total_target} usaha.')

            if score_88_count > 0:
                st.warning(f'⚠️ Ada {score_88_count} hasil matching dengan skor akhir 88.')
                with st.expander(f'Lihat detail {score_88_count} baris matching skor 88'):
                    df_score_88_matches = score_88_matches[['target_nama', 'target_email', 'matched_nama', 'matched_email', 'match_method', 'final_score']].copy()
                    df_score_88_matches.columns = ['Nama Usaha', 'Email Usaha', 'Nama Yang Cocok', 'Email Yang Cocok', 'Metode Match', 'Skor Kemiripan']
                    df_score_88_matches.index = range(1, len(df_score_88_matches) + 1)
                    st.dataframe(df_score_88_matches, height=400)

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

            st.altair_chart((pie_chart + label_chart).properties(height=400), width='stretch')

            if matched_count > 0:
                df_display = df_match[['target_nama', 'matched_email', 'final_score']].rename(
                    columns={
                        'target_nama': 'Nama Usaha',
                        'matched_email': 'Email Usaha',
                        'final_score': 'Skor Kemiripan',
                    }
                ).reset_index(drop=True)
                df_display.index = range(1, len(df_display) + 1)
                st.dataframe(df_display, height=500)
            else:
                st.info('Tidak ada hasil usaha yang sudah mengisi Form.')
        except Exception as error:
            st.error(f'Gagal memproses file: {error}')
