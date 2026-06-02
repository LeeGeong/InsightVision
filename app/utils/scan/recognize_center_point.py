from scan.util.open_file_to_pcd import file_to_pcd_np
from scan.util.cut import cut_from_rect_point
from scan.util.exclude import exclude
from scan.util.segment_plane import segment_plane
from scan.util.get_grab_point import get_grab_point
from scan.util.calculate_safe_area import calculate_safe_area

def get_error_data() -> dict:
    return {
        "isSuccess": False,
        "grab_point": [0,0,0],
        "safe_area": {
            "SafetyMaxX": 0.0,
            "SafetyMinX": 0.0,
            "SafetyMaxY": 0.0,
            "SafetyMinY": 0.0
        },
    }

def recognize_center_point(file_path : str, rect_point : list) -> dict:
    '''
    :param file_path: 点云文件路径
    :param rect_point: 视觉传来的四边形的四个点
    :return:  抓点、安全区（dict）
    '''
    data = {
        "isSuccess": True,
        "grab_point": None,
        "safe_area" : None,
    }

    try:
        pcd_np = file_to_pcd_np(file_path)

        # 1.切割 - 视觉传来的四边形的四个点
        data["isSuccess"], pcd_cut_from_rect= cut_from_rect_point(pcd_np, rect_point)
        if not data["isSuccess"]:
            return get_error_data()

        # 2.判断排除是否为钢板，并切割地面
        data["isSuccess"], pcd_steel= exclude(pcd_cut_from_rect)
        if not data["isSuccess"]:
            return get_error_data()

        # 3.平板切割
        data["isSuccess"], pcd_segment_plane= segment_plane(pcd_steel)
        if not data["isSuccess"]:
            return get_error_data()

        # 4.计算抓点
        grab_point = get_grab_point(pcd_segment_plane)
        data["grab_point"] = grab_point

        # 5.计算安全区
        area = calculate_safe_area(pcd_np, pcd_segment_plane)
        data["safe_area"] = area

    except:
        data = get_error_data()

    return data


if __name__ == "__main__":
    file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\638678751396409734.xyz"
    res = recognize_center_point(file_dir,[[7361,414920],[19599,414761],[19681,419170],[7480,419354]])


    # file_dir = r"D:\项目\JinZhongSteelRecognize\Data\638610362230520111.3.scan_result_got.xyz"
    # res = recognize_center_point(file_dir,[[14063,87888],[26402,87686],[26444,90262],[14105,90464]])

    # file_dir = r"D:\项目\JinZhongSteelRecognize\Data\638610404557880366.3.scan_result_got.xyz"
    # res = recognize_center_point(file_dir,[[15040,88329],[27581,88193],[27608,90712],[15067,90848]])

    print(res)


