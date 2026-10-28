@echo off
chcp 65001 >nul
setlocal
:: 把 sqweb_offline\site 推到已连接手机/模拟器的 App 私有目录
:: 用法: push_site.bat [adb路径] [site路径]

set ADB=%~1
if "%ADB%"=="" set ADB=F:\android-sdk\platform-tools\adb.exe

set SITE=%~2
if "%SITE%"=="" set SITE=%~dp0..\..\sqweb_offline\site

if not exist "%ADB%" (
  echo [x] 找不到 adb: %ADB%
  echo     可以手动指定: push_site.bat "C:\path\to\adb.exe"
  pause & exit /b 1
)
if not exist "%SITE%\index.html" (
  echo [x] 找不到素材目录: %SITE%
  pause & exit /b 1
)

echo [*] 设备列表:
"%ADB%" devices
echo [*] 准备目录...
"%ADB%" shell mkdir -p /sdcard/Android/data/io.hmzztwj.konofanweb/files/site
echo [*] 开始推送 %SITE%  (约 11 GB，视传输速度 3~10 分钟)
"%ADB%" push "%SITE%\." /sdcard/Android/data/io.hmzztwj.konofanweb/files/site/
echo [*] 完成，手机上打开「このファン Web」即可
pause
