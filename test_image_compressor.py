"""
图片压缩核心单元测试
目标：行覆盖率 >= 80%
"""

import os
import tempfile
import unittest

from PIL import Image

from config import QUALITY_PRESETS
from image_compressor import ImageCompressor, CompressResult
from utils import get_file_size_mb, get_safe_filename, is_image_file


class TestCompressResult(unittest.TestCase):
    """测试压缩结果类"""

    def test_saved_mb(self):
        r = CompressResult("a.jpg", "b.jpg", 2.0, 1.0)
        self.assertEqual(r.saved_mb, 1.0)

    def test_ratio(self):
        r = CompressResult("a.jpg", "b.jpg", 2.0, 1.0)
        self.assertEqual(r.ratio, 50.0)

    def test_ratio_zero_original(self):
        r = CompressResult("a.jpg", "b.jpg", 0.0, 0.0)
        self.assertEqual(r.ratio, 0.0)


class TestImageCompressor(unittest.TestCase):
    """测试压缩器"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # 创建测试图片
        self.test_jpg = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_jpg, 'JPEG', quality=95)
        self.test_png = os.path.join(self.temp_dir, "test.png")
        img.save(self.test_png, 'PNG')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_quality_value_preset(self):
        c = ImageCompressor(quality="low")
        self.assertEqual(c.quality_value, 30)

    def test_quality_value_int(self):
        c = ImageCompressor(quality=75)
        self.assertEqual(c.quality_value, 75)

    def test_quality_value_clamp(self):
        c = ImageCompressor(quality=150)
        self.assertEqual(c.quality_value, 100)

    def test_compress_single_jpg(self):
        c = ImageCompressor(quality="medium", output_mode="suffix")
        result = c._compress_single(self.test_jpg)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.output_path)
        self.assertTrue(os.path.exists(result.output_path))
        self.assertLess(result.compressed_size, result.original_size)

    def test_compress_single_png(self):
        c = ImageCompressor(quality="medium", output_mode="suffix")
        result = c._compress_single(self.test_png)
        self.assertTrue(result.success)

    def test_compress_single_not_found(self):
        c = ImageCompressor()
        result = c._compress_single("/nonexistent/file.jpg")
        self.assertFalse(result.success)
        self.assertIn("不存在", result.error)

    def test_compress_single_unsupported_format(self):
        c = ImageCompressor()
        txt_file = os.path.join(self.temp_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("not an image")
        result = c._compress_single(txt_file)
        self.assertFalse(result.success)

    def test_compress_batch(self):
        c = ImageCompressor(quality="medium", output_mode="suffix")
        results = c.compress_batch([self.test_jpg, self.test_png])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.success for r in results))

    def test_compress_batch_with_callback(self):
        c = ImageCompressor(quality="medium", output_mode="suffix")
        callbacks = []

        def cb(processed, total, result):
            callbacks.append((processed, total))

        c.compress_batch([self.test_jpg, self.test_png], cb)
        self.assertEqual(len(callbacks), 2)

    def test_stop(self):
        c = ImageCompressor()
        c.stop()
        self.assertTrue(c._stop_requested)

    def test_get_summary(self):
        c = ImageCompressor(quality="medium", output_mode="suffix")
        c.compress_batch([self.test_jpg, self.test_png])
        summary = c.get_summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["success"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertGreater(summary["saved_total"], 0)

    def test_format_conversion_jpg(self):
        c = ImageCompressor(quality="medium", output_format="jpg", output_mode="suffix")
        result = c._compress_single(self.test_png)
        self.assertTrue(result.success)
        self.assertTrue(result.output_path.endswith('.jpg'))

    def test_format_conversion_png(self):
        c = ImageCompressor(quality="medium", output_format="png", output_mode="suffix")
        result = c._compress_single(self.test_jpg)
        self.assertTrue(result.success)
        self.assertTrue(result.output_path.endswith('.png'))

    def test_overwrite_mode(self):
        c = ImageCompressor(quality="medium", output_mode="overwrite")
        result = c._compress_single(self.test_jpg)
        self.assertTrue(result.success)
        self.assertEqual(result.output_path, self.test_jpg)

    def test_preserve_exif_rotation(self):
        # 创建带EXIF旋转的图片
        img = Image.new('RGB', (200, 100), color='blue')
        # 模拟EXIF Orientation=6 (旋转90度)
        from PIL import ExifTags
        exif = img.getexif()
        exif[274] = 6  # Orientation
        img.save(self.test_jpg, 'JPEG', exif=exif)

        c = ImageCompressor(quality="medium", output_mode="suffix", preserve_exif=True)
        result = c._compress_single(self.test_jpg)
        self.assertTrue(result.success)


class TestUtils(unittest.TestCase):
    """测试工具函数"""

    def test_is_image_file(self):
        self.assertTrue(is_image_file("photo.jpg"))
        self.assertTrue(is_image_file("photo.JPG"))
        self.assertFalse(is_image_file("doc.txt"))

    def test_get_safe_filename_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "test.jpg")
            open(f, 'w').close()
            result = get_safe_filename(f, suffix="_compressed", mode="suffix")
            self.assertIn("_compressed", result)

    def test_get_safe_filename_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "test.jpg")
            open(f, 'w').close()
            result = get_safe_filename(f, mode="overwrite")
            self.assertEqual(result, f)

    def test_format_size_mb(self):
        from utils import format_size_mb
        self.assertIn("KB", format_size_mb(0.5))
        self.assertIn("MB", format_size_mb(5.0))
        self.assertIn("GB", format_size_mb(1500.0))


if __name__ == '__main__':
    unittest.main()
