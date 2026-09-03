# 图片瘦身大师

一款轻量级Android图片压缩工具，帮助您节省手机存储空间。

## 功能

- 批量图片压缩（保持尺寸，降低文件大小）
- 三档质量选择：低(30%)、中(60%)、高(85%)
- 格式转换：保持原格式 / 强制JPG / 强制PNG
- 多种保存模式：添加后缀 / 新目录 / 覆盖原图
- 实时进度显示 + 节省空间统计
- EXIF自动旋转

## 技术栈

- Python 3.10
- Kivy 2.2.0
- Pillow
- Buildozer

## GitHub Actions自动打包

1. Push代码到main分支 → 自动构建Debug APK
2. Push Tag (v*) → 自动构建Release APK并发布
3. 手动触发 → 可选择debug/release模式

## 本地测试

```bash
pip install kivy pillow
python main.py
```

## 目录结构

```
.
├── config.py              # 配置管理
├── utils.py               # 工具函数
├── image_compressor.py    # 压缩核心
├── main.py                # Kivy主程序
├── main.kv                # UI布局
├── buildozer.spec         # 打包配置
├── test_image_compressor.py  # 单元测试
├── .github/workflows/build.yml  # CI/CD
└── docs/
    ├── 自查报告.md
    └── 签名配置说明.md
```
