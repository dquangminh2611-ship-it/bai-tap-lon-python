from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
from io import StringIO


def tao_trinh_duyet() -> webdriver.Chrome:
    """
    Khởi tạo và trả về một phiên trình duyệt Chrome với cấu hình chống bot.

    Returns:
        webdriver.Chrome: Đối tượng trình duyệt Chrome đã được cấu hình.
    """
    cau_hinh = webdriver.ChromeOptions()
    cau_hinh.add_argument('--disable-blink-features=AutomationControlled')
    cau_hinh.add_experimental_option("excludeSwitches", ["enable-automation"])
    cau_hinh.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=cau_hinh)


def lay_noi_dung_html(trinh_duyet: webdriver.Chrome, url: str, thoi_gian_cho: int = 15) -> str:
    """
    Điều hướng trình duyệt tới URL và trả về mã nguồn HTML sau khi trang tải xong.

    Args:
        trinh_duyet (webdriver.Chrome): Phiên trình duyệt đang hoạt động.
        url (str): Địa chỉ trang web cần truy cập.
        thoi_gian_cho (int): Số giây chờ để trang tải hoàn toàn. Mặc định là 15.

    Returns:
        str: Mã nguồn HTML của trang sau khi đã xử lý bỏ các thẻ comment.
    """
    print(f"🌐 Đang kết nối tới: {url}")
    trinh_duyet.get(url)
    print("⏳ Đang tải nội dung... (Vui lòng xác thực 'I am human' nếu trang yêu cầu)")
    time.sleep(thoi_gian_cho)
    noi_dung_html = trinh_duyet.page_source
    return re.sub(r"<!--|-->", "", noi_dung_html)


def tim_bang_du_lieu(noi_dung_sach: str) -> pd.DataFrame | None:
    """
    Phân tích HTML và tìm bảng thống kê cầu thủ hợp lệ.

    Args:
        noi_dung_sach (str): Chuỗi HTML đã được làm sạch (bỏ comment).

    Returns:
        pd.DataFrame | None: DataFrame chứa dữ liệu bảng nếu tìm thấy, ngược lại trả về None.
    """
    print("🔍 Đang phân tích cấu trúc bảng...")
    danh_sach_bang = pd.read_html(StringIO(noi_dung_sach))
    for bang in danh_sach_bang:
        if isinstance(bang.columns, pd.MultiIndex):
            bang.columns = bang.columns.droplevel(0)
        if 'Player' in bang.columns and 'Min' in bang.columns:
            return bang
    return None


def xu_ly_du_lieu(bang_du_lieu: pd.DataFrame, nguong_phut: int = 90) -> pd.DataFrame:
    """
    Làm sạch và lọc dữ liệu từ bảng thống kê cầu thủ.

    Args:
        bang_du_lieu (pd.DataFrame): DataFrame thô vừa được trích xuất từ trang web.
        nguong_phut (int): Ngưỡng số phút thi đấu tối thiểu để giữ lại cầu thủ. Mặc định là 90.

    Returns:
        pd.DataFrame: DataFrame đã được lọc, làm sạch và đánh số thứ tự.
    """
    bang_du_lieu = bang_du_lieu[bang_du_lieu['Player'] != 'Player']
    bang_du_lieu['Min'] = bang_du_lieu['Min'].astype(str).str.replace(',', '')
    bang_du_lieu['Min'] = pd.to_numeric(bang_du_lieu['Min'], errors='coerce').fillna(0)

    ket_qua_loc = bang_du_lieu[bang_du_lieu['Min'] > nguong_phut].copy()
    ket_qua_loc = ket_qua_loc.fillna('N/a')

    ket_qua_loc.reset_index(drop=True, inplace=True)
    ket_qua_loc.index = ket_qua_loc.index + 1
    ket_qua_loc.index.name = 'STT'

    cac_cot = ket_qua_loc.columns.tolist()
    if 'Player' in cac_cot:
        cac_cot.insert(0, cac_cot.pop(cac_cot.index('Player')))
        ket_qua_loc = ket_qua_loc[cac_cot]

    return ket_qua_loc


def xuat_csv(du_lieu: pd.DataFrame, ten_file: str) -> None:
    """
    Xuất DataFrame ra file CSV với encoding UTF-8 có BOM (hỗ trợ tiếng Việt trên Excel).

    Args:
        du_lieu (pd.DataFrame): DataFrame cần xuất ra file.
        ten_file (str): Tên file CSV đầu ra (bao gồm phần mở rộng .csv).

    Returns:
        None
    """
    du_lieu.to_csv(ten_file, encoding='utf-8-sig')
    print(f"✅ Hoàn tất! Đã lưu {len(du_lieu)} cầu thủ vào hệ thống.")
    print(f"📁 Tệp tin: {ten_file}")


def thu_thap_du_lieu_ngoai_hang_anh() -> None:
    """
    Hàm chính điều phối toàn bộ quy trình cào dữ liệu thống kê cầu thủ
    từ FBref cho mùa giải 2025-2026 và xuất kết quả ra file CSV.

    Returns:
        None
    """
    URL = "https://fbref.com/en/comps/9/stats/Premier-League-Stats"
    TEN_FILE_XUAT = 'thong_ke_cau_thu_epl_2526.csv'

    print("🚀 Thiết lập trình duyệt Chrome...")
    trinh_duyet = tao_trinh_duyet()

    try:
        noi_dung_sach = lay_noi_dung_html(trinh_duyet, URL)
        bang_du_lieu = tim_bang_du_lieu(noi_dung_sach)

        if bang_du_lieu is not None:
            ket_qua = xu_ly_du_lieu(bang_du_lieu)
            xuat_csv(ket_qua, TEN_FILE_XUAT)
        else:
            print("❌ Lỗi: Không tìm thấy bảng dữ liệu mục tiêu trên trang web.")

    except Exception as loi:
        print(f"❌ Hệ thống gặp lỗi: {loi}")
    finally:
        trinh_duyet.quit()
        print("🔌 Đã đóng trình duyệt.")


if __name__ == "__main__":
    thu_thap_du_lieu_ngoai_hang_anh()