from kkbox_partner_sdk.auth_flow import KKBOXOAuth

CLIENT_ID = 'cea7cb81a731b46caeb9b8c0e25abd22'
CLIENT_SECRET = '6317f7914dcc9e1fb50d01f744b3f1fb'

auth = KKBOXOAuth(CLIENT_ID, CLIENT_SECRET)
token = auth.fetch_access_token_by_client_credentials()
print(token)

from kkbox_partner_sdk.api import KKBOXAPI

kkboxapi = KKBOXAPI(token)

keyword = '女武神'
types = ['artist', 'album', 'track', 'playlist']
types = ['track']
result = kkboxapi.search_fetcher.search(keyword, types)

tracks = result['tracks']['data']
# print('搜尋結果是:{}'.format(tracks))

track_id = 'KmtpBrC4R1boMEdm1Q'
track_id = result['tracks']['data'][0]['id']
print('歌曲編號是:{}'.format(track_id))

track_info = kkboxapi.track_fetcher.fetch_track(track_id)
url = track_info['url']
print('歌曲資訊連結是:{}'.format(url))

tickets = kkboxapi.ticket_fetcher.fetch_media_provision(track_id)
# print(tickets )
url = tickets['url']
print('下載位置連結是:{}'.format(url))

print('底下是播放資訊')
import subprocess

subprocess.run(['ffplay', '-nodisp', '-autoexit', url])
