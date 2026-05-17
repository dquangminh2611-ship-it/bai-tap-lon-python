from flask import Flask, jsonify, request, Response
import pandas as pd
import os

# Khởi tạo ứng dụng Flask
ung_dung_web = Flask(__name__)

# Cấu hình đường dẫn tệp tin dữ liệu
TEP_DU_LIEU_CSV: str = 'thong_ke_cau_thu_epl_2526.csv'


def doc_du_lieu_tu_csv() -> pd.DataFrame | None:
    """
    Truy xuất dữ liệu từ tệp CSV đã thu thập.

    Returns:
        pd.DataFrame | None: DataFrame chứa toàn bộ dữ liệu nếu tệp tồn tại,
        ngược lại trả về None.
    """
    if not os.path.exists(TEP_DU_LIEU_CSV):
        return None
    return pd.read_csv(TEP_DU_LIEU_CSV)


def tao_phan_hoi_loi(thong_diep: str, ma_trang_thai: int) -> tuple[Response, int]:
    """
    Tạo phản hồi JSON chuẩn cho các trường hợp lỗi.

    Args:
        thong_diep (str): Nội dung thông báo lỗi trả về cho người dùng.
        ma_trang_thai (int): Mã HTTP status code (ví dụ: 400, 404, 500).

    Returns:
        tuple[Response, int]: Tuple gồm đối tượng Response JSON và mã trạng thái HTTP.
    """
    return jsonify({
        "trang_thai": "loi",
        "thong_diep": thong_diep
    }), ma_trang_thai


def loc_cau_thu(bang_du_lieu: pd.DataFrame, tu_khoa: str) -> pd.DataFrame:
    """
    Lọc danh sách cầu thủ theo từ khóa tìm kiếm (không phân biệt hoa/thường).

    Args:
        bang_du_lieu (pd.DataFrame): DataFrame chứa toàn bộ dữ liệu cầu thủ.
        tu_khoa (str): Chuỗi từ khóa cần tìm trong cột 'Player'.

    Returns:
        pd.DataFrame: DataFrame chứa các hàng khớp với từ khóa tìm kiếm.
    """
    return bang_du_lieu[
        bang_du_lieu['Player'].str.contains(tu_khoa, case=False, na=False)
    ]


@ung_dung_web.route('/', methods=['GET'])
def trang_chu() -> tuple[Response, int]:
    """
    Endpoint mặc định để kiểm tra trạng thái hoạt động của server.

    Returns:
        tuple[Response, int]: JSON thông báo trạng thái và mã HTTP 200.
    """
    return jsonify({
        "trang_thai": "dang_chay",
        "thong_diep": "Hệ thống API dữ liệu Ngoại hạng Anh đã sẵn sàng!",
        "huong_dan": "/api/player?name=[Ten_Cau_Thu]"
    }), 200


@ung_dung_web.route('/api/player', methods=['GET'])
def tra_cuu_cau_thu() -> tuple[Response, int]:
    """
    Endpoint tìm kiếm thông tin chi tiết cầu thủ theo tên.

    Query Parameters:
        name (str): Tên hoặc một phần tên cầu thủ cần tra cứu.

    Returns:
        tuple[Response, int]: JSON chứa kết quả tìm kiếm và mã HTTP tương ứng.
            - 200: Tìm thấy dữ liệu thành công.
            - 400: Thiếu tham số 'name' trong request.
            - 404: Không tìm thấy cầu thủ phù hợp.
            - 500: Tệp dữ liệu CSV chưa tồn tại.
    """
    tu_khoa_tim_kiem: str | None = request.args.get('name')

    if not tu_khoa_tim_kiem:
        return tao_phan_hoi_loi(
            "Vui lòng nhập tên cầu thủ cần tra cứu (ví dụ: ?name=Salah)", 400
        )

    bang_du_lieu: pd.DataFrame | None = doc_du_lieu_tu_csv()

    if bang_du_lieu is None:
        return tao_phan_hoi_loi(
            f"Dữ liệu nguồn ({TEP_DU_LIEU_CSV}) chưa được khởi tạo.", 500
        )

    ket_qua_loc: pd.DataFrame = loc_cau_thu(bang_du_lieu, tu_khoa_tim_kiem)

    if ket_qua_loc.empty:
        return jsonify({
            "trang_thai": "khong_tim_thay",
            "thong_diep": f"Không có dữ liệu cho cầu thủ: '{tu_khoa_tim_kiem}'"
        }), 404

    danh_sach_thong_ke: list[dict] = ket_qua_loc.to_dict(orient='records')

    return jsonify({
        "trang_thai": "thanh_cong",
        "tong_so": len(danh_sach_thong_ke),
        "du_lieu": danh_sach_thong_ke
    }), 200


if __name__ == '__main__':
    print("--- KHỞI CHẠY HỆ THỐNG QUẢN LÝ DỮ LIỆU CẦU THỦ ---")
    print(f"📍 Điểm cuối API: http://127.0.0.1:5000/api/player?name=...")
    ung_dung_web.run(host='0.0.0.0', port=5000, debug=True)