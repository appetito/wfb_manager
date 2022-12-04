import argparse
import sys
import asyncio
import logging
import logging.handlers
from asyncio import subprocess
import os
import shlex
import signal


from config import Settings

# file_rotate = logging.handlers.TimedRotatingFileHandler('/var/log/wfb/svp_wfb.log', when='midnight', interval=1, backupCount=10)
console = logging.StreamHandler()

logger = logging.getLogger('main')
logging.basicConfig(level='DEBUG', format="%(asctime)s %(levelname)-8s %(name)s: %(message)s", handlers=[console])



# class SerialProto(asyncio.Protocol):

#     def __init__(self, service):
#         self.service = service

#     def connection_made(self, transport):
#         self.transport = transport
#         logging.debug("Port opened: %s", transport)
#         transport.serial.rts = False
#         self.service.on_connected(transport)

#     def data_received(self, data):
#         self.service.on_data_received(data)

#     def connection_lost(self, exc):
#         logging.debug("Port closed: %s", exc)
#         asyncio.get_event_loop().stop()


# class Service:

#     def __init__(self):
#         self.mav = mavlink.MAVLink(None, srcSystem=1, srcComponent=100)
#         self.cam = Cam()
#         self.state = State()

#     def on_connected(self, transport):
#         self.mav.file = transport

#     def init_streams(self):
#         self.mav.command_long_send(
#             target_system=1,
#             target_component=1,
#             command=mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
#             confirmation=0,
#             param1=mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
#             param2=200000,
#             param3=0,
#             param4=0,
#             param5=0,
#             param6=0,
#             param7=0,
#             force_mavlink1=False
#         )

#     async def run(self):
#         self.init_streams()
#         await self.cam.start()
#         await asyncio.sleep(1)

#         while True:
#             await asyncio.sleep(1)

#     def on_data_received(self, data):
#         try:
#             msgs = self.mav.parse_buffer(data) or []
#         except Exception as exc:
#             logging.info("MAVLink parse error: %s", exc)
#             msgs = []
#         for msg in msgs:
#             asyncio.create_task(self.handle_message(msg))

#     async def handle_message(self, msg):
#         #print(">>>", msg.get_srcSystem(), msg.get_srcComponent(), msg.to_dict())
#         if msg.get_msgId() == mavlink.MAVLINK_MSG_ID_COMMAND_LONG:
#             if msg.command == 200:
#                 return
#             logging.info("COMMAND_LONG: %s", msg.to_dict())
#             if msg.command == mavlink.MAV_CMD_DO_DIGICAM_CONTROL and msg.param5 == 1:
#                 logging.info("SHOOT BY DO_DIGICAM_CONTROL")
#                 shoot_state = dataclasses.replace(self.state)
#                 self.mav.command_ack_send(2000, mavlink.MAV_RESULT_IN_PROGRESS)
#                 await self.cam.shoot(shoot_state)
#                 self.mav.command_ack_send(2000, mavlink.MAV_RESULT_ACCEPTED)
#                 self.mav.camera_image_captured_send(
#                     0,                # time_boot_ms              : Timestamp (time since system boot). [ms] (type:uint32_t)
#                     0,                # time_utc                  : Timestamp (time since UNIX epoch) in UTC. 0 for unknown. [us] (type:uint64_t)
#                     1,                # camera_id                 : Camera ID (1 for first, 2 for second, etc.) (type:uint8_t)
#                     self.state.lat_raw,               # lat                       : Latitude where image was taken [degE7] (type:int32_t)
#                     self.state.lon_raw,                # lon                       : Longitude where capture was taken [degE7] (type:int32_t)
#                     self.state.alt_raw,                # alt                       : Altitude (MSL) where image was taken [mm] (type:int32_t)
#                     self.state.alt_raw,                 # relative_alt              : Altitude above ground [mm] (type:int32_t)
#                     [0, 0, 0, 0],                # q                         : Quaternion of camera orientation (w, x, y, z order, zero-rotation is 0, 0, 0, 0) (type:float)
#                     self.cam.image_index,               # image_index               : Zero based index of this image (image count since armed -1) (type:int32_t)
#                     1,                # capture_result            : Boolean indicating success (1) or failure (0) while capturing this image. (type:int8_t)
#                     b''                # file_url                  : URL of image taken. Either local storage or http://foo.jpg if camera provides an HTTP interface. (type:char)
#                     )
#         elif msg.get_msgId() == mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT:
#             self.state.update_from_global_position_int(msg)
#         elif msg.get_msgId() == mavlink.MAVLINK_MSG_ID_SYSTEM_TIME:
#             print('SYS_TIME', msg.to_dict())
#             self.state.update_from_system_time(msg)
#             print("TM:", self.state.time_utc, self.state.time_boot_ms)



# coro = serial_asyncio.create_serial_connection(loop, lambda: SerialProto(service), '/dev/ttyS1', baudrate=115200)



class DummyProto:

    def connection_made(self, transport):
        pass

    def datagram_received(self, data, addr):
        pass

    def error_received(self, exc):
        pass

    def connection_lost(self, exc):
        pass


class ProcessController:
    """
    Wraps subprocess and control start/stop/stdout/stdin
    """

    def __init__(self, name: str, command: str) -> None:
        self.name = name
        self.command = command

        self.running = False
        self.proc = None
        self.handle_stdout_task = None
        self.handle_stderr_task = None

    def __str__(self):
        return self.name

    async def start(self):
        args = shlex.split(self.command)
        logger.info(f"{self} starting subprocess: {self.command}")
        self.running = True
        self.proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        logger.info(f"{self} subprocess started with pid {self.proc.pid}")

        self.handle_stdout_task = asyncio.create_task(self.handle_stdout())
        self.handle_stderr_task = asyncio.create_task(self.handle_stderr())

        resturncode = await self.proc.wait()

        logger.info(f"{self} proc finished with code: {resturncode}")

    async def stop(self):
        logger.info(f"{self} stopping subprocess [pid {self.proc.pid}] ({self.proc.returncode})")
        if self.proc.returncode is None:
            self.proc.terminate()
        self.running = False
        self.handle_stdout_task and self.handle_stdout_task.cancel()
        self.handle_stderr_task and self.handle_stderr_task.cancel()
        logger.info(f"{self} stopped.")

    async def handle_stderr(self):
        logger.info(f"{self} starting handle_stderr")
        while self.running and self.proc.returncode is None:
            raw_data = await self.proc.stderr.readline()
            if raw_data:
                raw_data = raw_data.decode().strip()
                logger.info(f"{self} STDERR: {raw_data}")

    async def handle_stdout(self):
        logger.info(f"{self} starting handle_stdout")
        while self.running and self.proc.returncode is None:
            raw_data = await self.proc.stdout.readline()
            if raw_data:
                raw_data = raw_data.decode().strip()
                logger.info(f"{self} STDOUT: {raw_data}")


async def main(args):

    logger.info("WFB Manager main start")

    # mav_proxy = MavProxy(args.mode, args.mavlink, telem_chan)

    processes = [
        ProcessController('vtest', command='gst-launch-1.0 videotestsrc ! video/x-raw,width=1280,height=720 ! autovideosink'),
        ProcessController('UDPtx', command='gst-launch-1.0 videotestsrc is-live=true ! video/x-raw,width=1280,height=720,framerate=25/1 ! videoconvert ! x264enc ! h264parse ! rtph264pay pt=96 ! udpsink host=127.0.0.1 port=5000'),
        ProcessController('UDPrx', command='gst-launch-1.0  udpsrc port=5000 ! application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink sync=false'),
    ]

    async def shutdown(s, loop):
        logger.info("Shutdown (signal %s)", s)
        for p in processes:
            await p.stop()


    loop = asyncio.get_running_loop()
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop)))

    # await thermal_chan.start()
   
    # await thermal_camera.start()

    tasks = [asyncio.create_task(p.start()) for p in processes]

    await asyncio.gather(*tasks)

    logger.info("WFB Manager main exit")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SVP WFB Manager')

    # parser.add_argument('--mode', type=str, required=True, help='Instance mode - ground or air')

    args = parser.parse_args()

    settings = Settings()

    asyncio.run(main(args))

    print('FIN!')