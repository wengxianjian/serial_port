
python build.py


安装依赖: pip install pyserial PyQt5
python运行：python Serial_Port_Tool_v1.1.py

在CMD编译成可执行文件：pyinstaller --onefile --windowed Serial_Port_Tool_v1.1.py

可执行文件路径：dist



===============================================================
pyinstaller的使用：

基本语法：
pyinstaller options myscript.py

常用的可选参数如下：
--onefile 将结果打包成一个可执行文件
--onedir 将所有结果打包到一个文件夹中，该文件夹包括一个可执行文件和可执行文件执行时需要的依赖文件（默认）
--paths=DIR 设置导入路径
--distpath=DIR 设置将打包的结果文件放置的路径
--specpath=DIR 设置将spec文件放置的路径
--windowed 使用windows子系统执行，不会打开命令行（只对windows有效）
--nowindowed 使用控制台子系统执行（默认）（只对windows有效）
--icon=<FILE.ICO> 将file.ico添加为可执行文件的资源(只对windows有效）



