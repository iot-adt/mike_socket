import socket
import pyaudio
import threading
import RPi.GPIO as GPIO
import time

# GPIO 핀 설정
GPIO_PIN = 21  # 버튼 핀 번호
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# 음성 설정
RATE = 16000
CHANNELS = 2
FORMAT = pyaudio.paInt16
CHUNK = 1024

pa = pyaudio.PyAudio()

# 상태 변수
is_talking = False
talking_side = None  # "CLIENT" 또는 "SERVER"

# 마이크 데이터를 서버로 전송
def mic_thread(sock):
    global is_talking, talking_side
    stream = None  # 초기 스트림 상태
    while True:
        if GPIO.input(GPIO_PIN):  # 버튼이 눌린 상태
            if not is_talking or talking_side == "CLIENT":
                if stream is None:  # 스트림 초기화
                    stream = pa.open(rate=RATE, channels=CHANNELS, format=FORMAT, input=True,
                                     frames_per_buffer=CHUNK)
                    print("말하세요!")  # 말하세요 출력
                is_talking = True
                talking_side = "CLIENT"

                # 데이터를 읽고 전송
                data = stream.read(CHUNK, exception_on_overflow=False)
                sock.sendall(data)
        else:  # 버튼이 떼어진 상태
            if is_talking and talking_side == "CLIENT":
                is_talking = False
                talking_side = None
                print("버튼이 떼어졌습니다: 음성 전송 중단")
                if stream is not None:  # 스트림 닫기
                    stream.close()
                    stream = None
            time.sleep(0.1)  # CPU 과부하 방지

# 서버 데이터를 스피커로 출력
def speaker_thread(sock):
    stream = pa.open(rate=RATE, channels=CHANNELS, format=FORMAT, output=True,
                     frames_per_buffer=CHUNK)
    last_data = None  # 이전 데이터 추적
    while True:
        data = sock.recv(CHUNK)
        if data and data != last_data:  # 중복 데이터 방지
            stream.write(data)
            last_data = data

# 소켓 설정
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("클라이언트 시작")
    host = "10.144.115.93"  # 서버 IP 주소
    port = 8000
    s.connect((host, port))
    print("서버 접속")

    # 마이크와 스피커 스레드 실행
    t1 = threading.Thread(target=mic_thread, args=(s,), daemon=True)
    t2 = threading.Thread(target=speaker_thread, args=(s,), daemon=True)
    t1.start()
    t2.start()

    while True:
        time.sleep(1)
