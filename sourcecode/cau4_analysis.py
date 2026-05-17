import pandas as pd

def doc_du_lieu(duong_dan: str, cac_cot: list) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(duong_dan)
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file. Hãy chạy Câu 1 trước!")
        return None
    for col in cac_cot:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def tinh_thong_ke(df: pd.DataFrame, cac_cot: list, output_file: str) -> None:
    team_stats = df.groupby('Squad')[cac_cot].agg(['mean', 'median', 'std'])
    team_stats.to_csv(output_file)
    print(f"✅ Đã lưu bảng thống kê (mean/median/std) vào: {output_file}")

def tim_doi_dan_dau(summary_sum: pd.DataFrame, cac_cot: list,
                    output_file: str) -> pd.DataFrame:
    """Tìm đội dẫn đầu mỗi chỉ số và lưu ra CSV riêng."""
    records = []
    for col in cac_cot:
        top_team  = summary_sum[col].idxmax()
        top_value = summary_sum[col].max()
        records.append({
            'Chi_so':    col,
            'Doi_dan_dau': top_team,
            'Gia_tri':   round(top_value, 2)
        })
    df_top = pd.DataFrame(records)
    df_top.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ Đã lưu bảng đội dẫn đầu vào: {output_file}")
    print(df_top.to_string(index=False))
    return df_top

def nhan_dinh_phong_do(summary_sum: pd.DataFrame) -> None:
    best_attack = summary_sum['Gls'].idxmax()
    highest_xG  = summary_sum['Gls.1'].idxmax()
    print("\n--- Nhận định phong độ mùa giải 2025-2026 ---")
    if best_attack == highest_xG:
        print(f"{best_attack} là đội có phong độ xuất sắc nhất.")
        print("Lý do: Dẫn đầu cả bàn thắng thực tế (Gls) lẫn cơ hội tạo ra (xG).")
    else:
        print(f"Hàng công sắc bén nhất: {best_attack} (Gls cao nhất).")
        print(f"Tạo nhiều cơ hội nhất:  {highest_xG} (xG cao nhất).")

def analyze_team_stats() -> None:
    STATS_COLS       = ['Age', 'Min', 'Gls', 'Gls.1', 'Ast', 'Ast.1']
    FILE_THONG_KE    = 'team_stats_analysis.csv'      # mean/median/std
    FILE_DOI_DAN_DAU = 'team_leading_by_stat.csv'     # đội dẫn đầu từng chỉ số ← thêm mới

    df = doc_du_lieu('thong_ke_cau_thu_epl_2526.csv', STATS_COLS)
    if df is None:
        return

    tinh_thong_ke(df, STATS_COLS, FILE_THONG_KE)

    summary_sum = df.groupby('Squad')[STATS_COLS].sum()
    tim_doi_dan_dau(summary_sum, STATS_COLS, FILE_DOI_DAN_DAU)  # ← lưu CSV
    nhan_dinh_phong_do(summary_sum)

if __name__ == "__main__":
    analyze_team_stats()