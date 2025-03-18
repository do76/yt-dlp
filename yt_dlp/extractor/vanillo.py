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
            'uploader_url': 'M7A',
            'upload_date': '20240309',  # if using _parse_date, expect YYYYMMDD, server api provides 2024-03-09T07:56:35.636Z
            'duration': 5.71,
            'view_count': 205,
            'comment_count': 2,
            'like_count': 4,
            'dislike_count': 0,
            'average_rating': 4.2,
            'categories': ['film_and_animation'],
            'tags': ['Wawa', 'wawa', 'Wa Wa', 'wa wa', 'WaWa', 'wAwA', 'wA Wa'],
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

        uploader = data.get('uploader', {})
        uploader_url = uploader.get('url')

        upload_date_raw = data.get('publishedAt')
        upload_date = None
        if upload_date_raw:
            # _parse_date returns a string in YYYYMMDD format if successful.
            # If you prefer to keep the original ISO format, simply set:
            # upload_date = upload_date_raw
            upload_date = self._parse_date(upload_date_raw)

        duration = data.get('duration')
        view_count = None
        if data.get('views'):
            try:
                view_count = int(data.get('views'))
            except Exception:
                view_count = None

        comment_count = data.get('totalComments')

        # Extract likes and dislikes separately
        like_count = None
        if data.get('likes') is not None:
            try:
                like_count = int(data.get('likes'))
            except Exception:
                like_count = None

        dislike_count = None
        if data.get('dislikes') is not None:
            try:
                dislike_count = int(data.get('dislikes'))
            except Exception:
                dislike_count = None

        average_rating = None
        if like_count is not None and dislike_count is not None:
            total = like_count + dislike_count
            if total > 0:
                average_rating = round((like_count / total) * 5, 1)

        categories = data.get('category')
        if categories and not isinstance(categories, list):
            categories = [categories]
        tags = data.get('tags')

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
            'uploader_url': uploader_url,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'comment_count': comment_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'average_rating': average_rating,
            'categories': categories,
            'tags': tags,
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
