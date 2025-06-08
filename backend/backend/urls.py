"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from Where2go.views.admin_views import (
    AdminUserManagementView,
    GroupDeleteView,
    GroupEditView,
    GroupListView,
    UserBanView,
    UserSessionDeleteView,
)
from Where2go.views.auth_views import (
    ActivateUserView,
    Generate2FASecretView,
    LoginView,
    LoginView2FA,
)
from Where2go.views.categories_views import PlaceCategoriesView
from Where2go.views.group_views import (
    AddGroupMemberView,
    CreateGroupView,
    DeleteGroupView,
    GroupDetailView,
    JoinGroupView,
    LeaveGroupView,
    ListUserGroupsView,
    ManageGroupView,
    RemoveGroupMemberView,
)
from Where2go.views.map_views import NearbyPlacesView
from Where2go.views.oauth_views import (  # GoogleLoginView,; FacebookLoginView,
    GoogleLoginView,
    VKLoginView,
    social_auth_callback,
)
from Where2go.views.poll_views import ClosePollView  # , DeletePollView
from Where2go.views.poll_views import (
    CreatePollView,
    PollDetailView,
    PollListAllView,
    PollListView,
    PollResultsView,
    PollUpdateView,
    VotePollView,
)
from Where2go.views.user_views import (
    AccessLinkView,
    GetMeView,
    TemporaryAccessLinkView,
    UpdateUserView,
    UserCreate,
    UserDeleteView,
    UserDetailView,
    UserFriendsView,
    UserListView,
    UserSearchView,
    UserSessionView,
)

from Where2go.views.admin_views import admin_verify_2fa

schema_view = get_schema_view(
    openapi.Info(
        title="Where2go-api",
        default_version="v1",
        description="API documentation for Where2go project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@Where2go.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# LoginView,  UserCreate
urlpatterns = [
    path("", include('django_prometheus.urls')),
    path('admin/verify-2fa/', admin_verify_2fa, name='admin_verify_2fa'),

    path("", include("django_prometheus.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),  # OAuth URLs
    path("api/auth/vk/", VKLoginView.as_view(), name="vk_login"),
    path("api/auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path(
        "api/auth/social/callback/", social_auth_callback, name="social_auth_callback"
    ),
    path("api/auth/register/", UserCreate.as_view(), name="register"),
    path("api/auth/login-2fa", LoginView2FA.as_view(), name="login-2fa"),
    path(
        "api/auth/generate-2fa-secret",
        Generate2FASecretView.as_view(),
        name="generate-2fa-secret",
    ),
    path("api/auth/login", LoginView.as_view(), name="login"),
    path("api/auth/activate/", ActivateUserView.as_view(), name="activate-user"),
    path("api/auth/me", GetMeView.as_view(), name="get_me"),
    path("api/users/update/", UpdateUserView.as_view(), name="update-user"),
    path("api/users/list", UserListView.as_view(), name="user-list"),
    path("api/users/<int:id>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "api/users/<int:user_id>/friends/",
        UserFriendsView.as_view(),
        name="user-friends",
    ),
    path("api/users/search/", UserSearchView.as_view(), name="user-search"),
    path("api/groups/create", CreateGroupView.as_view(), name="create-group"),
    path("api/join-group/<int:group_id>/", JoinGroupView.as_view(), name="join-group"),
    path(
        "api/leave-group/<int:group_id>/", LeaveGroupView.as_view(), name="leave-group"
    ),
    path(
        "api/manage-group/<int:group_id>/",
        ManageGroupView.as_view(),
        name="manage-group",
    ),
    path("api/groups/", ListUserGroupsView.as_view(), name="list-user-groups"),
    path(
        "api/groups/<int:group_id>/add-member/",
        AddGroupMemberView.as_view(),
        name="add-member",
    ),
    path(
        "api/groups/<int:group_id>/remove-member/",
        RemoveGroupMemberView.as_view(),
        name="remove-member",
    ),
    path("api/groups/<int:group_id>/", DeleteGroupView.as_view(), name="delete-group"),
    path(
        "api/groups/<int:group_id>/detail/",
        GroupDetailView.as_view(),
        name="group-detail",
    ),
    path("api/groups/<int:group_id>/polls/", PollListView.as_view(), name="poll-list"),
    path(
        "api/groups/<int:group_id>/polls/create/",
        CreatePollView.as_view(),
        name="create-poll",
    ),
    path("api/polls/<int:id>/", PollDetailView.as_view(), name="poll-detail"),
    path("api/polls/<int:id>/close/", ClosePollView.as_view(), name="close-poll"),
    path("api/polls/<int:id>/vote/", VotePollView.as_view(), name="vote-poll"),
    path("api/polls/<int:id>/results/", PollResultsView.as_view(), name="poll-results"),
    path("api/polls/all/", PollListAllView.as_view(), name="poll-list-all"),
    path("api/polls/<int:pk>/update/", PollUpdateView.as_view(), name="update-poll"),
    # path('api/polls/', PollView.as_view(), name='polls'),
    # path('api/polls/<int:poll_id>/', DeletePollView.as_view(), name='delete-poll'),
    path("api/map/nearby-places/", NearbyPlacesView.as_view(), name="nearby-places"),
    path("api/map/categories", PlaceCategoriesView.as_view(), name="categories"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),

    # Обслуживание Vue.js приложения
    re_path(r"^$", TemplateView.as_view(template_name="index.html")),
    re_path(r"^(?!api/).*$", TemplateView.as_view(template_name="index.html")),

    path("api/admin/users/", UserListView.as_view(), name="admin-user-list"),
    path(
        "api/admin/users/<int:user_id>/",
        UserDeleteView.as_view(),
        name="admin-user-delete",
    ),
    path(
        "api/admin/users/<int:user_id>/ban/",
        UserBanView.as_view(),
        name="admin-user-ban",
    ),
    path("api/admin/groups/", GroupListView.as_view(), name="admin-group-list"),
    path(
        "api/admin/groups/<int:group_id>/",
        GroupEditView.as_view(),
        name="admin-group-edit",
    ),
    path(
        "api/admin/groups/<int:group_id>/delete/",
        GroupDeleteView.as_view(),
        name="admin-group-delete",
    ),
    path(
        "api/admin/sessions/<int:user_id>/",
        UserSessionDeleteView.as_view(),
        name="admin-user-sessions-delete",
    ),
    # path('api/admin/reset-password/<int:user_id>/', ResetPasswordView.as_view(), name='admin-reset-password'),
    # Временные ссылки доступа
    path("api/access-links/", TemporaryAccessLinkView.as_view(), name="access-links"),
    path(
        "api/access-links/<str:token>/",
        TemporaryAccessLinkView.as_view(),
        name="access-link-detail",
    ),
    path("api/access/<str:token>/", AccessLinkView.as_view(), name="access-link"),
    # Управление сессиями
    path("api/sessions/", UserSessionView.as_view(), name="user-sessions"),
    path(
        "api/sessions/<int:session_id>/",
        UserSessionView.as_view(),
        name="user-session-detail",
    ),
    # Административные функции
    path(
        "api/admin/users/<int:user_id>/manage/",
        AdminUserManagementView.as_view(),
        name="admin-user-management",
    ),
]
