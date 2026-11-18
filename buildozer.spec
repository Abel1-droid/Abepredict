[app]
title = Abepredict
package.name = abepredict
package.domain = com.abel1droid
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,csv,json
source.exclude_dirs = .git,.github,__pycache__,data,backups,bin,.buildozer
version = 0.1.0
requirements = python3==3.14.2,hostpython3==3.14.2,kivy,requests

orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 36
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk = 29
p4a.branch = develop
p4a.bootstrap = sdl2
