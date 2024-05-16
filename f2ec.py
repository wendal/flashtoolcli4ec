#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import ectool.unpkg
import os, sys, serial.tools.list_ports, time
import logging, shutil, ectool, json, subprocess

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

ctx = {
    "serial_port" : None,
    "serial_mode" : "usb",
    "flash_type" : [],
}

def main():
    if len(sys.argv) < 2:
        print("Usage: f2ec.py [-f file] [-p port]")
        return
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-p", "--port", dest="serial_port", help="指定UART串口, 使用USB转串口时使用,使用原生USB时不需要指定")
    parser.add_option("-f", "--file", dest="flash_file", help="指定烧录文件")
    parser.add_option("-m", "--mode", dest="serial_mode", help="指定串口模式, usb/uart")
    parser.add_option("-t", "--type", dest="flash_type", help="需要烧录的固件部分,默认是全部")
    # 是否自动重启
    parser.add_option("-r", "--restart", dest="auto_restart", action="store_true", default=False, help="是否自动重启")
    # 支持指定脚本目录或者脚本scrip.bin
    parser.add_option("-s", "--script", dest="script_file", help="指定脚本文件目录,或者scrip.bin文件")
    
    parser.parse_args(sys.argv)
    
    (options,args)=parser.parse_args()

    if options.flash_file is None:
        logger.error("未指定烧录文件, 程序结束")
        sys.exit(1)
    else :
        ctx["flash_file"] = options.flash_file
        logger.info("烧录文件: %s" % ctx["flash_file"])
        if not os.path.exists(ctx["flash_file"]):
            logger.error("文件不存在: %s" % ctx["flash_file"])
            sys.exit(1)
        if not os.path.isfile(ctx["flash_file"]):
            logger.error("不是文件: %s" % ctx["flash_file"])
            sys.exit(1)
        # 首先,清除临时文件
        if os.path.exists("tmp"):
            shutil.rmtree("tmp")
        os.makedirs("tmp")
        # 复制文件到tmp目录
        if str(ctx["flash_file"]).endswith(".binpkg"):
            shutil.copyfile(ctx["flash_file"], os.path.join("tmp", "tmp.binpkg"))
            ectool.unpkg.binpkg_unpack(os.path.join("tmp", "tmp.binpkg"), os.path.join("tmp"))
        elif str(ctx["flash_file"]).endswith(".soc"):
            shutil.copyfile(ctx["flash_file"], os.path.join("tmp", "tmp.soc"))
            ectool.unpkg.binpkg_unpack(os.path.join("tmp", "tmp.soc"), os.path.join("tmp"))
        else:
            logger.error("不支持的文件格式: %s" % ctx["flash_file"])
            sys.exit(1)
    
    #指定烧录文件的话, 就加载它
    if options.script_file is not None:
        if os.path.isdir(options.script_file):
            subprocess.check_call(["luatos-lua_v2.0.0.exe", "--dump_luadb=script.bin", "--norun=1", options.script_file], shell=True)
            shutil.copyfile("script.bin", "tmp/script.bin")
        else :
            shutil.copyfile(options.script_file, "tmp/script.bin")
        # 谨慎来说, 应该更新image_info.json里的数据
        logger.info("已替换脚本区数据" + options.script_file)
        
    # 载入待烧录文件的信息
    image_info = json.load(open("tmp/image_info.json"))
    image_meta = json.load(open("tmp/image_meta.json"))
    logger.info("芯片方案: %s" % image_meta["chip"])


    for k,v in image_info.items():
        logger.info("固件内容: %-24s: %8s" % (k, v["image_type"]))

    if options.serial_port is None:
        logger.info("未指定串口, 自动搜索USB串口")
        # 搜索USB串口, vid是0x0403, pid是0x6015
        timeout = 15
        while ctx["serial_port"] == None:
            for item in serial.tools.list_ports.comports():
                if not item.pid or not item.location :
                    continue
                if not "x.2" in item.location:
                    continue
                if item.vid == 0x19d1 and item.pid == 0x0001:
                    ctx.serial_port = item.device
                    logger.info("找到串口: %s" % ctx.serial_port)
                    break
            time.sleep(1)
            timeout = timeout - 1
        if ctx["serial_port"] == None :
            logger.error("搜索超时, 未找到串口, 程序结束")
            sys.exit(1)
    else :
        ctx["serial_port"] = options.serial_port
        if options.serial_mode is None:
            ctx["serial_mode"] = "uart"
    
    
    # 更新配置文件
    # 如果是ec618, 更新配置文件
    if image_meta["chip"] == "ec618":
        if ctx["serial_mode"] == "usb" :
            shutil.copy(os.path.join("win32", "config_ec618_usb.ini"), os.path.join("win32", "config.ini"))
        else :
            shutil.copy(os.path.join("win32", "config_ec618_usb.ini"), os.path.join("win32", "config.ini"))
    else :
        if ctx["serial_mode"] == "usb" :
            shutil.copy(os.path.join("win32", "config_pkg_product_uart.ini"), os.path.join("win32", "config.ini"))
        else :
            shutil.copy(os.path.join("win32", "config_pkg_product_usb.ini"), os.path.join("win32", "config.ini"))

    # 修改配置文件, 如果有script的话
    if "script" in image_info:
        with open(os.path.join("win32", "config.ini"), 'r') as f:
            fdata = f.read()
        fdata += """
[flexfile2]
filepath = script.bin
burnaddr = 0x%08x
storage_type = ap_flash
""" % image_info["script"]["burn_addr"]
        with open(os.path.join("win32", "config.ini"), 'w') as f:
            f.write(fdata)

    # 把文件拷贝到win32目录
    for k,v in image_info.items():
        if k == "script":
            shutil.copy(os.path.join("tmp", "script.bin"), os.path.join("win32", "script.bin"))
        elif k == "ap_bootloader":
            shutil.copy(os.path.join("tmp", "ap_bootloader.bin"), os.path.join("win32", "ap_bootloader.bin"))
        elif k == "ap":
            shutil.copy(os.path.join("tmp", "ap.bin"), os.path.join("win32", "ap.bin"))
        elif k == "cp-demo-flash":
            shutil.copy(os.path.join("tmp", "cp-demo-flash.bin"), os.path.join("win32", "cp-demo-flash.bin"))
        elif v["image_type"] == "CP":
            shutil.copy(os.path.join("tmp", "cp-demo-flash.bin"), os.path.join("win32", "cp-demo-flash.bin"))
    
    # 然后就根据flash_type来选择烧录哪些内容
    if options.flash_type is None:
        ctx["flash_type"] = ["bootloader", "cp", "ap"]
        if "script" in image_info:
            ctx["flash_type"].append("script")
    else :
        ctx["flash_type"] = options.flash_type.split(",")
    logger.info("烧录类型: %s" % " ".join(ctx["flash_type"]))

    # 打印固件信息, 准备烧录
    logger.info("烧录信息如下:")
    logger.info("烧录串口 %s 模式 %s" % (ctx["serial_port"], ctx["serial_mode"]))

    cmd_tmpl = ["win32\\FlashToolCLI.exe", "--cfgfile", os.path.abspath(os.path.join("win32", "config.ini"))]
    cmd_tmpl.append("--port")
    cmd_tmpl.append(ctx["serial_port"])

    
    # 尝试链接设备
    logger.info("尝试链接设备")
    cmd = cmd_tmpl.copy()
    cmd.append("probe")
    subprocess.check_call(cmd, shell=True)

    # 已经连接上了, 后续不需要再次probe
    cmd_tmpl.append("--skipconnect")
    cmd_tmpl.append("1")

    cmd = cmd_tmpl.copy()
    cmd.append("burnbatch")
    cmd.append("--imglist")

    # 烧录bootloader
    if "bootloader" in ctx["flash_type"]:
        cmd.append("bootloader")
    # 烧录cp
    if "cp" in ctx["flash_type"]:
        cmd.append("cp_system")
    # 烧录ap
    if "ap" in ctx["flash_type"]:
        cmd.append("system")
    # 烧录script
    if "script" in ctx["flash_type"]:
        cmd.append("flexfile2")

    logger.info("执行烧录命令 " + " ".join(cmd))
    subprocess.check_call(cmd, shell=True)

    logger.info("烧录完成")
    # 执行自动重启
    if options.auto_restart:
        logger.info("执行自动重启")
        cmd = cmd_tmpl.copy()
        cmd.append("sysreset")
        subprocess.call(cmd, shell=True)

if __name__ == '__main__':
    main()