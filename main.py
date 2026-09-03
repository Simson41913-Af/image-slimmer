"""
图片瘦身大师 - Android Kivy应用
主程序入口（含完整文件选择器）
"""

import os
import threading
from typing import List, Optional
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.button import Button

from config import APP_NAME, APP_VERSION, DEFAULT_QUALITY
from image_compressor import ImageCompressor, CompressResult
from utils import (
    check_permissions_android,
    request_storage_permissions_android11,
    scan_images_in_folder,
    get_file_size_mb,
    format_size_mb,
    logger,
)


class MainController(BoxLayout):
    """主界面控制器"""

    # UI绑定属性
    status_text = StringProperty("就绪")
    progress_value = NumericProperty(0)
    progress_text = StringProperty("0 / 0")
    saved_text = StringProperty("已节省: 0 MB")
    image_count = NumericProperty(0)
    selected_folder = StringProperty("")
    total_size_mb = NumericProperty(0.0)

    # 压缩设置
    quality = StringProperty(DEFAULT_QUALITY)
    output_format = StringProperty("original")
    output_mode = StringProperty("suffix")

    # 状态
    is_compressing = BooleanProperty(False)
    is_scanning = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_paths: List[str] = []
        self.compressor: Optional[ImageCompressor] = None
        self.compress_thread: Optional[threading.Thread] = None

        # Android权限检查
        if platform == "android":
            Clock.schedule_once(self._check_permissions, 1)

    def _check_permissions(self, dt):
        """检查并请求权限"""
        if not check_permissions_android():
            self.status_text = "请求存储权限..."
            request_storage_permissions_android11()
            Clock.schedule_once(self._check_permissions, 2)
        else:
            self.status_text = "权限已获取"

    # ============ 文件选择器（完整实现） ============
    def select_images(self):
        """选择单张/多张图片"""
        if self.is_compressing:
            return
        self._show_file_chooser(multiple=True)

    def select_folder(self):
        """选择文件夹"""
        if self.is_compressing:
            return
        self._show_file_chooser(multiple=False, dirselect=True)

    def _show_file_chooser(self, multiple=False, dirselect=False):
        """显示文件选择器（跨平台）"""
        if platform == "android":
            try:
                from android.storage import primary_external_storage_path
                default_path = primary_external_storage_path()
            except Exception:
                default_path = "/storage/emulated/0"
        else:
            default_path = os.path.expanduser("~/Pictures")

        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(
            path=default_path,
            dirselect=dirselect,
            size_hint_y=0.9
        )
        if multiple:
            filechooser.multiselect = True
        content.add_widget(filechooser)

        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        cancel_btn = Button(text="取消")
        select_btn = Button(text="选择")
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        content.add_widget(btn_layout)

        title = "选择图片" if multiple else ("选择文件夹" if dirselect else "选择")
        popup = Popup(title=title, content=content, size_hint=(0.9, 0.9), auto_dismiss=False)

        def on_select(instance):
            if filechooser.selection:
                if dirselect:
                    folder_path = filechooser.selection[0]
                    if os.path.isdir(folder_path):
                        popup.dismiss()
                        self._scan_folder(folder_path)
                    else:
                        self.status_text = "请选择文件夹"
                else:
                    popup.dismiss()
                    self._on_images_selected(filechooser.selection)
            else:
                self.status_text = "未选择任何文件"

        def on_cancel(instance):
            popup.dismiss()

        cancel_btn.bind(on_press=on_cancel)
        select_btn.bind(on_press=on_select)
        popup.open()

    def _scan_folder(self, folder_path: str):
        """扫描文件夹（异步）"""
        if not os.path.exists(folder_path):
            self.status_text = "文件夹不存在"
            return

        self.is_scanning = True
        self.status_text = f"扫描中..."
        self.selected_folder = folder_path

        def scan_worker():
            images = scan_images_in_folder(folder_path, recursive=True)
            Clock.schedule_once(lambda dt: self._on_scan_complete(images))

        threading.Thread(target=scan_worker, daemon=True).start()

    def _on_images_selected(self, paths: List[str]):
        """图片选择完成"""
        valid_paths = [p for p in paths if os.path.exists(p)]
        self.image_paths = valid_paths
        self.image_count = len(valid_paths)

        if valid_paths:
            total_size = sum(get_file_size_mb(p) for p in valid_paths)
            self.total_size_mb = total_size
            self.status_text = f"找到 {len(valid_paths)} 张图片，共 {format_size_mb(total_size)}"
        else:
            self.status_text = "未找到有效图片"
            self.image_count = 0

    def _on_scan_complete(self, images: List[str]):
        """扫描完成回调"""
        self.is_scanning = False
        self._on_images_selected(images)

    # ============ 压缩功能 ============
    def start_compress(self):
        """开始压缩"""
        if self.is_compressing or not self.image_paths:
            if not self.image_paths:
                self.status_text = "请先选择图片"
            return

        self.progress_value = 0
        self.progress_text = "0 / 0"
        self.saved_text = "已节省: 0 MB"
        self.is_compressing = True
        self.status_text = "压缩中..."

        self.compressor = ImageCompressor(
            quality=self.quality,
            output_format=self.output_format,
            output_mode=self.output_mode,
            suffix="_compressed",
        )

        self.compress_thread = threading.Thread(target=self._compress_worker, daemon=True)
        self.compress_thread.start()

    def _compress_worker(self):
        """压缩工作线程"""
        def progress_callback(processed: int, total: int, result: CompressResult):
            Clock.schedule_once(lambda dt: self._on_progress(processed, total, result))

        self.compressor.compress_batch(self.image_paths, progress_callback)
        summary = self.compressor.get_summary()
        Clock.schedule_once(lambda dt: self._on_compress_complete(summary))

    def _on_progress(self, processed: int, total: int, result: CompressResult):
        """进度更新"""
        self.progress_value = (processed / total) * 100 if total > 0 else 0
        self.progress_text = f"{processed} / {total}"
        if result.success and result.saved_mb > 0:
            self.saved_text = f"已节省: {format_size_mb(result.saved_mb)}"
        self.status_text = f"压缩中... {processed}/{total}"

    def _on_compress_complete(self, summary: dict):
        """压缩完成"""
        self.is_compressing = False
        self.progress_value = 100

        saved = summary["saved_total"]
        if summary["failed"] > 0:
            self.status_text = (
                f"完成! {summary['success']}/{summary['total']} 张, "
                f"失败 {summary['failed']} 张, 节省 {format_size_mb(saved)}"
            )
        else:
            self.status_text = f"压缩完成! 共 {summary['total']} 张, 节省 {format_size_mb(saved)}"
        self.saved_text = f"已节省: {format_size_mb(saved)}"

    def stop_compress(self):
        """停止压缩"""
        if self.compressor:
            self.compressor.stop()
            self.status_text = "正在停止..."

    def clear_selection(self):
        """清空选择"""
        if self.is_compressing:
            return
        self.image_paths = []
        self.image_count = 0
        self.selected_folder = ""
        self.total_size_mb = 0.0
        self.progress_value = 0
        self.progress_text = "0 / 0"
        self.saved_text = "已节省: 0 MB"
        self.status_text = "已清空"


class ImageCompressorApp(App):
    """主应用"""

    def build(self):
        self.title = f"{APP_NAME} v{APP_VERSION}"
        return MainController()

    def on_pause(self):
        return True


if __name__ == "__main__":
    ImageCompressorApp().run()
