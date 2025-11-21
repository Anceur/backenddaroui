from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

class RefreshTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # إذا كان المستخدم يعمل logout → لا نجدد access
        if request.path in ["/api/logout/", "/api/admin/logout/"]:
            return self.get_response(request)

        # نأخذ refresh token من الكوكيز
        refresh = request.COOKIES.get("refresh_token")

        if not refresh:
            return self.get_response(request)

        try:
            # نعمل Refresh
            refresh_obj = RefreshToken(refresh)
            access = str(refresh_obj.access_token)

            # نضعه في Authorization لكي Django يقرأ المستخدم
            request.META["HTTP_AUTHORIZATION"] = f"Bearer {access}"

        except TokenError:
            # إذا هذا refresh منتهي أو محذوف → لا Auto login
            pass

        return self.get_response(request)
