from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count, Q, Case, When, Value, BooleanField
from add_all.models import Add_departments, Add_movies, Comment, LikeDislike, MovieSeries, Notification, SavedFilm
from users.models import PasswordResetToken, User
from .serializers import *
from django.db.models import Max, Case, When, Value, BooleanField, Count, Q
from django.db.models.functions import Coalesce
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
import requests

class LoginView(APIView):
    authentication_classes = [BasicAuthentication]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(ModelViewSet):
    authentication_classes = [BasicAuthentication]
    serializer_class = UserModelSerializer
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TotalUserCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = User.objects.count()
        return Response({"totalUsers": total})

class TotalDepartmentsCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = Add_departments.objects.count()
        return Response({"totalDepartments": total})

class TotalMoviesCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = Add_movies.objects.count()
        return Response({"totalMovies": total})

class OptimizedAddMoviesViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MovieDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return MovieUpdateSerializer
        return MovieListSerializer

    def update(self, request, *args, **kwargs):
        # Agar frontenddan department_id kelmasa, mavjud qiymatni saqlab qolish
        if 'department_id' not in request.data and 'add_departments' not in request.data:
            instance = self.get_object()
            request.data['department_id'] = instance.add_departments.id if instance.add_departments else None
        
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        # 🔥 Bir xil tartiblash mantig'ini qo'llaymiz
        queryset = Add_movies.objects.annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        movie_id = self.request.query_params.get('movie_id')
        if movie_id:
            queryset = queryset.filter(id=movie_id)
        
        return queryset.distinct()

    def get_client_ip(self, request):
        """Client IP manzilini olish"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_uzbekistan_user(self, request):
        """
        Foydalanuvchi O'zbekistondan ekanligini aniqlaydi
        """
        try:
            # 1. IP Geolocation API orqali
            client_ip = self.get_client_ip(request)
            
            # Localhost yoki test IP bo'lsa
            if client_ip in ['127.0.0.1', 'localhost']:
                return self.check_headers_for_uzbekistan(request)
            
            # 🔥 BIR NECHTA GEOLOCATION API LAR
            geo_data = self.get_geolocation_data(client_ip)
            
            if geo_data:
                country = geo_data.get('country', '').lower()
                country_code = geo_data.get('countryCode', '').lower()
                
                # O'zbekiston tekshiruvi
                if country == 'uzbekistan' or country_code == 'uz':
                    # 🔥 YANGI: VPN tekshiruvi
                    is_vpn = self.check_vpn_indicators(geo_data, client_ip)
                    if is_vpn:
                        return False  # VPN bor - ruxsat ber
                    else:
                        return True   # VPN yo'q - blokla
                
                # Boshqa mamlakatlar - har doim ruxsat ber
                return False
                
            # API ishlamasa, browser ma'lumotlariga qarab
            return self.check_headers_for_uzbekistan(request)
            
        except Exception as e:
            return self.check_headers_for_uzbekistan(request)

    def get_geolocation_data(self, ip):
        """Bir nechta API lar orqali geolocation ma'lumotlarini olish"""
        apis = [
            f'http://ip-api.com/json/{ip}?fields=status,country,countryCode,isp,org,as,proxy,hosting',
            f'https://ipapi.co/{ip}/json/',
            f'http://ipwho.is/{ip}'
        ]
        
        for api_url in apis:
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Har xil API lardan ma'lumotlarni standartlashtirish
                    if 'ip-api.com' in api_url:
                        return {
                            'country': data.get('country', ''),
                            'countryCode': data.get('countryCode', ''),
                            'isp': data.get('isp', ''),
                            'org': data.get('org', ''),
                            'as': data.get('as', ''),
                            'proxy': data.get('proxy', False),
                            'hosting': data.get('hosting', False)
                        }
                    elif 'ipapi.co' in api_url:
                        return {
                            'country': data.get('country_name', ''),
                            'countryCode': data.get('country_code', ''),
                            'isp': data.get('org', ''),
                            'org': data.get('org', ''),
                            'as': data.get('asn', ''),
                            'proxy': data.get('proxy', False),
                            'hosting': data.get('hosting', False)
                        }
                    elif 'ipwho.is' in api_url:
                        return {
                            'country': data.get('country', ''),
                            'countryCode': data.get('country_code', ''),
                            'isp': data.get('connection', {}).get('isp', ''),
                            'org': data.get('connection', {}).get('org', ''),
                            'as': data.get('connection', {}).get('asn', ''),
                            'proxy': data.get('connection', {}).get('proxy', False),
                            'hosting': data.get('connection', {}).get('hosting', False)
                        }
            except Exception as e:
                continue
                
        return None

    def check_vpn_indicators(self, geo_data, ip):
        """VPN bor-yo'qligini aniqlash"""
        isp = geo_data.get('isp', '').lower()
        org = geo_data.get('org', '').lower()
        as_info = geo_data.get('as', '').lower()
        
        # 🔥 VPN PROVIDERLAR RO'YXATI
        vpn_indicators = [
            # Taniqli VPN kompaniyalari
            'vpn', 'proxy', 'hosting', 'datacenter', 'server',
            'expressvpn', 'nordvpn', 'surfshark', 'cyberghost',
            'private internet access', 'windscribe', 'vyprvpn',
            'ipvanish', 'hotspot shield', 'hide.me', 'purevpn',
            'worldstream', 'digital ocean', 'amazon aws',
            'google cloud', 'microsoft azure', 'linode', 'vultr',
            'ovh', 'hetzner', 'alibaba cloud', 'tencent cloud',
            'ibm cloud', 'oracle cloud'
        ]
        
        # ISP, Org yoki AS da VPN belgilari borligini tekshirish
        for indicator in vpn_indicators:
            if (indicator in isp or 
                indicator in org or 
                indicator in as_info):
                return True
        
        # Proxy yoki hosting maydonlari
        if geo_data.get('proxy') or geo_data.get('hosting'):
            return True
            
        # 🔥 YANGI: O'zbekiston ISP larini aniqlash
        uzbek_telecom_indicators = [
            'uzbektelekom', 'uztelecom', 'ucell', 'beeline uz', 
            'mobiuz', 'ums', 'perfectum', 'uzmobile'
        ]
        
        for telecom in uzbek_telecom_indicators:
            if (telecom in isp or 
                telecom in org or 
                telecom in as_info):
                return False  # O'zbekiston ISP - VPN emas
        
        return False

    def check_headers_for_uzbekistan(self, request):
        """Browser headers orqali O'zbekistonni tekshirish"""
        timezone = request.headers.get('Timezone', '')
        language = request.headers.get('Accept-Language', '')
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Timezone tekshiruvi
        uzbek_timezones = ['tashkent', 'samarkand', 'utc+5', '+05:00', 'asia/tashkent']
        if any(tz in timezone.lower() for tz in uzbek_timezones):
            return True
        
        # Language tekshiruvi
        if 'uz' in language.lower():
            return True
        
        return False

    def retrieve(self, request, *args, **kwargs):
        try:
            # 🔥 Yangi tartiblash bilan filter qilish
            instance = Add_movies.objects.annotate(
                latest_series_date=Max('series__created_at'),
                latest_activity=Coalesce(
                    Max('series__created_at'), 
                    'created_at'
                )
            ).filter(pk=kwargs['pk']).first()
            
            if not instance:
                return Response({"error": "Film topilmadi"}, status=status.HTTP_404_NOT_FOUND)
            
            # 🔥 DEBUG MA'LUMOTLARI
            client_ip = self.get_client_ip(request)
            
            # 🔥 YANGI TEKSHIRUV
            if instance.is_possible:
                is_uzbek = self.is_uzbekistan_user(request)
                
                if is_uzbek:
                    return Response({
                        "error": "Ushbu film O'zbekiston hududida ko'rsatilmaydi. Iltimos, VPN orqali kirib ko'ring.",
                        "is_blocked": True,
                        "movie_name": instance.movies_name,
                        "requires_vpn": True,
                        "debug_info": {
                            "client_ip": client_ip,
                            "is_possible": instance.is_possible
                        }
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # 🔥 MUHIM: Agar film bloklanmagan bo'lsa, NORMAL KODNI DAVOM ETTIRISH
            # User-specific annotatsiyalar
            queryset = Add_movies.objects.filter(pk=instance.pk)
            
            if request.user.is_authenticated:
                queryset = queryset.annotate(
                    is_saved=Case(
                        When(Q(savedfilm__user=request.user), then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField()
                    ),
                    like_count=Count('likedislike', filter=Q(likedislike__vote=True)),
                    dislike_count=Count('likedislike', filter=Q(likedislike__vote=False)),
                    user_vote=Case(
                        When(Q(likedislike__user=request.user), then=Value('likedislike__vote')),
                        default=Value(None),
                        output_field=BooleanField()
                    )
                )
            else:
                queryset = queryset.annotate(
                    is_saved=Value(False, output_field=BooleanField()),
                    like_count=Count('likedislike', filter=Q(likedislike__vote=True)),
                    dislike_count=Count('likedislike', filter=Q(likedislike__vote=False)),
                    user_vote=Value(None, output_field=BooleanField())
                )
            
            instance = queryset.select_related('add_departments').prefetch_related(
                'series', 'movie_comments', 'movie_comments__user'
            ).first()
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class MovieSeriesViewSet(ModelViewSet):
    queryset = MovieSeries.objects.all()
    serializer_class = OptimizedMovieSeriesSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = MovieSeries.objects.all()
        movie_id = self.request.query_params.get('movie')
        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)
        return queryset

class TotalSeriesCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = MovieSeries.objects.count()
        return Response({"totalSeries": total})

@api_view(["GET"])
def get_profile(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication credentials were not provided."}, status=401)
    serializer = UserModelSerializer(request.user)
    return Response(serializer.data)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_profile(request):
    try:
        user = request.user
        serializer = EditUserModelSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profil muvaffaqiyatli yangilandi!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({"error": "Foydalanuvchi topilmadi!"}, status=status.HTTP_404_NOT_FOUND)

class OptimizedSavedFilmsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        saved_films = SavedFilm.objects.filter(user=request.user).select_related(
            'film', 'film__add_departments'
        ).prefetch_related('film__series').order_by('-saved_at')
        serializer = OptimizedSavedFilmSerializer(saved_films, many=True)
        return Response(serializer.data)

    def post(self, request):
        film_id = request.data.get("filmId")
        if not film_id:
            return Response({"detail": "Film ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            film = Add_movies.objects.get(id=film_id)
        except Add_movies.DoesNotExist:
            return Response({"detail": "Film not found."}, status=status.HTTP_404_NOT_FOUND)

        saved_film, created = SavedFilm.objects.get_or_create(user=request.user, film=film)
        saved_films = SavedFilm.objects.filter(user=request.user).select_related(
            'film', 'film__add_departments'
        ).prefetch_related('film__series').order_by('-saved_at')
        serializer = OptimizedSavedFilmSerializer(saved_films, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, film_id=None):
        if not film_id:
            return Response({"detail": "Film ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            saved_film = SavedFilm.objects.get(user=request.user, film__id=film_id)
            saved_film.delete()
            saved_films = SavedFilm.objects.filter(user=request.user).select_related(
                'film', 'film__add_departments'
            ).prefetch_related('film__series').order_by('-saved_at')
            serializer = OptimizedSavedFilmSerializer(saved_films, many=True)
            return Response(serializer.data)
        except SavedFilm.DoesNotExist:
            return Response({"detail": "Film saqlanganlar ro'yxatida topilmadi."}, status=status.HTTP_404_NOT_FOUND)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by("-created_at")
    serializer_class = OptimizedCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TotalCommentsCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total = Comment.objects.count()
        return Response({"totalComments": total})

class VoteMovie(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def post(self, request, movie_id):
        movie = Add_movies.objects.get(id=movie_id)
        vote = request.data.get("vote")
        existing_vote = LikeDislike.objects.filter(user=request.user, movie=movie).first()
        if existing_vote:
            existing_vote.vote = vote
            existing_vote.save()
            return Response({"message": "Vote updated successfully"})
        LikeDislike.objects.create(user=request.user, movie=movie, vote=vote)
        return Response({"message": "Vote successfully recorded"})

class GetVotes(APIView):
    def get(self, request, movie_id):
        try:
            movie = Add_movies.objects.get(id=movie_id)
            like_count = LikeDislike.objects.filter(movie=movie, vote=True).count()
            dislike_count = LikeDislike.objects.filter(movie=movie, vote=False).count()
            return Response({"like_count": like_count, "dislike_count": dislike_count})
        except Add_movies.DoesNotExist:
            return Response({"error": "Movie not found"}, status=404)

class CheckVote(APIView):
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get(self, request, movie_id):
        movie = get_object_or_404(Add_movies, id=movie_id)
        if request.user.is_authenticated:
            vote = LikeDislike.objects.filter(user=request.user, movie=movie).first()
        else:
            ip = self.get_client_ip(request)
            session_key = request.session.session_key
            vote = LikeDislike.objects.filter(
                models.Q(ip_address=ip) | models.Q(session_key=session_key), movie=movie
            ).first()
        if vote:
            return Response({"vote": vote.vote, "can_change": True})
        return Response({"vote": None, "can_change": True})

class CreateVote(APIView):
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def post(self, request, movie_id):
        movie = get_object_or_404(Add_movies, id=movie_id)
        vote = request.data.get("vote")
        if vote is None:
            return Response({"error": "Vote not provided"}, status=400)

        if request.user.is_authenticated:
            existing_vote = LikeDislike.objects.filter(user=request.user, movie=movie).first()
            if existing_vote:
                existing_vote.vote = vote
                existing_vote.save()
                message = "Vote updated successfully"
            else:
                LikeDislike.objects.create(user=request.user, movie=movie, vote=vote)
                message = "Vote created successfully"
        else:
            ip = self.get_client_ip(request)
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            existing_vote = LikeDislike.objects.filter(
                models.Q(ip_address=ip) | models.Q(session_key=session_key), movie=movie
            ).first()
            if existing_vote:
                existing_vote.vote = vote
                existing_vote.save()
                message = "Vote updated successfully"
            else:
                LikeDislike.objects.create(movie=movie, vote=vote, ip_address=ip, session_key=session_key)
                message = "Vote created successfully"

        like_count = LikeDislike.objects.filter(movie=movie, vote=True).count()
        dislike_count = LikeDislike.objects.filter(movie=movie, vote=False).count()
        return Response({"like_count": like_count, "dislike_count": dislike_count, "message": message})

class NotificationListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        notifications = Notification.objects.all().order_by("-created_at")
        serializer = NotificationSerializer(notifications, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotificationViewUpdate(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.mark_as_read(request)
        return Response({"views_count": notification.views_count})

class UnreadNotificationCount(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            unread_count = Notification.objects.exclude(read_by=request.user).count()
        else:
            ip = self.get_client_ip(request)
            if not ip:
                return Response({"unread_count": Notification.objects.count()})
            unread_count = Notification.objects.extra(
                where=["NOT read_by_ips LIKE %s"], params=[f"%{ip}%"]
            ).count()
        return Response({"unread_count": unread_count})

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

class NotificationDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def put(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        title = request.data.get("title", "").strip()
        text = request.data.get("text", "").strip()
        if not title or not text:
            return Response({"error": "Title va Text bo'sh bo'lishi mumkin emas!"}, status=status.HTTP_400_BAD_REQUEST)
        notification.title = title
        notification.text = text
        notification.save()
        return Response({"message": "Notification updated successfully"}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response({"message": "Notification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class NotificationReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        if notification.read_by.filter(id=request.user.id).exists():
            return Response({"message": "Already read"}, status=status.HTTP_200_OK)
        notification.read_by.add(request.user)
        notification.save()
        return Response({"message": "Notification marked as read"})

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"error": "Ushbu email manziliga tegishli foydalanuvchi topilmadi"}, status=status.HTTP_404_NOT_FOUND)

            PasswordResetToken.objects.filter(user=user).delete()
            token = PasswordResetToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))

            subject = "Parolni tiklash kodi"
            context = {"token": token.token, "site_name": "AFD Platform", "expiry_minutes": 5}
            html_message = render_to_string("email/password_reset_email.html", context)
            text_message = f"""
                Assalomu alaykum,
                Sizning parolni tiklash kodingiz: {token.token}
                Diqqat: Bu kod faqat 5 daqiqagacha amal qiladi.
                Agar siz bu so'rovni amalga oshirmagan bo'lsangiz, iltimos, bu xabarga e'tibor bermang.
                Hurmat bilan,
                AFD Platform jamoasi
            """

            try:
                msg = EmailMultiAlternatives(subject, text_message, settings.DEFAULT_FROM_EMAIL, [email])
                msg.attach_alternative(html_message, "text/html")
                msg.send()
                return Response({"message": "Parolni tiklash kodi emailingizga yuborildi"}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": f"Xabar yuborishda xatolik: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response

class SimilarMoviesAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        movie_id = request.query_params.get('movie_id')
        limit = int(request.query_params.get('limit', 30))
        
        if not movie_id:
            return Response({"error": "movie_id parametri kerak"}, status=400)
        
        try:
            current_movie = Add_movies.objects.only('add_departments_id').get(id=movie_id)
            similar_movies = Add_movies.objects.filter(
                add_departments_id=current_movie.add_departments_id
            ).exclude(id=movie_id).only(
                'id', 'add_departments_id', 'movies_preview_url', 
                'movies_name', 'movies_description', 'country'
            )[:limit]
            
            serializer = SimilarMoviesSerializer(similar_movies, many=True)
            return Response(serializer.data)
            
        except Add_movies.DoesNotExist:
            return Response({"error": "Film topilmadi"}, status=404)

class IncrementMovieCountAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, movie_id):
        try:
            updated = Add_movies.objects.filter(id=movie_id).update(
                count=models.F('count') + 1
            )
            
            if updated:
                movie = Add_movies.objects.get(id=movie_id)
                return Response({
                    "success": True, 
                    "message": "Count muvaffaqiyatli oshirildi",
                    "new_count": movie.count
                })
            else:
                return Response({
                    "success": False,
                    "error": "Film topilmadi"
                }, status=404)
                
        except Add_movies.DoesNotExist:
            return Response({
                "success": False,
                "error": "Film topilmadi"
            }, status=404)
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Server xatosi: {str(e)}"
            }, status=500)

class DepartmentPagination(PageNumberPagination):
    page_size = 16
    page_size_query_param = 'page_size'
    max_page_size = 100

class DepartmentMoviesAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = DepartmentMoviesSerializer
    pagination_class = DepartmentPagination
    
    def get_queryset(self):
        department_id = self.kwargs['department_id']
        
        # 🔥 Yangi tartiblash
        queryset = Add_movies.objects.filter(
            add_departments_id=department_id
        ).annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data['results'],
            'pagination': {
                'count': response.data['count'],
                'total_pages': response.data['count'] // self.pagination_class.page_size + 1,
                'current_page': int(request.GET.get('page', 1)),
                'page_size': self.pagination_class.page_size,
                'next': response.data['next'],
                'previous': response.data['previous'],
            }
        }
        return response

class PasswordResetVerifyView(APIView):
    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            token = serializer.validated_data["token"]
            try:
                user = User.objects.get(email=email)
                PasswordResetToken.objects.get(
                    user=user,
                    token=token,
                    is_used=False,
                    expires_at__gte=timezone.now(),
                )
                return Response(
                    {"message": "Kod tasdiqlandi. Yangi parolni kiriting."},
                    status=status.HTTP_200_OK,
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "Ushbu email manziliga tegishli foydalanuvchi topilmadi"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except PasswordResetToken.DoesNotExist:
                return Response(
                    {"error": "Noto'g'ri kod yoki kodning amal qilish muddati tugagan"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["new_password"]
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.get(
                user=user, token=token, is_used=False, expires_at__gte=timezone.now()
            )
            user.set_password(new_password)
            user.save()
            reset_token.is_used = True
            reset_token.save()
            return Response(
                {"message": "Parol muvaffaqiyatli yangilandi."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SwiperMoviesAPIView(generics.ListAPIView):
    serializer_class = SwiperMoviesSerializer
    
    def get_queryset(self):
        # 🔥 Yangi tartiblash
        queryset = Add_movies.objects.annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')[:8]
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data
        }
        return response

class HomeMoviesAPIView(generics.ListAPIView):
    serializer_class = HomeMoviesSerializer
    
    def get_queryset(self):
        # 🔥 Yangi tartiblash - eng oxirgi faoliyat bo'yicha
        queryset = Add_movies.objects.annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        queryset = queryset.exclude(
            add_departments__department_name__icontains="Treylerlar"
        )
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data
        }
        return response

class DepartmentsViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    serializer_class = DepartmentsSerializer
    queryset = Add_departments.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data
        }
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data = {
            'data': response.data
        }
        return response

class TrailersAPIView(generics.ListAPIView):
    """
    Faqat Treylerlar departmentidagi filmlarni qaytaradi
    """
    serializer_class = TrailersSerializer
    
    def get_queryset(self):
        # 🔥 Yangi tartiblash
        queryset = Add_movies.objects.filter(
            add_departments__department_name__icontains="Treylerlar"
        ).annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data
        }
        return response
    
class CustomPagination(PageNumberPagination):
    page_size = 16 
    page_size_query_param = 'page_size'
    max_page_size = 100

class AllMoviesAPIView(generics.ListAPIView):
    serializer_class = AllMoviesSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        # 🔥 Yangi tartiblash
        queryset = Add_movies.objects.annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        queryset = queryset.exclude(
            add_departments__department_name__icontains="Treylerlar"
        )
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data['results'],
            'pagination': {
                'count': response.data['count'],
                'total_pages': response.data['count'] // self.pagination_class.page_size + 1,
                'current_page': int(request.GET.get('page', 1)),
                'page_size': self.pagination_class.page_size,
                'next': response.data['next'],
                'previous': response.data['previous'],
            }
        }
        return response

class MovieSearchAPIView(generics.ListAPIView):
    serializer_class = MovieSearchSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        
        if not query:
            return Add_movies.objects.none()
        
        # 🔥 Yangi tartiblash bilan qidiruv
        queryset = Add_movies.objects.filter(
            Q(movies_name__icontains=query) |
            Q(movies_name__istartswith=query)
        ).annotate(
            latest_series_date=Max('series__created_at'),
            latest_activity=Coalesce('latest_series_date', 'created_at')
        ).order_by('-latest_activity')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            'data': response.data,
            'query': request.GET.get('q', ''),
            'count': len(response.data)
        }
        return response