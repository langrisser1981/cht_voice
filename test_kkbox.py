from kkbox_partner_sdk.auth_flow import KKBOXOAuth

CLIENT_ID = 'cea7cb81a731b46caeb9b8c0e25abd22'
CLIENT_SECRET = '6317f7914dcc9e1fb50d01f744b3f1fb'

auth = KKBOXOAuth(CLIENT_ID, CLIENT_SECRET)
token = auth.fetch_access_token_by_client_credentials()
print(token)

from kkbox_partner_sdk.api import KKBOXAPI
kkboxapi = KKBOXAPI(token)
track_id = 'KmtpBrC4R1boMEdm1Q'
artist = kkboxapi.track_fetcher.fetch_track(track_id)
#print(artist)

song = kkboxapi.ticket_fetcher.fetch_media_provision(track_id)
#print(song)
file = song['url']
#print(file)

import subprocess
subprocess.run(['ffplay', '-autoexit', file])

