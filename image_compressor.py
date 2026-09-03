"""
图片压缩核心引擎
基于Pillow，修复了旋转、PNG覆盖等bug
"""

import os
import shutil
import threading
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass

from PIL import Image, ImageOps

from config import QUALITY_PRESETS, PNG_COMPRESS_LEVEL, SUPPORTED_EXTENSIONS
from utils import logger, get_file_size_mb, get_safe_filename, delete_file_safe


@dataclass
class CompressResult:
    """单张图片压缩结果"""
    input_path: str
    output_path: Optional[str]
    original_size: float  # MB
    compressed_size: float = 0.0  # MB
    success: bool = True
    error: Optional[str] = None

    @property
    def saved_mb(self) -> float:
        return self.original_size - self.compressed_size

    @property
    def ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100


class ImageCompressor:
    """图片压缩器（线程安全）"""

    def __init__(
        self,
        quality: str = "medium",
        output_format: str = "original",
        output_mode: str = "suffix",
        output_dir: Optional[str] = None,
        suffix: str = "_compressed",
        preserve_exif: bool = True
    ):
        self.quality = quality
        self.output_format = output_format
        self.output_mode = output_mode
        self.output_dir = output_dir
        self.suffix = suffix
        self.preserve_exif = preserve_exif

        self._stop_lock = threading.Lock()
        self._stop_requested = False
        self._results: List[CompressResult] = []
        self._total_original = 0.0
        self._total_compressed = 0.0

    @property
    def quality_value(self) -> int:
        if isinstance(self.quality, int):
            return max(1, min(100, self.quality))
        return QUALITY_PRESETS.get(self.quality, 60)

    def _compress_single(self, input_path: str) -> CompressResult:
        """压缩单张图片（修复版）"""
        original_size = get_file_size_mb(input_path)

        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"文件不存在: {input_path}")

            ext = os.path.splitext(input_path)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"不支持的图片格式: {ext}")

            # 打开图片
            image = Image.open(input_path)

            # 自动旋转（使用Pillow内置方法，修复了原bug）
            if self.preserve_exif:
                image = ImageOps.exif_transpose(image)

            # 确定输出格式和扩展名
            if self.output_format == "jpg":
                output_ext = ".jpg"
                save_format = "JPEG"
            elif self.output_format == "png":
                output_ext = ".png"
                save_format = "PNG"
            else:
                output_ext = ext
                save_format = image.format or "JPEG"

            # 生成输出路径
            output_path = get_safe_filename(
                input_path,
                suffix=self.suffix if output_ext == ext else None,
                output_dir=self.output_dir,
                mode=self.output_mode
            )
            if self.output_format in ["jpg", "png"]:
                base = os.path.splitext(output_path)[0]
                output_path = base + output_ext

            # 执行压缩保存
            if save_format in ["JPEG", "WEBP"]:
                save_kwargs = {
                    "quality": self.quality_value,
                    "optimize": True,
                    "progressive": True,
                }
                if self.preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
                    save_kwargs["exif"] = image.info["exif"]
                image.save(output_path, save_format, **save_kwargs)

            elif save_format == "PNG":
                save_kwargs = {
                    "compress_level": PNG_COMPRESS_LEVEL,
                    "optimize": True,
                }
                image.save(output_path, "PNG", **save_kwargs)
            else:
                image.save(output_path, save_format)

            image.close()

            compressed_size = get_file_size_mb(output_path)
            result = CompressResult(input_path, output_path, original_size, compressed_size)

            # 修复: 压缩后变大则删除输出文件、保留原图
            if compressed_size > original_size and self.output_mode == "overwrite":
                delete_file_safe(output_path)
                shutil.copy2(input_path, output_path)
                compressed_size = get_file_size_mb(output_path)
                result.compressed_size = compressed_size
                logger.info(f"压缩后变大，保留原图: {os.path.basename(input_path)}")
            elif compressed_size > original_size:
                # 非覆盖模式: 也提示用户
                logger.info(f"压缩后略大 ({original_size:.2f}MB → {compressed_size:.2f}MB)，建议调整质量参数")

            return result

        except Exception as e:
            result = CompressResult(input_path, None, original_size, 0.0)
            result.success = False
            result.error = str(e)
            logger.error(f"压缩失败: {input_path}, {e}")
            return result

    def compress_batch(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable[[int, int, CompressResult], None]] = None
    ) -> List[CompressResult]:
        """批量压缩（线程安全）"""
        total = len(file_paths)
        self._results = []
        self._total_original = 0.0
        self._total_compressed = 0.0

        with self._stop_lock:
            self._stop_requested = False

        for idx, path in enumerate(file_paths, 1):
            with self._stop_lock:
                if self._stop_requested:
                    logger.info("用户请求停止压缩")
                    break

            result = self._compress_single(path)
            self._results.append(result)

            if result.success:
                self._total_original += result.original_size
                self._total_compressed += result.compressed_size

            if progress_callback:
                progress_callback(idx, total, result)

        return self._results

    def stop(self):
        """请求停止压缩"""
        with self._stop_lock:
            self._stop_requested = True

    def get_summary(self) -> Dict[str, Any]:
        """获取压缩汇总"""
        success_count = sum(1 for r in self._results if r.success)
        saved = self._total_original - self._total_compressed
        ratio = (saved / self._total_original * 100) if self._total_original > 0 else 0

        return {
            "total": len(self._results),
            "success": success_count,
            "failed": len(self._results) - success_count,
            "original_total": self._total_original,
            "compressed_total": self._total_compressed,
            "saved_total": saved,
            "ratio": ratio,
        }
