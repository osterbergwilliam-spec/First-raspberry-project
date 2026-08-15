cat > stream_to_obs.sh << 'EOF'
#!/bin/bash
# Stream webcam to RTMP server (OBS or similar)
ffmpeg -f v4l2 -i /dev/video0 -f flv rtmp://your-obs-server:1935/live/stream_key
EOF

chmod +x stream_to_obs.sh