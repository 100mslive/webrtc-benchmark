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

total_video_frames_decoded = 0
total_video_frames_decoded_180p = 0
total_video_frames_decoded_360p = 0
total_video_frames_decoded_720p = 0
total_seconds_degraded = 0
remote_port = ''
throttle_kbps = 1000000
total_video_layer_switches = 0


def get_daily_stats_from_js(driver):
    script1 = '''

  var stats1=[]
  var stats = rtcpeers.soup.recvTransport._handler._pc.getStats()
  stats.then(
    function(value) {value.forEach((result, i) => {
          stats1.push(result)
      })},
    function(error) {console.log(error); stats1.push(error)}
  ); 
  await stats;

  return stats1
    
  '''

    stats = driver.execute_script(script1)
    # print(f'stats={stats}')
    return stats


def main():
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
    # meeting_url = "https://narayan-live.qa-app.100ms.live/streaming/meeting/lei-bgms-squ"
    # meeting_url = "https://narayan.qa-app.100ms.live/meeting/lvx-smp-gle"
    # prod-in2
    # meeting_url = "https://narayan.app.100ms.live/preview/jvv-hsch-vyc"
    # prod-eu2
    # meeting_url = "https://narayan.app.100ms.live/meeting/vaq-skrw-gwk"
    # preprod
    # meeting_url = "https://narayan.app.100ms.live/preview/xcr-jjsd-zcj"
    # meeting_url = "https://narayan.app.100ms.live/meeting/bnc-ekqh-rrs"
    meeting_url = "https://akashtest.daily.co/KzdveB3UYDlAFAEHjwMg"
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
    time.sleep(30)

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
        layer_frames_decoded = {}
        layer_seconds = {}

        while True:
            next_call = next_call+1
            stats = get_daily_stats_from_js(driver)

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

            def get_temporal_from_framesPerSecond(fps):
                if height == 720:
                    if fps > 15:
                        return "30"
                    elif fps > 7:
                        return "15"
                    elif fps > 3:
                        return "7"
                else:
                    if fps > 7:
                        return "15"
                    elif fps > 4:
                        return "7"
                    elif fps > 1:
                        return "3"
                return "0"
            if 'framesPerSecond' in v:
                fps = get_temporal_from_framesPerSecond(v['framesPerSecond'])
            else:
                fps = 0

            new_video_layer = "" + str(height) + "p" + str(fps)

            if new_video_layer in layer_frames_decoded:
                layer_frames_decoded[new_video_layer] += frames_decoded_in_last_sec
                layer_seconds[new_video_layer] += 1
            else:
                layer_frames_decoded[new_video_layer] = frames_decoded_in_last_sec
                layer_seconds[new_video_layer] = 1

            if frames_decoded_in_last_sec == 0:
                new_video_layer = "degraded"

            if new_video_layer != current_video_layer and current_video_layer != "none":
                total_video_layer_switches += 1

            current_video_layer = new_video_layer
            total_video_frames_decoded += frames_decoded_in_last_sec

            print(f"frames:{total_video_frames_decoded=},{total_seconds_degraded=}",
                  f"{current_video_layer=},{total_video_layer_switches=},", layer_frames_decoded, layer_seconds)

            a = get_inbound_rtp_stats(stats, 'audio')[0]
            print(
                f"audio {a['concealedSamples']=},{a['packetsLost']=},{a['packetsDiscarded']=},{throttle_kbps=}")
            if next_call - time.time() > 0:
                time.sleep(next_call - time.time())

    def throttle_network1(num_kbps):
        throttle_network(num_kbps, remote_port)

    # time for setup
    time.sleep(30)

    # test starts from here
    timerThread = threading.Thread(target=get_stats_every_sec)
    timerThread.daemon = True
    timerThread.start()
    time.sleep(20)

    # throttle_array = [300, 500, 1200, 300, 100, 1300, 300, 1200, 80, 1500, 80, 300, 300, 300, 300, 300, 300,
    #                   300, 300, 300, 300, 300, 300, 80, 150, 150, 200, 200, 250, 250, 250, 500, 500, 500, 500, 500]
    throttle_array = [150, 500, 300, 150, 150, 200, 1200,
                      1500, 300, 300, 150, 150, 200, 200, 250, 250, 500, 500]
    # throttle_array = [300, 80, 1200, 80, 100, 1300, 300, 1200, 80, 1500, 80, 300, 300, 300, 300, 300, 300,
    #                   300, 300, 300, 300, 300, 300, 80, 150, 150, 200, 200, 250, 250, 250, 500, 500, 500, 500, 500]
    for num_kbps in throttle_array:
        print('Current DateTime:', datetime.now())
        throttle_network1(num_kbps)
        throttle_kbps = num_kbps
        time.sleep(120)

    # close the browser
    driver.close()
    print("sample test case successfully completed")

    print(f"summary:{total_video_frames_decoded=},{total_video_frames_decoded_180p=},",
          f"{total_video_frames_decoded_360p=},{total_video_frames_decoded_720p=},{total_seconds_degraded=}")


if __name__ == "__main__":
    main()
