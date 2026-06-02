import pandas as pd
from typing import Dict, Any
from app.log import logger


def filtering_algorithm(return_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    OCR结果智能过滤算法

    该函数根据多个条件对OCR识别结果进行智能过滤和筛选：
    1. 如果只有一条记录，直接返回
    2. 统计 status 为 'success' 的记录数量
    3. 如果 success_count == 1：只保留 success 记录，删除所有 error 记录
    4. 如果 success_count > 1：
       - 筛选掉 error 的数据，只保留 success
       - 找出重复的 Ocr_BatchNo（出现次数 > 1）
       - 只保留重复的 Ocr_BatchNo，删除不重复的记录
       - 对重复项只保留第一个
       - 如果去重后剩余数据 > 1 条，按照 Priority 的值取最小的
    5. 如果 success_count == 0：直接返回原始数据

    参数:
        return_dict: 包含 OCR 结果的字典，结构如下:
            - results: 字典列表，每个字典包含 OCR 数据
              必须包含 'Ocr_BatchNo' 和 'status' 字段
              可选包含 'Priority' 字段（用于优先级排序）

    返回:
        经过过滤和去重后的结果字典。如果输入无效，则返回原始字典。

    处理逻辑示例:
        >>> # 场景1：只有一个 success
        >>> data = {"results": [
        ...     {"Ocr_BatchNo": "001", "status": "success"},
        ...     {"Ocr_BatchNo": "002", "status": "error"}
        ... ]}
        >>> result = filtering_algorithm(data)
        >>> len(result["results"])
        1

        >>> # 场景2：多个 success，需要去重和优先级排序
        >>> data = {"results": [
        ...     {"Ocr_BatchNo": "001", "status": "success", "Priority": 3},
        ...     {"Ocr_BatchNo": "002", "status": "success", "Priority": 1},
        ...     {"Ocr_BatchNo": "003", "status": "success", "Priority": 2},
        ...     {"Ocr_BatchNo": "001", "status": "success", "Priority": 4},
        ... ]}
        >>> result = filtering_algorithm(data)
        >>> # 只保留 Priority 最小的记录

    开发者: JJH
    创建时间: 2026-01-21
    更新时间: 2026-01-21
    """
    if not isinstance(return_dict, dict):
        return return_dict

    results = return_dict.get("results")
    if not isinstance(results, list) or not results:
        logger.warning("results 为空或不是列表，直接返回")
        return return_dict

    logger.info(f"开始处理，原始记录数: {len(results)}")

    # 如果只有一条记录，直接返回
    if len(results) == 1:
        logger.info("只有一条记录，直接返回")
        return return_dict

    # 判断 status 为 success 的个数
    success_count = sum(1 for item in results if item.get('status') == 'success')
    logger.info(f"status 为 success 的记录数: {success_count}, status 为 error 的记录数: {len(results) - success_count}")

    if success_count == 1:
        # 如果只有一个 success，删除所有 error 的记录
        filtered_results = [item for item in results if item.get('status') == 'success']
        logger.info(f"只有一个 success，过滤后保留 {len(filtered_results)} 条记录")
        return_dict["results"] = filtered_results
        return return_dict
    elif success_count > 1:
        # 如果有多个 success，进入后续的去重逻辑
        logger.info(f"有 {success_count} 个 success，进入去重逻辑")
        try:
            df = pd.DataFrame(results)

            # 筛选掉 error 的数据，只保留 success
            df_success = df[df['status'] == 'success']
            logger.info(f"筛选 success 后剩余 {len(df_success)} 条记录")

            # 找出重复的Ocr_BatchNo（出现次数 > 1）
            batch_counts = df_success['Ocr_BatchNo'].value_counts()
            duplicate_batches = batch_counts[batch_counts > 1].index.tolist()
            logger.info(f"重复的 Ocr_BatchNo: {duplicate_batches}")

            # 如果有重复的批号，进入去重逻辑
            if duplicate_batches:
                # 只保留重复的Ocr_BatchNo，删除不重复的记录
                df_filtered = df_success[df_success['Ocr_BatchNo'].isin(duplicate_batches)]
                logger.info(f"只保留重复批次后剩余 {len(df_filtered)} 条记录")

                # 对重复项只保留第一个
                df_before_drop = df_filtered.copy()
                df_filtered = df_before_drop.drop_duplicates(subset=["Ocr_BatchNo"], keep="first")
                logger.info(f"去重后剩余 {len(df_filtered)} 条记录")
            else:
                # 如果没有重复的批号，直接使用 df_success
                logger.info("没有重复的批号，使用所有 success 记录")
                df_filtered = df_success

            # 如果去重后剩余数据 > 1 条，按照 Priority 的值取最小的
            if len(df_filtered) > 1:
                if 'Priority' in df_filtered.columns:
                    df_before_sort = df_filtered.copy()
                    df_filtered = df_filtered.sort_values(by='Priority', ascending=True).head(1)
                    logger.info(f"按 Priority 排序，保留 Priority 最小的记录: {df_filtered['Priority'].values[0] if not df_filtered.empty else 'N/A'}")
                else:
                    logger.warning("Priority 字段不存在，无法按 Priority 排序")
            elif len(df_filtered) == 1:
                logger.info(f"去重后只剩一条记录: {df_filtered['Ocr_BatchNo'].values[0]}")
            else:
                logger.warning("去重后无记录, 直接返回原始数据")
                return return_dict

            df = df_filtered.fillna("")
            return_dict["results"] = df.to_dict("records")

            if not df.empty:
                logger.info(f"最终结果: {df[['Ocr_BatchNo', 'box', 'status', 'message', 'Priority']].to_dict('records')}")

        except Exception as e:
            logger.error(f"去重失败: {e}")
            return return_dict
    else:
        # 如果没有 success，直接返回
        logger.warning("没有 success 记录，直接返回原始数据")

    return return_dict




def remove_duplicates(return_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据 Ocr_BatchNo 字段去除结果中的重复记录
    
    该函数处理包含 OCR 结果的字典，根据 'Ocr_BatchNo' 字段去除重复条目。
    仅保留每个批号第一次出现的记录，避免重复处理同一批次数据。
    
    参数:
        return_dict: 包含 OCR 结果的字典，结构如下:
            - results: 字典列表，每个字典包含 OCR 数据，必须包含 'Ocr_BatchNo' 字段
    
    返回:
        去除了重复记录的结果字典。如果输入无效或不包含所需字段，则返回原始字典。
    
    示例:
        >>> data = {"results": [{"Ocr_BatchNo": "001", "box": "A"}, {"Ocr_BatchNo": "001", "box": "B"}]}
        >>> result = remove_duplicates(data)
        >>> len(result["results"])
        1
    
    开发者: JJH
    创建时间: 2025-07-21
    """
    if not isinstance(return_dict, dict):
        return return_dict

    results = return_dict.get("results")
    if not isinstance(results, list) or not results:
        return return_dict

    try:
        df = pd.DataFrame(results)
        
        if "Ocr_BatchNo" not in df.columns:
            return return_dict

        df.drop_duplicates(subset=["Ocr_BatchNo"], keep="first", inplace=True)
        df = df.fillna("")
        return_dict["results"] = df.to_dict("records")
        
        if not df.empty:
            logger.info(f"去重后结果: {df[['Ocr_BatchNo', 'box', 'status', 'message']].to_dict('records')}")
            
    except Exception as e:
        logger.error(f"去重失败: {e}")
    
    return return_dict

