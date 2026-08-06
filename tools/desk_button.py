import requests
import sys

BUTTON = sys.argv[1]

ESP_IP = "192.168.1.176"

url = f"http://{ESP_IP}/api/{BUTTON}"

response = requests.get(url)

print(response.text)