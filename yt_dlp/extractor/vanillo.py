import json

from .common import InfoExtractor
from ..utils import ExtractorError


class VanilloIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/(?:v|embed)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/v/iaCi-oTmmGY',
        'info_dict': {
            'id': 'iaCi-oTmmGY',
            'title': 'Wawa',
            'description': '',
            'thumbnail': 'https://images.vanillo.tv/V6mYuajeHGsSSPRJKCdRAvvWgHFVGZ00g-ne3TZevss/h:300/aHR0cHM6Ly9pbWFnZXMuY2RuLnZhbmlsbG8udHYvdGh1bWJuYWlsL1RhUGE3TEJFTVBlS205elh2ZWdzLmF2aWY',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # 1) Retrieve video info (metadata)
        video_info_url = f'https://api.vanillo.tv/v1/videos/{video_id}?groups=uploader,profile.full'
        video_info = self._download_json(video_info_url, video_id, note='Downloading video info')
        if video_info.get('status') != 'success':
            raise ExtractorError('Video info API returned an error', expected=True)
        data = video_info.get('data', {})
        title = data.get('title') or video_id
        description = data.get('description')
        thumbnail = data.get('thumbnail')

        # 2) Get watch token (required for accessing manifests)
        watch_token_url = 'https://api.vanillo.tv/v1/watch'
        post_data = json.dumps({'videoId': video_id}).encode('utf-8')
        watch_token_resp = self._download_json(
            watch_token_url, video_id,
            note='Downloading watch token',
            data=post_data,
            headers={'Content-Type': 'application/json'})

        watch_token = watch_token_resp.get('data', {}).get('watchToken')
        if not watch_token:
            raise ExtractorError('Failed to retrieve watch token', expected=True)

        # 3) Get the HLS & DASH manifest URLs using the watch token
        manifests_url = f'https://api.vanillo.tv/v1/watch/manifests?watchToken={watch_token}'
        manifests = self._download_json(manifests_url, video_id, note='Downloading manifests')
        hls_url = manifests.get('data', {}).get('media', {}).get('hls')
        dash_url = manifests.get('data', {}).get('media', {}).get('dash')

        # 4) Extract available formats using yt-dlp helpers
        formats = []
        if hls_url:
            formats.extend(self._extract_m3u8_formats(
                hls_url, video_id, ext='mp4', m3u8_id='hls', fatal=False))
        if dash_url:
            formats.extend(self._extract_mpd_formats(
                dash_url, video_id, mpd_id='dash', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }

class VanilloPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/playlist/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/playlist/wn9_PM-DTPypZeNy32EE1A',
        'info_dict': {
            'id': 'wn9_PM-DTPypZeNy32EE1A',
            'title': 'Staff Picks',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        api_url = f'https://api.vanillo.tv/v1/playlists/{playlist_id}/videos?offset=0&limit=20'
        playlist_data = self._download_json(api_url, playlist_id, note='Downloading playlist info')
        videos = playlist_data.get('data', {}).get('videos', [])
        entries = []
        for video in videos:
            vid = video.get('id')
            if not vid:
                continue
            video_url = f'https://vanillo.tv/v/{vid}'
            entries.append(self.url_result(video_url, VanilloIE.ie_key()))
        return self.playlist_result(entries, playlist_id, playlist_title=f'Playlist {playlist_id}')

class VanilloUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/u/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/u/f9pKNFrUSG6Qo3pJ4UlGbQ',
        'info_dict': {
            'id': 'f9pKNFrUSG6Qo3pJ4UlGbQ',
            'title': 'User BakhosVillager videos',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        api_url = f'https://api.vanillo.tv/v1/profiles/{user_id}/videos?offset=0&limit=20'
        user_data = self._download_json(api_url, user_id, note='Downloading user videos')
        videos = user_data.get('data', {}).get('videos', [])
        entries = []
        for video in videos:
            vid = video.get('id')
            if not vid:
                continue
            video_url = f'https://vanillo.tv/v/{vid}'
            entries.append(self.url_result(video_url, VanilloIE.ie_key()))
        return self.playlist_result(entries, user_id, playlist_title=f'User {user_id} videos')
