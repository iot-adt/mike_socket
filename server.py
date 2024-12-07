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
talking_side = None  # "SERVER" 또는 "CLIENT"

# 마이크 데이터를 클라이언트로 전송
def mic_thread(conn):
    global is_talking, talking_side
    stream = None  # 초기 스트림 상태
    while True:
        if GPIO.input(GPIO_PIN):  # 버튼이 눌린 상태
            if not is_talking or talking_side == "SERVER":
                if stream is None:  # 스트림 초기화
                    stream = pa.open(rate=RATE, channels=CHANNELS, format=FORMAT, input=True,
                                     frames_per_buffer=CHUNK)
                    print("말하세요!")  # 말하세요 출력
                is_talking = True
                talking_side = "SERVER"

                # 데이터를 읽고 전송
                data = stream.read(CHUNK, exception_on_overflow=False)
                conn.sendall(data)
        else:  # 버튼이 떼어진 상태
            if is_talking and talking_side == "SERVER":
                is_talking = False
                talking_side = None
                print("버튼이 떼어졌습니다: 음성 전송 중단")
                if stream is not None:  # 스트림 닫기
                    stream.close()
                    stream = None
            time.sleep(0.1)  # CPU 과부하 방지

# 클라이언트 데이터를 스피커로 출력
def speaker_thread(conn):
    stream = pa.open(rate=RATE, channels=CHANNELS, format=FORMAT, output=True,
                     frames_per_buffer=CHUNK)
    last_data = None  # 이전 데이터 추적
    while True:
        data = conn.recv(CHUNK)
        if data and data != last_data:  # 중복 데이터 방지
            stream.write(data)
            last_data = data

# 소켓 설정
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print("서버 시작")
    host = "0.0.0.0"
    port = 8000
    s.bind((host, port))
    s.listen(1)

    conn, addr = s.accept()
    print(f"클라이언트 접속: {addr}")

    # 마이크와 스피커 스레드 실행
    t1 = threading.Thread(target=mic_thread, args=(conn,), daemon=True)
    t2 = threading.Thread(target=speaker_thread, args=(conn,), daemon=True)
    t1.start()
    t2.start()

    while True:
        time.sleep(1)
