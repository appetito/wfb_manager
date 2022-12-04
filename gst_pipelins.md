gst-launch-1.0 -v v4l2src device=/dev/video2 num-buffers=-1 ! "video/x-raw,format=(string)UYVY, width=(int)1920, height=(int)1080,framerate=(fraction)30/1" ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=4000000" ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5602 sync=false


gst-launch-1.0 -v v4l2src device=/dev/video2 num-buffers=-1 ! "video/x-raw,format=(string)UYVY, width=(int)1280, height=(int)720,framerate=(fraction)30/1" ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=4000000" ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5602 sync=false


384x292

gst-launch-1.0 -v v4l2src device=/dev/video0 num-buffers=-1 ! videoconvert ! v4l2h264enc extra-controls="controls, h264_profile=4, video_bitrate=2000000" ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5603 sync=false

/usr/bin/wfb_tx -p 2 -u 5603 -K /etc/drone.key -B 20 -G long -S 1 -L 1 -M 1 -k 8 -n 12 -T 0 -i 7669206 wlan0
/usr/bin/wfb_rx -p 2 -c 127.0.0.1 -u 5601 -K /etc/gs.key -k 8 -n 12 -i 7669206 wlan0

gst-launch-1.0 udpsrc port=5601 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! h264parse ! mmalh264dec ! mmalvideosink sync=false

gst-launch-1.0 udpsrc port=5600 caps='application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264' ! rtph264depay ! h264parse ! mmalh264dec ! mmalvideosink sync=false


gst-launch-1.0 videotestsrc ! video/x-raw,width=1280,height=720 ! autovideosink




gst-launch-1.0 videotestsrc ! video/x-raw,width=1280,height=720 ! videoconvert ! vtenc_h264 ! 'video/x-h264, profile=high, level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5602 sync=false

 gst-launch-1.0 videotestsrc is-live=true ! video/x-raw,width=1280,height=720,framerate=25/1 ! videoconvert ! x264enc ! h264parse ! rtph264pay pt=96 ! udpsink host=127.0.0.1 port=5000

 gst-launch-1.0  udpsrc port=5000 ! application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink