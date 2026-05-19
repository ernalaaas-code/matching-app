import pandas as pd
import re
import rapidfuzz

# Kolom yang dipakai untuk deduplication
BASE_NAMA_COL = 'data1'
BASE_EMAIL_COL = 'email'
BASE_NIB_COL = 'data6'

# Kolom tambahan untuk deduplication
BASE_ALAMAT_COL = 'data2'

def clean_nama(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_email(value):
    if pd.isna(value):
        return ''
    return str(value).strip().lower()

def normalize_nib(value):
    if pd.isna(value):
        return ''
    text = str(value).strip()
    if text.endswith('.0'):
        text = text[:-2]
    return re.sub(r'\D', '', text)

def normalize_alamat(value):
    if pd.isna(value):
        return ''
    text = str(value).lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_similarity_score(name1, name2):
    """Hitung skor kemiripan antara dua nama menggunakan fuzzy matching"""
    token_set = rapidfuzz.fuzz.token_set_ratio(name1, name2)
    token_sort = rapidfuzz.fuzz.token_sort_ratio(name1, name2)
    partial = rapidfuzz.fuzz.partial_ratio(name1, name2)
    return round((token_set + token_sort + partial) / 3, 2)

def remove_duplicates(df_base, similarity_threshold=90):
    """
    Hapus duplikasi dari df_base berdasarkan kemiripan nama dan alamat (>= threshold)
    Mengembalikan: (df_deduplicated, df_duplicates_info)
    df_duplicates_info berisi: baris_dihapus, baris_referensi, nama_dihapus, nama_referensi, alamat_dihapus, alamat_referensi, skor_kemiripan
    """
    df_base = df_base.copy()
    df_base['original_index'] = range(len(df_base))

    # Bersihkan nama dan alamat
    df_base['nama_clean'] = df_base[BASE_NAMA_COL].apply(clean_nama)
    df_base['alamat_clean'] = df_base[BASE_ALAMAT_COL].apply(normalize_alamat)
    df_base['email_clean'] = df_base[BASE_EMAIL_COL].apply(normalize_email)
    df_base['nib_clean'] = df_base[BASE_NIB_COL].apply(normalize_nib)

    # Tandai baris yang akan dihapus dan track pasangannya
    indices_to_drop = set()
    duplicates_info = []
    names = df_base['nama_clean'].fillna('').tolist()
    addresses = df_base['alamat_clean'].fillna('').tolist()

    for i in range(len(df_base)):
        if i in indices_to_drop:
            continue

        for j in range(i + 1, len(df_base)):
            if j in indices_to_drop:
                continue

            name_similarity = get_similarity_score(names[i], names[j])
            address_similarity = get_similarity_score(addresses[i], addresses[j])
            combined_similarity = (name_similarity + address_similarity) / 2

            # Jika kemiripan >= threshold, tandai indeks j sebagai duplikasi dari i
            if combined_similarity >= similarity_threshold:
                indices_to_drop.add(j)
                duplicates_info.append({
                    'baris_dihapus': j,
                    'baris_referensi': i,
                    'nama_dihapus': df_base.iloc[j][BASE_NAMA_COL],
                    'nama_referensi': df_base.iloc[i][BASE_NAMA_COL],
                    'alamat_dihapus': df_base.iloc[j][BASE_ALAMAT_COL],
                    'alamat_referensi': df_base.iloc[i][BASE_ALAMAT_COL],
                    'email_dihapus': df_base.iloc[j][BASE_EMAIL_COL],
                    'email_referensi': df_base.iloc[i][BASE_EMAIL_COL],
                    'skor_kemiripan': combined_similarity,
                })

    # Simpan informasi duplikasi
    df_duplicates_info = pd.DataFrame(duplicates_info)

    # Hapus duplikasi dan reset index
    df_deduplicated = df_base.drop(index=list(indices_to_drop)).reset_index(drop=True)

    return df_deduplicated, df_duplicates_info

def load_base_data(path, sheet_base='Sheet1'):
    """Load base data dari Excel"""
    df_base = pd.read_excel(path, sheet_name=sheet_base)
    return df_base

def process_deduplication(path, sheet_base='Sheet1', similarity_threshold=90):
    """
    Main function untuk menjalankan deduplication
    Mengembalikan (df_deduplicated, df_removed)
    """
    df_base = load_base_data(path, sheet_base)

    df_deduplicated, df_removed = remove_duplicates(df_base, similarity_threshold=similarity_threshold)

    return df_deduplicated, df_removed

if __name__ == '__main__':
    excel_path = r'data\hasil_fasih_api dan target.xlsx'
    df_deduplicated, removed = process_deduplication(excel_path)
    print(f'Duplikasi dihapus: {removed}')
    print(f'Total baris base: {len(df_deduplicated)}')
    print(df_deduplicated.head())
