import argparse
import sys
import asyncio
import logging
import logging.handlers
from asyncio import subprocess
import os
import shlex
import signal

# file_rotate = logging.handlers.TimedRotatingFileHandler('/var/log/wfb/svp_wfb.log', when='midnight', interval=1, backupCount=10)
console = logging.StreamHandler()

logger = logging.getLogger('main')
logging.basicConfig(level='DEBUG', format="%(asctime)s %(levelname)-8s %(name)s: %(message)s", handlers=[console])





class DummyProto:

    def connection_made(self, transport):
        pass

    def datagram_received(self, data, addr):
        pass

    def error_received(self, exc):
        pass

    def connection_lost(self, exc):
        pass


class V4lStream:
    """
    gst-launch-1.0 -v v4l2src device=/dev/video2 num-buffers=-1 ! "video/x-raw,format=(string)UYVY, width=(int)1920, height=(int)1080,framerate=(fraction)30/1" ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=4000000" ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5602 sync=false
    gst-launch-1.0 -v v4l2src device=/dev/video0 num-buffers=-1 ! videoconvert ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=2000000" ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5603 sync=false
    """

    def __init__(self, device, pipeline):
        self.device = device
        self.pipeline = pipeline

        self.running = False
        self.proc = None
        self.handle_stdout_task = None
        self.handle_stderr_task = None

    async def start(self):
        self.running = True

        device_string = f"v4l2src device={self.device} num-buffers=-1 "
        args = shlex.split(device_string + self.pipeline)
        logger.info("V4lStream [%s] start pipeline: %s", self.device, " ".join(args))
        self.proc = await asyncio.create_subprocess_exec(
            'gst-launch-1.0',
            *args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        self.handle_stdout_task = asyncio.create_task(self.handle_stdout())
        self.handle_stderr_task = asyncio.create_task(self.handle_stderr())

        resturncode = await self.proc.wait()
        logger.info("V4lStream [%s] proc finished with code: %s", self.device, resturncode)

    async def stop(self):
        logger.info("V4lStream [%s] Stopping subprocesses", self.device)
        self.proc.terminate()
        self.running = False
        self.handle_stdout_task and self.handle_stdout_task.cancel()
        self.handle_stderr_task and self.handle_stderr_task.cancel()
        logger.info("V4lStream [%s] Stopped", self.device)

    async def handle_stderr(self):
        logger.info("V4lStream [%s] starting handle_stderr", self.device)
        while self.running and self.proc.returncode is None:
            raw_data = await self.proc.stderr.readline()
            raw_data = raw_data.decode()
            logger.info("V4lStream [%s] STDERR: %s", self.device, raw_data)

    async def handle_stdout(self):
        logger.info("V4lStream [%s] starting handle_stdout", self.device)
        while self.running and self.proc.returncode is None:
            raw_data = await self.proc.stderr.readline()
            raw_data = raw_data.decode()
            logger.info("V4lStream [%s] STDERR: %s", self.device, raw_data)


class Channel:
    """
    WFB Channel
    """

    def __init__(self, name):
        self.name = name

        self.rx_proc = None
        self.tx_proc = None
        self.stat_transport = None
        self.rssi = -100

        self.running = False

    async def start(self):
        self.running = True
        # await self.start_rx()
        await self.start_tx()

        loop = asyncio.get_running_loop()
        self.stat_transport, _ = await loop.create_datagram_endpoint(
            DummyProto,
            remote_addr=('127.0.0.1', 5800))

        self.report_task = asyncio.create_task(self.report())
        self.errors_task = asyncio.create_task(self.watch_errors())
        # asyncio.create_task(self.watch_errors())

    async def start_rx(self):
        """

        """
        rx_args = ['-K', f'/etc/{key}.key', '-p', f'{rx_port}', '-u', f'{udp_out}', '-k', k, '-n', n, iface]

        logger.info("Chan [%s] starting RX subprocess: %s", self.name, ' '.join(rx_args))
        self.rx_proc = await asyncio.create_subprocess_exec(
            'wfb_rx',
            *rx_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    async def start_tx(self):
        """
        /usr/bin/wfb_tx -p 2 -u 5603 -K /etc/drone.key -B 20 -G long -S 1 -L 1 -M 1 -k 8 -n 12 -T 0 -i 7669206 wlan0
        """
        tx_args = "-p 2 -u 5603 -K /etc/drone.key -B 20 -G long -S 1 -L 1 -M 1 -k 8 -n 12 -T 0 -i 7669206 wlan0".split()
        logger.info("Chan [%s] starting TX subprocess: %s", self.name, ' '.join(tx_args))
        self.tx_proc = await asyncio.create_subprocess_exec(
            'wfb_tx',
            *tx_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

    async def report(self):
        logger.info("Chan [%s] starting report task", self.name)
        loop = asyncio.get_running_loop()
        while self.running:
            # wd = asyncio.create_task(self.restart_rx(2))
            raw_data = await self.rx_proc.stdout.readline()
            raw_data = raw_data.decode()
            logger.info("RX STDOUT: %s", raw_data)

    async def watch_errors(self):
        logger.info("Chan [%s] starting watch_errors", self.name)
        while self.running:
            raw_data = await self.rx_proc.stderr.readline()
            raw_data = raw_data.decode()
            logger.info("Chan %s RX ERROR: %s", self.name, raw_data)

    async def stop(self):
        logger.info("Chan [%s] Stopping subprocesses", self.name)
        self.running = False
        self.rx_proc.terminate()
        self.tx_proc.terminate()
        self.report_task.cancel()
        self.errors_task.cancel()


async def main(args):


    thermal_chan = Channel(
        'thermal_tx'
    )

    main_camera = V4lStream(
        '/dev/video2',
        pipeline = '! "video/x-raw,format=(string)UYVY, width=(int)1920, height=(int)1080,framerate=(fraction)30/1" ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=4000000" ! "video/x-h264, profile=high, level=(string)4" ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5602 sync=false'
    )

    thermal_camera = V4lStream(
        '/dev/video0',
        pipeline='! videoconvert ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=1000000" ! "video/x-h264, profile=high, level=(string)4" ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5603 sync=false'
    )

    # mav_proxy = MavProxy(args.mode, args.mavlink, telem_chan)
    async def shutdown(s, loop):
        logger.info("Shutdown (signal %s)", s)
        await main_camera.stop()


    loop = asyncio.get_running_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    # await thermal_chan.start()
   
    # await thermal_camera.start()

    tasks = [
        asyncio.create_task(thermal_chan.start()),
        asyncio.create_task(main_camera.start()),
        asyncio.create_task(thermal_camera.start()),
    ]
    await asyncio.gather(*tasks)
    logger.info("Main exit")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SVP WFB Launcher')

    # parser.add_argument('--mode', type=str, required=True, help='Instance mode - ground or air')
    # parser.add_argument('--fec', type=str, required=True, help='fec params k/n (8/12 default, 1/2 for telemetry)')
    # parser.add_argument('--mavlink', type=str, required=True, help='MAVLink endpoint - GCS for ground, mavrouter for air')
    # parser.add_argument('--freq', type=int, default=2432, help='WiFi frequency default 2432')
    # parser.add_argument('--txpower', type=int, default=58, help='TX power (20-63) default  58')
    # parser.add_argument('--bitrate', type=float, default=11, help='bitrate (2, 5.5, 11) default 11')
    # parser.add_argument('iface', type=str, help='Wlan iface to use')

    args = parser.parse_args()

    # ath9k_configure(args.iface, args.freq, args.txpower, args.bitrate)

    # try:
    asyncio.run(main(args))
    # except KeyboardInterrupt:
        # print('Stopping all')
    # finally:
    print('FIN!')