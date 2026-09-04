"""
工具函数模块
权限管理（适配Android 11+ Scoped Storage）、路径处理、文件扫描
"""

import os
import logging
from typing import List, Optional

from config import SUPPORTED_EXTENSIONS


# ============ 日志 ============
def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """配置日志记录器"""
    log = logging.getLogger(name)
    log.setLevel(level)
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        log.addHandler(handler)
    return log


logger = setup_logger()


# ============ Android权限（适配API 30+） ============
def request_storage_permissions_android11() -> bool:
    """
    适配Android 11+ (API 30+) 的Scoped Storage
    使用 MANAGE_EXTERNAL_STORAGE 或 SAF (Storage Access Framework)
    """
    try:
        from android.permissions import request_permissions, Permission
        from android import api_version

        if api_version >= 30:
            # Android 11+: 请求 MANAGE_EXTERNAL_STORAGE
            # 注意: 用户需要在系统设置中手动开启"所有文件访问权限"
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.MANAGE_EXTERNAL_STORAGE,
            ]
        else:
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ]

        request_permissions(permissions)
        return True
    except Exception as e:
        logger.error(f"权限请求失败: {e}")
        return False


def check_permissions_android() -> bool:
    """检查存储权限是否已授予"""
    try:
        from android.permissions import check_permission, Permission
        from android import api_version

        read_granted = check_permission(Permission.READ_EXTERNAL_STORAGE)
        write_granted = check_permission(Permission.WRITE_EXTERNAL_STORAGE)

        if api_version >= 30:
            manage_granted = check_permission(Permission.MANAGE_EXTERNAL_STORAGE)
            return read_granted and write_granted and manage_granted
        return read_granted and write_granted
    except Exception:
        return False


# ============ 文件路径工具 ============
def get_safe_filename(
    filepath: str,
    suffix: Optional[str] = None,
    output_dir: Optional[str] = None,
    mode: str = "suffix"
) -> str:
    """
    生成安全的输出文件路径（自动处理重名）
    """
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    name, ext = os.path.splitext(basename)

    if mode == "overwrite":
        return filepath

    if mode == "newdir" and output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, basename)

    # 默认: 添加后缀
    suffix = suffix or "_compressed"
    new_basename = f"{name}{suffix}{ext}"
    new_path = os.path.join(dirname, new_basename)

    # 自动处理重名
    counter = 1
    while os.path.exists(new_path):
        new_basename = f"{name}{suffix}_{counter}{ext}"
        new_path = os.path.join(dirname, new_basename)
        counter += 1
    return new_path


def is_image_file(filename: str) -> bool:
    """判断是否为支持的图片文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_size_mb(filepath: str) -> float:
    """获取文件大小（MB）"""
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except Exception:
        return 0.0


def format_size_mb(size_mb: float) -> str:
    """格式化大小显示"""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f}KB"
    elif size_mb < 1024:
        return f"{size_mb:.1f}MB"
    else:
        return f"{size_mb / 1024:.2f}GB"


def scan_images_in_folder(folder_path: str, recursive: bool = True) -> List[str]:
    """扫描文件夹中的所有图片"""
    image_files: List[str] = []
    if not os.path.exists(folder_path):
        logger.warning(f"文件夹不存在: {folder_path}")
        return image_files

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if is_image_file(filename):
                image_files.append(os.path.join(root, filename))
        if not recursive:
            break

    logger.info(f"扫描完成，找到 {len(image_files)} 张图片")
    return image_files


def delete_file_safe(filepath: str) -> bool:
    """安全删除文件（吞掉异常）"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        logger.warning(f"删除文件失败: {filepath}, {e}")
    return False
