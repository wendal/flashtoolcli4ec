
#!/usr/bin/python3
# -*- coding: UTF-8 -*-

"""
用于免boot刷EC618脚本的脚本
"""

import sys, serial.tools.list_ports, time
import logging, traceback, os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

def ec618_check_reply(burncom, wanted=None, logger=None):
    t1 = time.time()
    reply = burncom.read_until(wanted)
    t2 = time.time()
    #logger.info("耗时 " + str(t2 - t1))
    if not reply:
        logger.info("没读到数据")
        return
    bytes_data = []
    for index in range(len(reply)):
        if reply[index] < 128 and reply[index] > 0:
            bytes_data.append(reply[index])
    if len(bytes_data) == 0:
        return
    data = "".join(map(chr, bytes_data))
    if wanted and "OK " + wanted in data:
        return True
    else:
        logger.info("读到的数据" + str(data))


def ec618_burn_fast(item, bin_path):

    ec618_soc_log = item.device

    # 开始传输过程
    burncom = serial.Serial(ec618_soc_log, baudrate=3000000, timeout=0.2)
    burncom.write_timeout = 1

    # 先关日志
    # burncom.write(b'\x7e\x00\x50\x7e')
    # if not ec618_check_reply(burncom, "LOG OFF", logger) :
    #     logger.info("没有读到OK LOG OFF, 设备上的固件不支持快速下载")
    #     return False

    # 初始化
    logger.info("下载开始(单脚本免Boot模式)")
    # send_evt.send_percent(0)
    burncom.write(b'\x7e\x00\x30\x7e')
    #reply = burncom.read(102400)
    burncom.timeout = 1  # 初始化需要擦除flash,可以慢些
    if not ec618_check_reply(burncom, "FOTA INIT", logger):
        logger.info("没有读到FOTA INIT, 无法继续快速下载")
        return False
    burncom.timeout = 0.2

    # bin_path = "test\\gpio.bin"
    # bin_path = "test\\mobile.bin"
    fsize = None
    fcount = 0
    with open(bin_path, "rb") as f:
        fsize = len(f.read())
        logger.info("文件大小: " + str(fsize))

    with open(bin_path, "rb") as f:
        while 1:
            data = f.read(4096)
            if not data or len(data) == 0:
                break
            slen = len(data)
            fcount += slen
            if fsize == fcount:  # 最后一个包会慢些
                burncom.timeout = 1
            else:  # 其他包 0.1秒够了
                burncom.timeout = 0.1
            data = b'\x7e\x00\x31\x7e' + (slen).to_bytes(2, byteorder="big") + data
            #logger.info("待发送的数据的长度" + str(len(data)))
            burncom.write(data)
            if not ec618_check_reply(burncom, "FOTA WRITE", logger):
                logger.info("写入数据失败,那就是失败了")
                try:
                    burncom.close()
                except:
                    pass
                return
            else:
                logger.info("下载百分比: {}".format(int(fcount / fsize * 100)))
    # 结束数据传输
    logger.info(">>>>>>>>>>>>>>>>>>> send done")
    burncom.write(b'\x7e\x00\x32\x7e')
    burncom.timeout = 0.1
    if ec618_check_reply(burncom, "FOTA DONE", logger):
        # 设备重启
        burncom.write(b'\x7e\x00\x01\x7e')
        time.sleep(0.1)
        try:
            burncom.close()
        except:
            pass
        return True
    else:
        logger.info("没输出OK FOTA DONE")


def main():
    burncom = None
    try:
        for item in serial.tools.list_ports.comports():
            if not item.pid or not item.location:
                continue
            if item.vid != 0x19d1 or item.pid != 0x0001 or not "x.2" in item.location:
                continue
            logger.info("找到ec618的soc log口,尝试快速下载")
            #logger.info("尝试快速下载")
            application_path = os.path.dirname(sys.executable)
            upath = "output.sota"
            if hasattr(sys, "_MEIPASS") :
                upath = os.path.join(sys._MEIPASS, "data", "output.sota")
            if os.path.exists("output.sota"):
                upath = "output.sota"
            if ec618_burn_fast(item, upath):
                logger.info("快速下载完成, 设备响应OK, 退出下载")
                logger.info("快速下载已完成")
                return True, True
            else:
                logger.info("快速下载失败!!")
                sys.exit(1)
            break
    except:
        logger.info("快速下载模式失败 " + traceback.format_exc())
    logger.error("没有找到可供下载的COM设备")

if __name__ == "__main__":
    main()
