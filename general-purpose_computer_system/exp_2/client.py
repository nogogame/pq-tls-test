import subprocess
import csv
import multiprocessing
import time
import shlex
import os
import logging
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def netem_set(ns, dev,latency,loss):
    if loss == 0:
        command = ['ip', 'netns', 'exec', ns, 'tc', 'qdisc', 'change', 'dev', dev, 'root', 'netem', 'limit', '1000', 'latency', latency, 'rate', '1000mbit']
    else:
        command = ['ip', 'netns', 'exec', ns, 'tc', 'qdisc', 'change', 'dev', dev, 'root', 'netem', 'limit', '1000', 'latency', latency, 'loss','{0}%'.format(loss),'rate', '1000mbit']
    run_subprocess(command)

def handshake_full(ke_alg):
    command = [ 'ip', 'netns', 'exec', 'client_namespace', '../openssl-OQS-OpenSSL_1_1_1-stable/apps/openssl', 's_time','-curves', ke_alg]
    return command
def rtt_time():
    command = ['ip', 'netns', 'exec', 'client_namespace', 'ping', '192.168.1.1', '-c', '10']
    result = run_subprocess(command)
    result_fmt = result.splitlines()[-1].split("/")
    return result_fmt[4].replace(".", "p")

def run_client(ke_alg, count):
    handshake_times = []
    for _ in range(count):
        process = subprocess.Popen(handshake_full(ke_alg), stdout=subprocess.PIPE, text=True)
        output, _ = process.communicate()
        handshake_times.append(output)
    return handshake_times

def run_subprocess(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error("Command execution failed with return code %d: %s", e.returncode, e.stderr)
        raise

combinations = {
    "rsa:2048":"prime256v1",
    "rsa:3072":"secp384r1",
    "rsa:4096":"secp521r1",
    "falcon512":"kyber512",
    "dilithium2":"sntrup761",
    "dilithium3":"kyber768",
    "dilithium5":"kyber1024",
    "p256_falcon512":"p256_kyber512",
    "p256_dilithium2":"p256_sntrup761",
    "p384_dilithium3":"p384_kyber768",
    "p521_dilithium5":"p521_kyber1024"
}

sig_alg="rsa:2048"
ke_alg = combinations[sig_alg]
Latency = ['7.75ms','14.75ms','33.75ms']
Lossrate    = [0,1,2,3,4,5]
count = 500

current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
folder_path = os.path.join("data")
os.makedirs(folder_path, exist_ok=True)

for latency_time in Latency:
    netem_set('client_namespace', 'client_veth',  latency=latency_time,loss = 0)
    netem_set('server_namespace', 'server_veth',  latency=latency_time,loss = 0)
    rtt_str = rtt_time()
    file_name = os.path.join(folder_path, '{}_{}ms_{}_full.csv'.format(ke_alg, rtt_str,sig_alg))
    with open(file_name, 'w') as out:
        csv_out = csv.writer(out)
        for loss_rate in Lossrate:
            netem_set('client_namespace', 'client_veth', latency=latency_time,loss=loss_rate)
            netem_set('server_namespace', 'server_veth', latency=latency_time,loss=loss_rate)
            handshake_times = [loss_rate]
            handshake_time = run_client(ke_alg, count)
            handshake_times.extend(handshake_time)
            csv_out.writerow(handshake_times)