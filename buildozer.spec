[app]
title = 图片瘦身大师
package.name = imageslimmer
package.domain = com.yourcompany
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy==2.2.0,pillow,android
orientation = portrait
fullscreen = 0

[android]
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 30
android.minapi = 21
android.sdk = 30
android.ndk = 23c
android.ndk_api = 21
android.enable_androidx = True
android.accept_sdk_license = True
android.debug = 1

[buildozer]
log_level = 2
warn_on_root = 0
