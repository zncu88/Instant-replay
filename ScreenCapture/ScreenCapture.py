import collections
import os
import queue
import threading
import uuid
import wave
from collections import deque

from PIL import Image
from pynput import keyboard
import mss
import mss.tools
#最初使用队列进行临时储存过去影像，发现占用内存过多，保存过大视频就会导致内存炸了，所以考虑使用临时文件的方法牺牲存储来优化内存。后来使用将numpy数组直接存储成随机名字的npy文件，但发现文件太大，占用存储空间过大，并且存储过程占用资源过大，所以说使用npz文件将数组压缩后在使用。
#后发现使用cpu过大，并且目前的获取的视频没有声音。在尝试融入声音的过程中，初步设想是利用线程和线程中线程来完成，但发现并不是很好操控，后来思考得出产生声音和产生图象是完全分割开的操作，所以准备使用多进程来分别实现两个功能，在主线程进行视频合成。最后选择多线程进行，然后发现出现音画不同步比较严重，考虑到可能是帧率不合适
#音频正常，先利用过去的视频和音频调整采集的帧率，但发现这样做并不合适，还是会出现音画不同步，并且每一次帧率都不一样，然后又考虑每次生成完视频音频后在合成前利用ffmpeg对视频帧率处理，后来发现虽然时长符合了，但最终只是整体时长符合，有时慢有时快，所以得出结论是在采集的时候因为pyautogui采集和处理速度过慢，导致出现丢帧的现象，所以采用了mss更快的直接调用系统api的方法，解决了音画不同步的问题，果然在图像处理方面速度快很重要。
#后来发现虽然视频录制可以正常进行了，但视频回放还是很难实现同步，出现了很多问题，后来排查问题发现是截图频率太低，导致视频时长很短，综合来看应该是存储占用了太长时间拖后腿导致截图并不能及时获得，所以考虑到进行异步处理，分别从将截图操作视为另一个线程和将整个回放操作视为主进程外的另一个进程。后来利用多线程初步解决了这个问题，但利用队列储存numpy数组这个操作占用内存太多了，暂时还没有想到处理策略。

import cv2
import numpy as np
import pyautogui
import time
from datetime import datetime
import pyaudio
fourcc = cv2.VideoWriter_fourcc(*"XVID")
w, h = pyautogui.size()

monitor = {'top': 0, 'left': 0, 'width': w, 'height': h}


class User(object):
    def __init__(self,photo_location,temp_url,video_location,audio_location,fps,_save):
        self.photo_url = photo_location
        self.temp_url = temp_url
        self.audio_location = audio_location
        self.video_location = video_location
        self.fps = fps
        self.queue = queue.Queue()
        self.save = _save
        self.screen_size = (2048,1280)
        self.tempFile = []
        self.getting = False
        self.thisTime = None
        self.photo_queue = queue.Queue()

        self.bool = False
        self.bool2 = False
    def getScrrenCapture(self):
        im = pyautogui.screenshot()
        now = datetime.now()
        name = ''.join(i.strip() for i in now.strftime("%Y%m%d%H%M%S"))
        str = f"{name}.png"
        im.save(f"{self.photo_url}/{str}")


    def getPhoto(self,stop_photoback):
        with mss.mss() as sct:
            while not stop_photoback.is_set():
                img = sct.grab(monitor)
                self.photo_queue.put(img)
                time.sleep(1/self.save)

    def startVideoCapture(self,name,stop_video_event):
        while not stop_video_event.is_set() or self.photo_queue.qsize() != 0:
                img = self.photo_queue.get()
                img = np.array(img)
                frame = cv2.resize(img, (self.screen_size[0], self.screen_size[1]))
                #frame = np.array(frame)
                node_id = str(uuid.uuid4()).replace('-', '')
                name1 = os.path.join(self.temp_url, f"{node_id}.npz")
                np.savez_compressed(f"{name1}", frame=frame)
                self.queue.put(name1)
                self.thisTime = name1
                print(self.queue.qsize())

                if self.queue.qsize() >= self.save*self.fps/2:
                    if not self.getting:
                        name2delete = self.queue.get()
                        os.remove(name2delete)

        self.getVideoCapture(name)
    def getVideoCapture(self,name):
        size = self.queue.qsize()
        print(size)
        out = cv2.VideoWriter(f"{self.video_location}/{name}videohistory.avi", cv2.VideoWriter_fourcc('X','V','I','D'),self.fps/2,self.screen_size)
        self.getting = True
        for _ in range(size):
            name2delete = self.queue.get()
            frame = np.load(name2delete)['frame']
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame,(self.screen_size[0],self.screen_size[1]))
            os.remove(name2delete)
            out.write(frame)
        self.getting = False

    def getVideo(self,name,stop_video_event):
        print('开始采集视频')
        out = cv2.VideoWriter(f"{self.video_location}/{name}video.avi", cv2.VideoWriter_fourcc('X', 'V', 'I', 'D'),self.fps / 2, self.screen_size)
        with mss.mss() as sct:
            while not stop_video_event.is_set():
                    img = sct.grab(monitor)
                    img = np.array(img)
                    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) #不知为何必须要两次才可以
                    frame = cv2.resize(img, (self.screen_size[0], self.screen_size[1]))
                    out.write(frame)
                    #time.sleep(0.001)




class Audio(object):
    def __init__(self,queue:collections.deque,rate,chunk,audio_location):
        self.queue = queue
        self.audio = pyaudio.PyAudio()
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = rate  #一秒有多少个
        self.CHUNK = chunk   #一块有多少个
        self.stream = self.audio.open(format=self.FORMAT,
                                      channels=self.CHANNELS,
                                      rate=self.RATE,
                                      input=True,
                                      output=True,
                                      frames_per_buffer=self.CHUNK)
        self.continueA = True
        self.audioList = []   #不需要删除的用列表表示
        self.audio_location = audio_location
        self.getA = False

    def play(self,name,stop_event):
        self.audioList = []
        print('开始采集音频')
        while not stop_event.is_set():
            data = self.stream.read(self.CHUNK)
            self.audioList.append(data)
            #time.sleep(0.001)
        print('采集结束，开始保存')
        self.save(name,self.audioList)
        print(f'成功保存到{self.audio_location}/{name}.wav')
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

    def save(self,name,list):
        wf = wave.open(f'{self.audio_location}/{name}.wav', 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(list))
        list.clear()
        wf.close()

    def audioGet(self,name,stop_event):
        while not stop_event.is_set():
            data = self.stream.read(self.CHUNK)
            self.queue.append(data)
        self.saveAudio(name)


    def saveAudio(self,name):
            self.save(f'{name}audiohistory',self.queue)
            self.queue.clear()











