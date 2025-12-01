from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

router = SimpleRouter()
router.register("users", UserViewSet)
router.register("departments", DepartmentsViewSet)
router.register("movies", OptimizedAddMoviesViewSet, basename="movies")
router.register("films-comments", CommentViewSet, basename="comments")
router.register("series", MovieSeriesViewSet, basename="series")

urlpatterns = [
    path("", include(router.urls)),
    # path("get_profile/", get_profile),
    # path("edit_profile/", edit_profile),
    # path("login/", LoginView.as_view()),
    # path("signup/", SignupView.as_view()),
    # path("token/", TokenObtainPairView.as_view()),
    # path("token/refresh/", TokenRefreshView.as_view()),
    
    # Saved films - bitta endpoint bilan
    # path('saved-films/', OptimizedSavedFilmsView.as_view()),
    # path('saved-films/<int:film_id>/', OptimizedSavedFilmsView.as_view(), name='saved-film-detail'),
    
    # Department movies
    path('departments/<int:department_id>/movies/', DepartmentMoviesAPIView.as_view()),
    
    # Voting system
    # path("vote-count/<int:movie_id>/", GetVotes.as_view()),
    # path("check-vote/<int:movie_id>/", CheckVote.as_view()),
    # path("vote/<int:movie_id>/", CreateVote.as_view()),
    
    # Notifications
    # path("notifications/", NotificationListView.as_view()),
    # path("notifications/<int:pk>/", NotificationDetailView.as_view()),
    # path("notifications/<int:pk>/read/", NotificationReadView.as_view()),
    # path("notifications/<int:pk>/view/", NotificationViewUpdate.as_view()),
    # path("notifications/unread_count/", UnreadNotificationCount.as_view()),
    
    # Password reset
    # path("password-reset/request/", PasswordResetRequestView.as_view()),
    # path("password-reset/verify/", PasswordResetVerifyView.as_view()),
    # path("password-reset/confirm/", PasswordResetConfirmView.as_view()),
    
    # Statistics
    # path("totalMovies/", TotalMoviesCount.as_view()),
    # path("totalUsers/", TotalUserCount.as_view()),
    # path("totalDepartments/", TotalDepartmentsCount.as_view()),
    # path("totalSeries/", TotalSeriesCount.as_view()),
    # path("totalComments/", TotalCommentsCount.as_view()),
    
    # Additional features
    path('similar-movies/', SimilarMoviesAPIView.as_view()),
    path('movies/<int:movie_id>/increment-count/', IncrementMovieCountAPIView.as_view()),

    # Swiper movies (count 8)
    path('sprmvs/', SwiperMoviesAPIView.as_view(), name='swiper-movies'),

    # Home movies ( count 12 )
    path('hmvs/', HomeMoviesAPIView.as_view(), name='home-movies'),

    # Trailers
    path('trls/', TrailersAPIView.as_view(), name='trailers'),

    # All movies
    path('all-movies/', AllMoviesAPIView.as_view(), name='all-movies'),

    # Search 
    path('search/', MovieSearchAPIView.as_view(), name='movie-search'),
]