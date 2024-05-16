# flashtoolcli4ec
把移芯方案的FlashToolCLI封装成脚本调用

因为原生工具只支持windows, 其他平台可以参考 ectool2py 但功能有限

## 命令参数介绍

```
-f 指定待刷入的文件,必须是.binpkg或者.soc文件, 如果是LuatOS固件且打算刷脚本,就必须是.soc文件
-r 指定是否需要重启, 默认不重启
-p 指定串口端口, 默认COM46
-m 指定flash模式, 默认usb,可选uart
-s 脚本文件的文件夹,必须是\结尾, 也可以是script.bin文件的绝对路径
```

## 刷机条件

要先让模块进入刷机然后再刷, 否则会报错, 具体操作是 上拉BOOT, 然后模块上电(长按开机键或者复位键), 释放BOOT

## 用法

刷binpkg量产文件

```
python f2ec.py -f binpkg -p COM46 -m usb -r
```

刷LuatOS量产文件

```
python f2ec.py -f gpiodemo.soc -p COM46 -m usb
```

刷LuatOS量产文件,但替换脚本内容

```
python f2ec.py -f gpiodemo.soc -p COM46 -m usb --script=D:\github\LuatOS\demo\gpio\gpio\ -r
```


刷LuatOS量产文件,但替换脚本内容, 且只刷脚本

```
python f2ec.py -f gpiodemo.soc -p COM46 -m usb --script=D:\github\LuatOS\demo\gpio\gpio\ -r -t script
```

刷LuatOS非量产固件,且只刷脚本

```
暂不支持, 用一种方式吧
```


## 授权协议

[MIT License](LICENSE)
