import pandas as pd
import re
import rapidfuzz

# Kolom yang dipakai untuk matching
BASE_NAMA_COL = 'data1'
BASE_EMAIL_COL = 'email'
BASE_EMAIL_COL2= 'data4'
BASE_NIB_COL = 'data6'


def remove_parentheses(text):
    text = str(text)
    return re.sub(r'\s*\([^)]*\)\s*', ' ', text).strip()

TARGET_NAMA_COL = 'Nama'
TARGET_EMAIL_COL = 'email'
TARGET_NIB_COL = 'NIB'


def clean_nama(text):
    text = remove_parentheses(text)
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_nib(value):
    if pd.isna(value):
        return ''
    text = str(value).strip()
    if text.endswith('.0'):
        text = text[:-2]
    return re.sub(r'\D', '', text)


def normalize_email(value):
    if pd.isna(value):
        return ''
    return str(value).strip().lower()


def get_best_name_match(target_name, base_choices):
    if not target_name:
        return None, 0, 0, 0, 0

    token_set = rapidfuzz.process.extractOne(target_name, base_choices, scorer=rapidfuzz.fuzz.token_set_ratio)
    token_sort = rapidfuzz.process.extractOne(target_name, base_choices, scorer=rapidfuzz.fuzz.token_sort_ratio)
    partial = rapidfuzz.process.extractOne(target_name, base_choices, scorer=rapidfuzz.fuzz.partial_ratio)

    candidates = {}

    for result in [token_set, token_sort, partial]:
        if result is None:
            continue

        _, _, idx = result
        base_name = base_choices[idx]

        scores = {
            'token_set_score': rapidfuzz.fuzz.token_set_ratio(target_name, base_name),
            'token_sort_score': rapidfuzz.fuzz.token_sort_ratio(target_name, base_name),
            'partial_ratio_score': rapidfuzz.fuzz.partial_ratio(target_name, base_name),
        }
        scores['final_score'] = round(sum(scores.values()) / len(scores), 2)
        candidates[idx] = scores

    if not candidates:
        return None, 0, 0, 0, 0

    best_idx, best_scores = max(candidates.items(), key=lambda item: item[1]['final_score'])
    return (
        best_idx,
        best_scores['token_set_score'],
        best_scores['token_sort_score'],
        best_scores['partial_ratio_score'],
        best_scores['final_score'],
    )


def load_data(path, sheet_base='Sheet1', sheet_target='target', df_base_deduplicated=None):
    """
    Load data dari Excel, atau gunakan df_base_deduplicated jika sudah tersedia
    """
    if df_base_deduplicated is not None:
        df_base = df_base_deduplicated.copy()
    else:
        df_base = pd.read_excel(path, sheet_name=sheet_base)
    
    df_target = pd.read_excel(path, sheet_name=sheet_target)
    return df_base, df_target


def prepare_dataframes(df_base, df_target):
    df_base = df_base.copy()
    df_target = df_target.copy()

    df_base['nama_clean'] = df_base[BASE_NAMA_COL].apply(clean_nama)
    df_target['nama_clean'] = df_target[TARGET_NAMA_COL].apply(clean_nama)

    df_base['nib_clean'] = df_base[BASE_NIB_COL].apply(normalize_nib)
    df_base['email_clean'] = df_base[BASE_EMAIL_COL].apply(normalize_email)
    df_base['email_clean2'] = df_base[BASE_EMAIL_COL2].apply(normalize_email)

    df_target['nib_clean'] = df_target[TARGET_NIB_COL].apply(normalize_nib)
    df_target['email_clean'] = df_target[TARGET_EMAIL_COL].apply(normalize_email)

    return df_base, df_target


def match_records(df_base, df_target, score_threshold=90):
    base_name_choices = df_base['nama_clean'].fillna('').tolist()

    base_by_nib = (
        df_base[df_base['nib_clean'] != '']
        .drop_duplicates('nib_clean')
        .set_index('nib_clean')
    )

    base_by_email = (
        df_base[df_base['email_clean'] != '']
        .drop_duplicates('email_clean')
        .set_index('email_clean')
    )

    base_by_email2 = (
        df_base[df_base['email_clean2'] != '']
        .drop_duplicates('email_clean2')
        .set_index('email_clean2')
    )

    matches = []

    for target_idx, target_row in df_target.iterrows():
        match_idx = None
        match_method = ''
        token_set_score = 0
        token_sort_score = 0
        partial_ratio_score = 0
        final_score = 0

        target_nib = target_row['nib_clean']
        target_email = target_row['email_clean']
        target_name = target_row['nama_clean']

        if target_nib and target_nib in base_by_nib.index:
            match_idx = df_base.index[df_base['nib_clean'] == target_nib][0]
            match_method = 'NIB'
            final_score = 100

        elif target_email and target_email in base_by_email2.index:
            match_idx = df_base.index[df_base['email_clean2'] == target_email][0]
            match_method = 'email2'
            final_score = 100

        elif target_email and target_email in base_by_email.index:
            match_idx = df_base.index[df_base['email_clean'] == target_email][0]
            match_method = 'email'
            final_score = 100

        else:
            (
                match_idx,
                token_set_score,
                token_sort_score,
                partial_ratio_score,
                final_score,
            ) = get_best_name_match(target_name, base_name_choices)
            match_method = 'nama_fuzzy' if match_idx is not None else 'tidak_match'

        base_row = df_base.loc[match_idx] if match_idx is not None else pd.Series(dtype='object')

        matches.append({
            'target_index': target_idx,
            'target_nama': target_row[TARGET_NAMA_COL],
            'target_nib': target_row[TARGET_NIB_COL],
            'target_email': target_row[TARGET_EMAIL_COL],
            'match_index': match_idx,
            'match_method': match_method,
            'matched_nama': base_row.get(BASE_NAMA_COL, ''),
            'matched_nib': base_row.get(BASE_NIB_COL, ''),
            'matched_email': base_row.get(BASE_EMAIL_COL, ''),
            'matched_email2': base_row.get(BASE_EMAIL_COL2, ''),
            # 'matched_email_used': base_row.get(BASE_EMAIL_COL2, '') if match_method == 'email2' else base_row.get(BASE_EMAIL_COL, ''),
            'token_set_score': token_set_score,
            'token_sort_score': token_sort_score,
            'partial_ratio_score': partial_ratio_score,
            'final_score': final_score,
        })

    df_match = pd.DataFrame(matches)
    df_match = df_match[df_match['final_score'] >= score_threshold].reset_index(drop=True)
    return df_match


def process_matching_file(path, sheet_base='Sheet1', sheet_target='target', score_threshold=90, df_base_deduplicated=None):
    """
    Main function untuk matching
    Parameter df_base_deduplicated memungkinkan penggunaan base data yang sudah dideduplication
    """
    df_base, df_target = load_data(path, sheet_base, sheet_target, df_base_deduplicated)
    df_base, df_target = prepare_dataframes(df_base, df_target)
    df_match = match_records(df_base, df_target, score_threshold=score_threshold)
    return df_match, len(df_target)


if __name__ == '__main__':
    excel_path = r'data\hasil_fasih_api dan target.xlsx'
    df_match, total_target = process_matching_file(excel_path)
    print(df_match.head())
    print(f'Total target rows: {total_target}')
