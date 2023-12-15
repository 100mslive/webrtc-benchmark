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

throttle_kbps = 1000000


def get_throttle_kbps():
    return throttle_kbps


def get_stats_from_js(driver):
    script1 = '''
  var stats1=[]
  var stats = __hms.sdk.getWebrtcInternals().subscribeConnection.getStats()
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
    return stats


def get_twilio_stats_from_js(driver):
    script1 = '''
  var stats1=[]
  var stats = twilioRoom._signaling._peerConnectionManager._peerConnections.values().next().value._peerConnection._peerConnection.getStats()
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
    return stats


def get_publish_stats_from_js(driver):
    script1 = '''
  var stats1=[]
  var stats = __hms.sdk.getWebrtcInternals().publishConnection.getStats()
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
    return stats


def get_remote_port(stats):
    for stat in stats:
        if stat.get('type') == 'remote-candidate' and \
                (stat.get('candidateType') == 'srflx' or stat.get('candidateType') == 'prflx' or stat.get('candidateType') == 'host'):
            remote_port = stat.get('port')
            print(f"port:{stat.get('port')}, isremote:{stat.get('isRemote')}")
            return str(remote_port)


def get_inbound_rtp_stats(stats, kind):
    media_stats = []
    for stat in stats:
        if stat.get('type') == 'inbound-rtp' and stat.get('kind') == kind:
            media_stats.append(stat)
    return media_stats


def get_outbound_rtp_stats(stats, kind, rid):
    media_stats = []
    for stat in stats:
        if stat.get('type') == 'outbound-rtp' and stat.get('kind') == kind:
            if stat.get('rid') == rid:
                media_stats.append(stat)

    return media_stats


def throttle_network(num_kbps, remote_port, packet_loss_ratio=0.0):
    global throttle_kbps
    throttle_kbps = num_kbps
    subprocess.run([f'{os.path.realpath(os.path.dirname(__file__))}/throttle_network_in_plr.sh', str(num_kbps), str(packet_loss_ratio),
                    remote_port], check=False, text=True)


def throttle_network_out(num_kbps, remote_port, packet_loss_ratio=0.0):
    global throttle_kbps
    throttle_kbps = num_kbps
    subprocess.run([f'{os.path.realpath(os.path.dirname(__file__))}/throttle_network_out_plr.sh', str(num_kbps), str(packet_loss_ratio),
                    remote_port], check=False, text=True)


def block_all_network():
    subprocess.run(
        [f'{os.path.realpath(os.path.dirname(__file__))}/block_all_network.sh'], check=False, text=True)


def get_temporal_from_framesPerSecond(fps):
    if fps > 18:
        return "30"
    if fps > 7:
        return "15"
    return "0"
