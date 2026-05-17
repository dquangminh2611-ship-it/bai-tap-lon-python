import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# ── Hằng số cấu hình ──
FILE_CSV   : str   = 'thong_ke_cau_thu_epl_2526.csv'
STATS_COLS : list  = ['Age', 'Min', 'Gls', 'Gls.1', 'Ast', 'Ast.1']
K_RANGE    : range = range(2, 6)
K_OPTIMAL  : int   = 3


def chuan_bi_du_lieu(duong_dan: str, cac_cot: list) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Đọc file CSV và chuẩn hoá dữ liệu các cột số bằng StandardScaler.

    Args:
        duong_dan (str): Đường dẫn đến file CSV chứa dữ liệu cầu thủ.
        cac_cot (list): Danh sách tên các cột số cần dùng cho phân cụm.

    Returns:
        tuple[pd.DataFrame, np.ndarray]: Tuple gồm DataFrame gốc và
            ma trận đã chuẩn hoá dạng numpy array (shape: n_samples × n_features).
    """
    df       : pd.DataFrame = pd.read_csv(duong_dan)
    X        : pd.DataFrame = df[cac_cot].apply(pd.to_numeric, errors='coerce').fillna(0)
    X_scaled : np.ndarray   = StandardScaler().fit_transform(X)
    return df, X_scaled


def tinh_chi_so_cum(X_scaled: np.ndarray, k_range: range) -> tuple[list[float], list[float]]:
    """
    Tính WCSS và Silhouette Score cho từng giá trị K trong khoảng cho trước.

    Args:
        X_scaled (np.ndarray): Ma trận đặc trưng đã chuẩn hoá.
        k_range (range): Khoảng giá trị K cần thử nghiệm.

    Returns:
        tuple[list[float], list[float]]: Tuple gồm danh sách WCSS và
            danh sách Silhouette Score tương ứng với từng K.
    """
    wcss       : list[float] = []
    sil_scores : list[float] = []

    for k in k_range:
        mo_hinh = KMeans(n_clusters=k, random_state=42, n_init=10)
        mo_hinh.fit(X_scaled)
        wcss.append(mo_hinh.inertia_)
        sil_scores.append(silhouette_score(X_scaled, mo_hinh.labels_))

    return wcss, sil_scores


def ve_bieu_do_chon_k(k_range: range, wcss: list[float], sil_scores: list[float]) -> None:
    """
    Vẽ biểu đồ Elbow và Silhouette Score để hỗ trợ chọn K tối ưu.

    Args:
        k_range (range): Khoảng giá trị K đã thử nghiệm.
        wcss (list[float]): Danh sách giá trị WCSS tương ứng với từng K.
        sil_scores (list[float]): Danh sách Silhouette Score tương ứng với từng K.

    Returns:
        None
    """
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(k_range, wcss, 'bo-')
    plt.title('Biểu đồ Elbow')
    plt.xlabel('Số lượng nhóm (k)')
    plt.ylabel('WCSS')

    plt.subplot(1, 2, 2)
    plt.plot(k_range, sil_scores, 'ro-')
    plt.title('Biểu đồ Silhouette Score')
    plt.xlabel('Số lượng nhóm (k)')
    plt.ylabel('Silhouette Score')

    plt.show()


def phan_cum_kmeans(df: pd.DataFrame, X_scaled: np.ndarray, k: int) -> pd.DataFrame:
    """
    Thực hiện phân cụm K-Means và gán nhãn cụm vào DataFrame.

    Args:
        df (pd.DataFrame): DataFrame gốc chứa dữ liệu cầu thủ.
        X_scaled (np.ndarray): Ma trận đặc trưng đã chuẩn hoá.
        k (int): Số lượng cụm K tối ưu cần phân chia.

    Returns:
        pd.DataFrame: DataFrame gốc có thêm cột 'Cluster' chứa nhãn cụm (0 đến k-1).
    """
    mo_hinh      = KMeans(n_clusters=k, random_state=42, n_init=10)
    df['Cluster'] = mo_hinh.fit_transform(X_scaled).argmax(axis=1)
    return df


def giam_chieu_pca(X_scaled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Giảm chiều dữ liệu xuống 2D và 3D bằng PCA để trực quan hoá.

    Args:
        X_scaled (np.ndarray): Ma trận đặc trưng đã chuẩn hoá (n_samples × n_features).

    Returns:
        tuple[np.ndarray, np.ndarray]: Tuple gồm ma trận 2D (n_samples × 2)
            và ma trận 3D (n_samples × 3) sau khi giảm chiều.
    """
    X_2d : np.ndarray = PCA(n_components=2).fit_transform(X_scaled)
    X_3d : np.ndarray = PCA(n_components=3).fit_transform(X_scaled)
    return X_2d, X_3d


def ve_scatter_2d(X_2d: np.ndarray, nhan_cum: pd.Series) -> None:
    """
    Vẽ biểu đồ phân tán 2D từ dữ liệu sau khi giảm chiều bằng PCA.

    Args:
        X_2d (np.ndarray): Ma trận toạ độ 2D (n_samples × 2).
        nhan_cum (pd.Series): Nhãn cụm tương ứng với từng điểm dữ liệu.

    Returns:
        None
    """
    plt.figure(figsize=(8, 6))
    plt.scatter(X_2d[:, 0], X_2d[:, 1], c=nhan_cum, cmap='viridis')
    plt.title('Phân cụm cầu thủ trên mặt phẳng 2D (PCA)')
    plt.colorbar(label='Nhóm (Cluster)')
    plt.show()


def ve_scatter_3d(X_3d: np.ndarray, nhan_cum: pd.Series) -> None:
    """
    Vẽ biểu đồ phân tán 3D từ dữ liệu sau khi giảm chiều bằng PCA.

    Args:
        X_3d (np.ndarray): Ma trận toạ độ 3D (n_samples × 3).
        nhan_cum (pd.Series): Nhãn cụm tương ứng với từng điểm dữ liệu.

    Returns:
        None
    """
    fig : plt.Figure = plt.figure(figsize=(10, 8))
    ax                = fig.add_subplot(111, projection='3d')
    ax.scatter(X_3d[:, 0], X_3d[:, 1], X_3d[:, 2], c=nhan_cum, cmap='viridis')
    ax.set_title('Phân cụm cầu thủ khối 3D (PCA)')
    plt.show()


def machine_learning_analysis() -> None:
    """
    Hàm chính điều phối toàn bộ quy trình phân tích machine learning:
    đọc dữ liệu → tính chỉ số cụm → vẽ biểu đồ chọn K →
    phân cụm K-Means → giảm chiều PCA → trực quan hoá 2D và 3D.

    Returns:
        None
    """
    df, X_scaled = chuan_bi_du_lieu(FILE_CSV, STATS_COLS)

    wcss, sil_scores = tinh_chi_so_cum(X_scaled, K_RANGE)
    ve_bieu_do_chon_k(K_RANGE, wcss, sil_scores)

    df = phan_cum_kmeans(df, X_scaled, K_OPTIMAL)

    X_2d, X_3d = giam_chieu_pca(X_scaled)
    ve_scatter_2d(X_2d, df['Cluster'])
    ve_scatter_3d(X_3d, df['Cluster'])

    print(f"✅ Đã hoàn thành phân cụm K-means với K={K_OPTIMAL}")


if __name__ == "__main__":
    machine_learning_analysis()