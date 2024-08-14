import collections
import os
import queue
import subprocess
import threading
import time
from datetime import datetime
from threading import Thread
import cv2

import ffmpeg
from pynput import keyboard

from ScreenCapture import User
from time import sleep
from ScreenCapture import Audio



RATE = 44100
CHUNK = 1024
BUFFER_DURATION = 30
CHUNK_DURATION = CHUNK / RATE  # 每块持续时间（秒）
BUFFER_SIZE = int(BUFFER_DURATION / CHUNK_DURATION)
TEMP_URL = "E:/python_study/ScreenCapture/temp"
audio_url = "E:/python_study/ScreenCapture/audio"
video_url = "E:/python_study/ScreenCapture/video/"
photo_url = "E:/python_study/ScreenCapture/photo/"
fps = 30

def settings(rate,chunk,buffer_duration,temp_url,audio_Url,video_Url,photo_Url,Fps):
    global RATE, CHUNK, BUFFER_DURATION, TEMP_URL, audio_url, video_url,photo_url,fps,BUFFER_SIZE,CHUNK_DURATION
    RATE = rate
    CHUNK = chunk
    BUFFER_DURATION = buffer_duration
    TEMP_URL = temp_url
    audio_url = audio_Url
    video_url = video_Url
    photo_url = photo_Url
    CHUNK_DURATION = CHUNK / RATE  # 每块持续时间（秒）
    fps = Fps



stop_audio_event = threading.Event()
stop_video_event = threading.Event()
stop_videoback = threading.Event()
stop_audioback = threading.Event()
stop_photoback = threading.Event()
def on_press(key):
    try:
        if key.char=='w':
            stop_audio_event.set()
            stop_video_event.set()
            return False
        elif key.char=='q':
            stop_videoback.set()
            stop_audioback.set()
            stop_photoback.set()
            return False
    except:
        print('',end='')
        return None
def deleteFiles(path):
    num = 0
    if not os.path.exists(path):
        print("目录不存在")
    for root, dirs, files in os.walk(path):
        for file in files:
            os.remove(os.path.join(root, file))
            num+=1
    print(f"删除临时文件{num}个成功")

def get_duration(file):
    # 使用ffmpeg获取媒体文件的时长
    result = subprocess.run(
        ['ffmpeg', '-i', file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    ).stdout

    # 提取时长信息
    for line in result.splitlines():
        if "Duration" in line:
            duration = line.split("Duration: ")[1].split(",")[0]
            print(duration)
            return duration_to_seconds(duration)
    return None

def duration_to_seconds(duration):
    h, m, s = map(float, duration.split(':'))
    return h * 3600 + m * 60 + s
def set():
    rate = int(input("rate:"))
    chunk = int(input("chunk: "))
    buffer_duration = int(input("history_time: "))
    temp_url = input("temp files location: ")
    audio_Url = input("temp audio files location")
    video_Url = input("video location")
    photo_Url = input("photo location")
    Fps = int(input("fps: "))
    if rate == 0:
        rate = RATE
    if chunk == 0:
        chunk = CHUNK
    if buffer_duration == 0:
        buffer_duration = BUFFER_DURATION
    if temp_url == '0':
        temp_url = TEMP_URL
    if audio_Url == '0':
        audio_Url = audio_url
    if video_Url == '0':
        video_Url = video_url
    if photo_Url == '0':
        photo_Url = photo_url
    if Fps == 0:
        Fps = fps
    settings(rate, chunk, buffer_duration, temp_url, audio_Url, video_Url, photo_Url, Fps)
def change_fps(input_video,input_audio,output_file):
    video_seconds = get_duration(f'{input_video}')
    audio_seconds = get_duration(f'{input_audio}')

    # 计算比例
    duration_ratio = audio_seconds / video_seconds

    # 生成ffmpeg命令
    os.system(
        f'ffmpeg -i {input_video} -i {input_audio} -filter_complex "[0:v]setpts=PTS*{duration_ratio}" -c:v libx264 -c:a aac {output_file}')


def main():
    #set()
    audio_buffer = collections.deque([], int(BUFFER_DURATION / CHUNK_DURATION))
    user = User(photo_url, TEMP_URL, video_url, audio_url, fps, BUFFER_DURATION)
    audio = Audio(audio_buffer, rate=RATE, chunk=CHUNK, audio_location=audio_url)
    while True:
        choice = input("从下面几项选择： 1.录制视频  2.截取照片 3.开启视频回放功能 ")
        if choice == '1':
            now = datetime.now()
            name = ''.join(i.strip() for i in now.strftime("%Y%m%d%H%M%S"))
            output_file = f'{video_url}/{name}final.mp4'
            input_audio = f"{audio_url}/{name}.wav"
            input_video = f"{video_url}/{name}video.avi"
            print("开始录屏...(按w键停止)")

            threadVideo = threading.Thread(target=user.getVideo,args=(name,stop_video_event))
            threadAudio = threading.Thread(target=audio.play,args=(name,stop_audio_event))
            threadVideo.start()
            threadAudio.start()
            with keyboard.Listener(on_press=on_press) as listener: listener.join()
            threadVideo.join()
            threadAudio.join()
            change_fps(input_video,input_audio,output_file)
            os.remove(input_video)
            os.remove(input_audio)
            print("生成成功")
        if choice == '2':
            user.getScrrenCapture()
            print("截图已保存")
        if choice == '3':
            deleteFiles(TEMP_URL)
            print("开始视频即时回放功能")
            now = datetime.now()
            name = ''.join(i.strip() for i in now.strftime("%Y%m%d%H%M%S"))
            threadPhotoGet = threading.Thread(target=user.getPhoto,args= (stop_photoback,))
            threadVideoBack = threading.Thread(target=user.startVideoCapture,args=(name,stop_videoback))
            threadAudioBack = threading.Thread(target = audio.audioGet,args=(name,stop_audioback))
            threadPhotoGet.start()
            threadVideoBack.start()
            threadAudioBack.start()

            while True:
                with keyboard.Listener(on_press=on_press) as listener: listener.join()

                threadPhotoGet.join()
                threadVideoBack.join()
                threadAudioBack.join()
                output_file = f'{video_url}/{name}history_final.mp4'
                input_audio = f"{audio_url}/{name}audiohistory.wav"
                input_video = f"{video_url}/{name}videohistory.avi"
                os.system(
                    f'ffmpeg -i {input_video} -i {input_audio}  -c:v copy -c:a aac {output_file}')
                print("保存成功，继续采集")
                now = datetime.now()
                name = ''.join(i.strip() for i in now.strftime("%Y%m%d%H%M%S"))

                stop_videoback.clear()
                stop_audioback.clear()
                stop_photoback.clear()
                threadPhotoGet = threading.Thread(target=user.getPhoto, args=(stop_photoback,))
                threadVideoBack = threading.Thread(target=user.startVideoCapture,args=(name,stop_videoback))
                threadAudioBack = threading.Thread(target=audio.audioGet,args=(name,stop_audioback))
                threadPhotoGet.start()
                threadVideoBack.start()
                threadAudioBack.start()





if __name__ == '__main__':
    main()






