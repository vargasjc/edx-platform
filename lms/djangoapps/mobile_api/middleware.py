"""
Middleware for Mobile APIs
"""
from datetime import datetime
from django.core.cache import cache
from django.http import HttpResponse
from pytz import UTC
from mobile_api.mobile_platform import MobilePlatform
from mobile_api.models import AppVersionConfig
from mobile_api.utils import parsed_version
from openedx.core.lib.mobile_utils import is_request_from_mobile_app
import request_cache


class AppVersionUpgrade(object):
    """
    Middleware class to keep track of mobile application version being used
    """
    LATEST_VERSION_HEADER = 'EDX-APP-LATEST-VERSION'
    LAST_SUPPORTED_DATE_HEADER = 'EDX-APP-UPGRADE-DATE'
    NO_LAST_SUPPORTED_DATE = 'NO_LAST_SUPPORTED_DATE'
    NO_LATEST_VERSION = 'NO_LATEST_VERSION'
    USER_APP_VERSION = 'USER_APP_VERSION'
    REQUEST_CACHE_NAME = 'app-version-info'
    MEM_CACHE_TIMEOUT = 3600

    def process_request(self, request):
        """
        raises HTTP Upgrade Require error if request is from mobile native app and
        user app version is no longer supported
        """
        version_data = self._get_version_info(request)
        if version_data:
            last_supported_date = version_data[self.LAST_SUPPORTED_DATE_HEADER]
            if last_supported_date != self.NO_LAST_SUPPORTED_DATE:
                if datetime.now().replace(tzinfo=UTC) > last_supported_date:
                    return HttpResponse(status=426)  # Http status 426; Update Required

    def process_response(self, __, response):
        """
        If request is from mobile native app, then add headers to response;
        1. EDX-APP-LATEST-VERSION; if user app version < latest available version
        2. EDX-APP-UPGRADE-DATE; if user app version < min supported version and timestamp < expiry of that version
        """
        request_cache_dict = request_cache.get_cache(self.REQUEST_CACHE_NAME)
        if request_cache_dict:
            last_supported_date = request_cache_dict[self.LAST_SUPPORTED_DATE_HEADER]
            if last_supported_date != self.NO_LAST_SUPPORTED_DATE:
                response[self.LAST_SUPPORTED_DATE_HEADER] = last_supported_date.isoformat()
            latest_version = request_cache_dict[self.LATEST_VERSION_HEADER]
            user_app_version = request_cache_dict[self.USER_APP_VERSION]
            if (latest_version != self.NO_LATEST_VERSION and
                    parsed_version(user_app_version) < parsed_version(latest_version)):
                response[self.LATEST_VERSION_HEADER] = latest_version
        return response

    def _get_cache_key_name(self, key, field):
        """ get key name to use to cache any property against field name and identification key """
        return "mobile_api.app_version_upgrade.{}.{}".format(field, key)

    def _get_version_info(self, request):
        """
        It sets request cache data for last_supported_date and latest_version with memcached values if exists against
        user app properties else computes the values for specific platform and sets it in both memcache (for next
        server interaction from same app version/platform) and request cache
        """
        user_agent = request.META.get('HTTP_USER_AGENT')
        if user_agent:
            platform = self._get_platform(request, user_agent)
            if platform:
                request_cache_dict = request_cache.get_cache(self.REQUEST_CACHE_NAME)
                request_cache_dict[self.USER_APP_VERSION] = platform.version
                cached_data = cache.get_many([
                    self._get_cache_key_name(platform.version, self.LAST_SUPPORTED_DATE_HEADER),
                    self._get_cache_key_name(platform.NAME, self.LATEST_VERSION_HEADER)
                ])

                last_supported_date = cached_data.get(
                    self._get_cache_key_name(platform.version, self.LAST_SUPPORTED_DATE_HEADER),
                    None
                )
                if not last_supported_date:
                    last_supported_date = self._get_last_supported_date(platform.NAME, platform.version)
                    cache.set(
                        self._get_cache_key_name(platform.version, self.LAST_SUPPORTED_DATE_HEADER),
                        last_supported_date,
                        self.MEM_CACHE_TIMEOUT
                    )
                request_cache_dict[self.LAST_SUPPORTED_DATE_HEADER] = last_supported_date

                latest_version = cached_data.get(
                    self._get_cache_key_name(platform.NAME, self.LATEST_VERSION_HEADER),
                    None
                )
                if not latest_version:
                    latest_version = self._get_latest_version(platform.NAME)
                    cache.set(
                        self._get_cache_key_name(platform.NAME, self.LATEST_VERSION_HEADER),
                        latest_version,
                        self.MEM_CACHE_TIMEOUT
                    )
                request_cache_dict[self.LATEST_VERSION_HEADER] = latest_version

                return {
                    self.LAST_SUPPORTED_DATE_HEADER: last_supported_date,
                    self.LATEST_VERSION_HEADER: latest_version,
                    self.USER_APP_VERSION: platform.version,
                }

    def _get_platform(self, request, user_agent):
        """
        determines the platform for mobile app making the request
        returns None if request is not from native mobile app or does not belong to supported platforms
        """
        if is_request_from_mobile_app(request):
            return MobilePlatform.get_instance(user_agent)

    def _get_last_supported_date(self, platform_name, platform_version):
        """ get expiry date of app version for a platform """
        return AppVersionConfig.last_supported_date(platform_name, platform_version) or self.NO_LAST_SUPPORTED_DATE

    def _get_latest_version(self, platform_name):
        """ get latest app version available for platform """
        return AppVersionConfig.latest_version(platform_name) or self.NO_LATEST_VERSION
