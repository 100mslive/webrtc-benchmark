from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pprint import pprint
import subprocess
import time
import threading
from datetime import datetime
import os


from utils import *

import csv


total_video_frames_decoded = 0
total_video_frames_decoded_180p = 0
total_video_frames_decoded_360p = 0
total_video_frames_decoded_720p = 0
total_seconds_degraded = 0
remote_port = ''
throttle_kbps = 1000000
total_video_layer_switches = 0
expected_resolution = 1280*720.0


def clip(value, min_value, max_value):
    return max(min(value, max_value), min_value)

# 5*(p1)^3*(p2)^0.3*(p3)^0.5*(p4)^1*(p5)*2


def calc_qoe(freeze_duration_norm, resolution_norm, fps_norm, delay_norm, audio_concealed_norm):
    freeze_duration_norm = clip(freeze_duration_norm, 0, 1)
    resolution_norm = clip(resolution_norm, 0, 1)
    fps_norm = clip(fps_norm, 0, 1)
    delay_norm = clip(delay_norm, 0, 1)
    audio_concealed_norm = clip(audio_concealed_norm, 0, 1)
    return 5*(freeze_duration_norm ** 3)*(resolution_norm ** 0.3)*(fps_norm ** 0.2)*(delay_norm ** 0.5)*(audio_concealed_norm ** 2)


def main():

    # Add this line to create a new CSV file or append to an existing one
    csv_file = open('stats.csv', 'w', newline='')
    csv_writer = csv.writer(csv_file)

    # Add a header row if the file is new
    if os.stat('stats.csv').st_size == 0:
        csv_writer.writerow(['Timestamp', 'bitrate_kbps', 'Total Frames Decoded', 'freeze+pause in seconds', 'fps',
                            'Current Video Layer', 'freeze_duration_norm', 'resolution_norm',
                             'fps_norm', 'delay_norm', 'audio_concealed_norm', 'QoE'])

    global remote_port, throttle_kbps
    print("sample test case started")

    # This is a dummy call, to enter the sudo password first
    throttle_network(100000, '12345')
    desired_cap = {
        # Configure ChromeOptions to pass fake media stream
        'chromeOptions': {
            'args': ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]
        }
    }
    chrome_options = Options()
    chrome_options.add_argument("use-fake-ui-for-media-stream")
    # driver = webdriver.Remote(command_executor =
    #             'http://YOUR_USERNAME:YOUR_ACCESS_KEY@hub.browserstack.com/wd/hub', desired_capabilities = desired_cap)

    driver = webdriver.Chrome(chrome_options)
    # driver=webdriver.firefox()
    # driver=webdriver.ie()
    # maximize the window size
    driver.maximize_window()
    # navigate to the url
    # qa
    # meeting_url = "https://narayan.qa-app.100ms.live/preview/lvx-smp-gle"
    # prod-in2
    # meeting_url = "https://narayan.app.100ms.live/preview/jvv-hsch-vyc"
    # prod-eu3
    # meeting_url = "https://narayan.app.100ms.live/meeting/vaq-skrw-gwk"
    # preprod
    # meeting_url = "https://narayan.app.100ms.live/preview/xcr-jjsd-zcj"
    # qa daily
    # meeting_url = "https://narayan.qa-app.100ms.live/meeting/ret-orxh-pes"
    meeting_url = "https://akashtest.daily.co/KzdveB3UYDlAFAEHjwMg"
    # meeting_url = "https://narayan.app.100ms.live/meeting/mdp-erma-fnl"
    # meeting_url = "https://akash-videoconf-1125.app.100ms.live/meeting/tka-gpxd-esg"

    driver.get(meeting_url)
    # WebDriverWait(driver, 40).until(EC.element_to_be_clickable(
    #     (By.ID, "name"))).send_keys("test_narayan")

    # join_room_text = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH,
    #                                                                              "//*[contains(text(),'Join')]")))
    # join_room = join_room_text.find_element(By.XPATH, '..')
    # WebDriverWait(driver, 40).until(
    #     EC.element_to_be_clickable(join_room)).click()

    # WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH,
    #                                                            "//*[contains(text(),'Start Recording')]")))
    time.sleep(10)

    stats = get_daily_stats_from_js(driver)

    remote_port = get_remote_port(stats)

    def get_stats_every_sec():
        global total_video_frames_decoded, total_video_frames_decoded_180p, total_video_frames_decoded_360p
        global total_video_frames_decoded_720p, total_seconds_degraded
        global remote_port, throttle_kbps
        global total_video_layer_switches
        next_call = time.time()
        last = 0
        # maintain current layer state to count the number of layer switches
        current_video_layer = "none"
        layer_stats = {}
        layer_seconds = {}
        last_freeze_duration = 0
        last_concealed_samples = 0
        last_jitter_buffer_delay = 0
        last_jitter_buffer_emitted_count = 0
        last_jitter_buffer_delay_in_ms = 100
        # calculate QoE using 5 params:
        # p1:freeze_duration_norm p2:resolution_norm p3:fps_norm p4:delay_norm p5:audio_concealed_norm
        # the formula is 5*(1-p1)^3*(1-p2)^0.3*(1-p3)^0.5*(1-p4)^1*(1-p5)*2

        freeze_duration_norm = 0
        resolution_norm = 0
        fps_norm = 0
        delay_norm = 0
        audio_concealed_norm = 0
        # calculate these 5 params every second

        while True:
            next_call = next_call+1
            stats = get_daily_stats_from_js(driver)
            # print(f"{stats=}")

            new_port = get_remote_port(stats)
            if remote_port != new_port and new_port:
                remote_port = new_port
                throttle_network(throttle_kbps, remote_port)

            v = get_inbound_rtp_stats(stats, 'video')[0]
            print(
                f"video {v['framesDropped']=},{v['freezeCount']=},{v['pauseCount']=},{v['packetsLost']=},{v['totalFreezesDuration']=},{v['totalPausesDuration']=}")
            frames_decoded_in_last_sec = 0
            if last != 0:
                frames_decoded_in_last_sec = v['framesDecoded'] - last
                if frames_decoded_in_last_sec == 0:
                    total_seconds_degraded += 1
            last = v['framesDecoded']
            height = v['frameHeight']
            width = v['frameWidth']
            resolution_norm = (width*height/expected_resolution)

            freeze_duration_norm = 1 - (v['totalFreezesDuration'] -
                                        last_freeze_duration)

            if freeze_duration_norm < 0:
                freeze_duration_norm = 0.5
            last_freeze_duration = v['totalFreezesDuration']

            if frames_decoded_in_last_sec == 0:
                freeze_duration_norm = 0

            fps_norm = (frames_decoded_in_last_sec/30)

            current_jb_delay = v['jitterBufferDelay'] - \
                last_jitter_buffer_delay
            current_jb_emitted_count = v['jitterBufferEmittedCount'] - \
                last_jitter_buffer_emitted_count
            last_jitter_buffer_delay = v['jitterBufferDelay']
            last_jitter_buffer_emitted_count = v['jitterBufferEmittedCount']

            if current_jb_emitted_count > 0:
                jitter_buffer_delay_in_ms = current_jb_delay*1000 / current_jb_emitted_count
            else:
                jitter_buffer_delay_in_ms = last_jitter_buffer_delay_in_ms

            last_jitter_buffer_delay_in_ms = jitter_buffer_delay_in_ms
            delay_norm = 1 - min(1, jitter_buffer_delay_in_ms/2000)

            a = get_inbound_rtp_stats(stats, 'audio')[0]
            current_concealed_samples = a['concealedSamples'] - \
                a['silentConcealedSamples'] - last_concealed_samples
            last_concealed_samples = a['concealedSamples'] - \
                a['silentConcealedSamples']

            audio_concealed_norm = 1 - current_concealed_samples/48000

            qoe = calc_qoe(freeze_duration_norm, resolution_norm,
                           fps_norm, delay_norm, audio_concealed_norm)

            def get_temporal_from_framesPerSecond(fps):
                if height == 720:
                    if fps > 15:
                        return "30"
                    elif fps > 7:
                        return "15"
                    elif fps > 3:
                        return "7"
                else:
                    if fps > 11:
                        return "15"
                    elif fps > 5:
                        return "7"
                    elif fps > 1:
                        return "3"
                return "0"
            if 'framesPerSecond' in v:
                fps = get_temporal_from_framesPerSecond(v['framesPerSecond'])
            else:
                fps = 0

            new_video_layer = "" + str(height) + "p" + str(fps)

            if new_video_layer in layer_stats:
                layer_stats[new_video_layer] += frames_decoded_in_last_sec
                layer_seconds[new_video_layer] += 1
            else:
                layer_stats[new_video_layer] = frames_decoded_in_last_sec
                layer_seconds[new_video_layer] = 1

            if frames_decoded_in_last_sec == 0:
                new_video_layer = "degraded"

            if new_video_layer != current_video_layer and current_video_layer != "none":
                total_video_layer_switches += 1

            current_video_layer = new_video_layer
            total_video_frames_decoded += frames_decoded_in_last_sec

            print(f"frames:{total_video_frames_decoded=},{total_seconds_degraded=}",
                  f"{current_video_layer=},{total_video_layer_switches=},", layer_stats, layer_seconds)

            freeze_duration_norm = round(freeze_duration_norm, 2)
            resolution_norm = round(resolution_norm, 2)
            fps_norm = round(fps_norm, 2)
            delay_norm = round(delay_norm, 2)
            audio_concealed_norm = round(audio_concealed_norm, 2)
            qoe = round(qoe, 2)
            print(
                f"{freeze_duration_norm=},{resolution_norm=},{fps_norm=},{delay_norm=},{audio_concealed_norm=},{qoe=}")

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            csv_row = [timestamp, throttle_kbps, total_video_frames_decoded, v['totalFreezesDuration']+v['totalPausesDuration'], frames_decoded_in_last_sec,
                       current_video_layer, freeze_duration_norm, resolution_norm, fps_norm, delay_norm, audio_concealed_norm, qoe]

            csv_writer.writerow(csv_row)

            print(
                f"audio {a['concealedSamples']=},{a['packetsLost']=},{a['packetsDiscarded']=},{a.get('estimatedPlayoutTimestamp')=},{throttle_kbps=}")
            if next_call - time.time() > 0:
                time.sleep(next_call - time.time())

    def throttle_network1(num_kbps):
        throttle_network(num_kbps, remote_port)

    # time for setup
    time.sleep(10)

    # test starts from here
    timerThread = threading.Thread(target=get_stats_every_sec)
    timerThread.daemon = True
    timerThread.start()
    time.sleep(10)

    throttle_array = [(150, 120), (3000, 120),
                      (300, 120), (500, 120), (200, 120)]
    # throttle_array = [(1500, 10), (150, 5), (1500, 120)]
    # throttle_array = [150, 500, 300, 150, 150, 200, 1200,
    #                   1500, 300, 300, 150, 150, 200, 200, 250, 250, 500, 500]
    # throttle_array = [300, 80, 1200, 80, 100, 1300, 300, 1200, 80, 1500, 80, 300, 300, 300, 300, 300, 300,
    #                   300, 300, 300, 300, 300, 300, 80, 150, 150, 200, 200, 250, 250, 250, 500, 500, 500, 500, 500]
    for num_kbps_and_duration in throttle_array:
        print('Current DateTime:', datetime.now())
        throttle_network1(num_kbps_and_duration[0])
        throttle_kbps = num_kbps_and_duration[0]
        time.sleep(num_kbps_and_duration[1])

    # close the browser
    driver.close()
    print("sample test case successfully completed")

    print(f"summary:{total_video_frames_decoded=},{total_video_frames_decoded_180p=},",
          f"{total_video_frames_decoded_360p=},{total_video_frames_decoded_720p=},{total_seconds_degraded=}")

    csv_file.close()


if __name__ == "__main__":
    main()
