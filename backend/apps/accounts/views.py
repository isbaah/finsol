from rest_framework.generics import RetrieveAPIView

from apps.accounts.serializers import UserSerializer


class MeView(RetrieveAPIView):
    """GET /api/v1/me/ — the authenticated user's own profile.

    Default DRF permission (IsAuthenticated) is sufficient here: an
    unverified user's session never reaches request.user.is_authenticated,
    so this endpoint doubles as the "protected API access" boundary proven
    in tests.py.
    """

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
