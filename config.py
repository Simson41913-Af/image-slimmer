"""
图片瘦身大师 - 配置管理
所有可调参数集中在此，便于维护
"""

# ============ 压缩质量档位 ============
# JPG: 1-100, 数值越高画质越好、文件越大
QUALITY_PRESETS = {
    "low": 30,
    "medium": 60,  # 默认
    "high": 85,
}

# PNG: 0-9, 数值越高压缩率越大、速度越慢
PNG_COMPRESS_LEVEL = 6

# ============ 默认设置 ============
DEFAULT_QUALITY = "medium"
DEFAULT_OUTPUT_SUFFIX = "_compressed"
DEFAULT_BACKUP_ENABLED = True
DEFAULT_FORMAT = "original"  # original / jpg / png
DEFAULT_OVERWRITE_MODE = "suffix"  # suffix / newdir / overwrite

# ============ 支持的文件类型 ============
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

# ============ 应用信息 ============
APP_NAME = "图片瘦身大师"
APP_VERSION = "1.0.0"

# ============ 日志 ============
LOG_ENABLED = True
LOG_LEVEL = "INFO"
