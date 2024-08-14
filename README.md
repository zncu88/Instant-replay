# Instant-replay
Real time playback and screen recording functions implemented using Python libraries


By continuously capturing screen images and maintaining a recording list, ffmpeg is used to achieve screen recording effects. Instant replay uses a similar method, but due to the inability of memory to support large-scale data in numpy arrays, the method of downloading npz files locally and then reading them is used. Unfortunately, the high latency of screenshots is still caused by time-consuming file and image operations, queues have to be used for caching, resulting in high memory usage. Currently, no good solution has been found to solve this problem...

The voice input tool uses voicemeeter
