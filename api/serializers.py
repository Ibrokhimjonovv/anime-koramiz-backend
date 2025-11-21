from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from django.utils import timezone
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from add_all.models import Add_departments, Add_movies, Comment, MovieSeries, Notification, SavedFilm
from users.models import PasswordResetToken, User

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        uname = data.get("username")
        pword = data.get("password")
        if uname and pword:
            user = User.objects.get(username=uname)
            if user.check_password(pword):
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                return data
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

class SignupSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "username", "email", "password"]
        extra_kwargs = {
            "email": {
                "validators": [EmailValidator()],
                "error_messages": {"unique": "Bu email manzil allaqachon ro'yxatdan o'tgan"}
            }
        }

    def validate_email(self, value):
        if self.Meta.model.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu email manzil allaqachon ro'yxatdan o'tgan")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = self.Meta.model(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserModelSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = [
            'id',
            'first_name', 
            'last_name', 
            'date_joined',
            'last_login', 
            'is_superuser', 
            'username', 
            'email', 
            'profile_image'
        ]

class EditUserModelSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile_image", "old_password", "new_password"]

    def update(self, instance, validated_data):
        old_password = validated_data.pop("old_password", None)
        new_password = validated_data.pop("new_password", None)
        if old_password and new_password:
            if not instance.check_password(old_password):
                raise serializers.ValidationError({"old_password": "Eski parol noto'g'ri!"})
            instance.set_password(new_password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class OptimizedCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'user_id', 'username', 'text', 'created_at', 'movie']

class OptimizedMovieSeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSeries
        fields = "__all__"

class MovieListSerializer(serializers.ModelSerializer):
    series_count = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Add_movies
        fields = [
            'id', 'add_departments', 'department_name', 'movies_description',
            'movies_preview_url', 'movies_name', 'country',
            'all_series', 'count', 'year', 'series_count', 'genre', 'created_at',
            'is_possible', 'movies_url'
        ]
    
    def get_series_count(self, obj):
        return obj.series.count()
    
    def get_department_name(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None

class MovieDetailSerializer(serializers.ModelSerializer):
    series = OptimizedMovieSeriesSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    dislike_count = serializers.IntegerField(read_only=True)
    comments = OptimizedCommentSerializer(many=True, read_only=True, source='movie_comments')
    department_name = serializers.SerializerMethodField()
    department_id = serializers.IntegerField(source='add_departments.id', read_only=True)
    is_possible = serializers.BooleanField(default=False)

    class Meta:
        model = Add_movies
        fields = [
            'id', 'department_id', 'department_name', 'movies_preview_url',
            'movies_name', 'movies_description', 'movies_url', 'country', 
            'count', 'year', 'genre', 'all_series', 'created_at', 'series', 
            'like_count', 'dislike_count', 'comments', 'is_possible', 'add_departments'
        ]
        extra_kwargs = {
            'add_departments': {'write_only': True}  # Faqat yozish uchun
        }
    
    def get_department_name(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None

class MovieUpdateSerializer(serializers.ModelSerializer):
    department_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Add_movies
        fields = [
            'id', 'department_id', 'movies_preview_url', 'movies_name', 
            'movies_description', 'movies_url', 'country', 'count', 'year', 
            'genre', 'all_series', 'is_possible'
        ]
    
    def update(self, instance, validated_data):
        department_id = validated_data.pop('department_id', None)
        
        if department_id:
            try:
                department = Add_departments.objects.get(id=department_id)
                validated_data['add_departments'] = department
            except Add_departments.DoesNotExist:
                raise serializers.ValidationError({"department_id": "Berilgan department topilmadi"})
        
        return super().update(instance, validated_data)
    
class OptimizedSavedFilmSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='film.id')
    add_departments = serializers.IntegerField(source='film.add_departments_id')
    movies_preview_url = serializers.CharField(source='film.movies_preview_url')
    movies_name = serializers.CharField(source='film.movies_name')
    country = serializers.CharField(source='film.country')
    all_series = serializers.CharField(source='film.all_series')
    count = serializers.IntegerField(source='film.count')
    series_count = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedFilm
        fields = [
            'id', 'add_departments', 'department_name', 'movies_preview_url', 
            'movies_name', 'country', 'all_series', 'count', 'series_count', 'saved_at'
        ]
    
    def get_series_count(self, obj):
        return obj.film.series.count()
    
    def get_department_name(self, obj):
        return obj.film.add_departments.department_name if obj.film.add_departments else None

class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "title", "text", "created_at", "views_count", "is_read"]

    def get_is_read(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        if request.user.is_authenticated:
            return obj.read_by.filter(id=request.user.id).exists()
        else:
            ip = obj.get_client_ip(request)
            return ip and ip in obj.read_by_ips

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email bilan ro'yxatdan o'tgan foydalanuvchi topilmadi.")
        return value

class PasswordResetVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)
    email = serializers.EmailField()

    def validate(self, data):
        try:
            user = User.objects.get(email=data["email"])
            reset_token = PasswordResetToken.objects.filter(
                user=user, token=data["token"], is_used=False, expires_at__gte=timezone.now()
            ).first()
            if not reset_token:
                raise serializers.ValidationError("Kod yaroqsiz yoki muddati o'tgan.")
        except User.DoesNotExist:
            raise serializers.ValidationError("Bu email bilan ro'yxatdan o'tgan foydalanuvchi topilmadi.")
        return data

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(max_length=32)
    confirm_password = serializers.CharField(max_length=32)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords don't match.")
        try:
            user = User.objects.get(email=data["email"])
            reset_token = PasswordResetToken.objects.filter(
                user=user, token=data["token"], is_used=False, expires_at__gte=timezone.now()
            ).first()
            if not reset_token:
                raise serializers.ValidationError("Kod yaroqsiz yoki muddati o'tgan.")
        except User.DoesNotExist:
            raise serializers.ValidationError("Bu email bilan ro'yxatdan o'tgan foydalanuvchi topilmadi.")
        return data

class SimilarMoviesSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Add_movies
        fields = ['id', 'add_departments', 'department_name', 'movies_preview_url', 'movies_name', 'movies_description', 'country']
    
    def get_department_name(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None

class DepartmentMoviesSerializer(serializers.ModelSerializer):
    dmdnme = serializers.SerializerMethodField()
    dmnme = serializers.CharField(source='movies_name')
    dmimage = serializers.SerializerMethodField()
    dmscnt = serializers.SerializerMethodField()
    dmcnt = serializers.IntegerField(source="count")
    dmcont = serializers.CharField(source="country")
    dmllsrs = serializers.CharField(source="all_series")
    department_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Add_movies
        fields = [
            'id',
            'dmdnme', 
            'dmnme',
            'dmimage',
            'dmcont',
            'dmcnt',
            'dmscnt',
            'dmllsrs',
            'department_id'
        ]
    
    def get_dmdnme(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_dmdindx(self, obj):
        return obj.add_departments.id if obj.add_departments else None
    
    def get_dmimage(self, obj):
        return obj.movies_preview_url
    
    def get_dmscnt(self, obj):
        return obj.series.count() if hasattr(obj, 'series') else 0
    
    def get_department_id(self, obj):  # Yangi metod
        return obj.add_departments.id if obj.add_departments else None
    
class SwiperMoviesSerializer(serializers.ModelSerializer):
    mcrntindx = serializers.IntegerField(source='id') 
    dindx = serializers.IntegerField(source='add_departments.id')
    dnme = serializers.SerializerMethodField()
    mnme = serializers.CharField(source='movies_name')
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Add_movies
        fields = [
            'mcrntindx', 
            'dindx', 
            'dnme', 
            'mnme', 
            'image'
        ]
    
    def get_dnme(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_image(self, obj):
        return obj.movies_preview_url
    
class HomeMoviesSerializer(serializers.ModelSerializer):
    hfsdnme = serializers.SerializerMethodField()
    hfsdindx = serializers.SerializerMethodField()
    hfsnme = serializers.CharField(source='movies_name')
    hfsimage = serializers.SerializerMethodField()
    hfsscnt = serializers.SerializerMethodField()
    hfscnt = serializers.IntegerField(source="count")
    hfscont = serializers.CharField(source="country")
    hfsllsrs = serializers.CharField(source="all_series")
    
    class Meta:
        model = Add_movies
        fields = [
            'id',
            'hfsdindx',
            'hfsdnme', 
            'hfsnme',
            'hfsimage',
            'hfscont',
            'hfscnt',
            'hfsscnt',
            'hfsllsrs',
            'created_at'  # 🔥 YANGI
        ]
    
    def get_hfsdnme(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_hfsdindx(self, obj):
        return obj.add_departments.id if obj.add_departments else None
    
    def get_hfsimage(self, obj):
        return obj.movies_preview_url
    
    def get_hfsscnt(self, obj):
        return obj.series.count() if hasattr(obj, 'series') else 0

class DepartmentsSerializer(ModelSerializer):
    movies = serializers.SerializerMethodField()
    department_id = serializers.IntegerField(source='id', read_only=True)
    # image = serializers.SerializerMethodField()

    class Meta:
        model = Add_departments
        fields = [
            'department_id',
            'department_name',
            'image',
            'description',
            'movies',
            # 'created_at',
        ]

    def get_movies(self, obj):
        return obj.movie_count
    
    # def get_image(self, obj):
    #     return obj.image.url if obj.image else None

class TrailersSerializer(serializers.ModelSerializer):
    tdnme = serializers.SerializerMethodField()
    tdindx = serializers.SerializerMethodField()
    tnme = serializers.CharField(source='movies_name')
    timage = serializers.SerializerMethodField()
    tscnt = serializers.SerializerMethodField()
    tcnt = serializers.IntegerField(source="count")
    tcont = serializers.CharField(source="country")
    tllsrs = serializers.CharField(source="all_series")
    
    class Meta:
        model = Add_movies
        fields = [
            'id',
            'tdindx',
            'tdnme', 
            'tnme',
            'timage',
            'tcont',
            'tcnt',
            'tscnt',
            'tllsrs'
        ]
    
    def get_tdnme(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_tdindx(self, obj):
        return obj.add_departments.id if obj.add_departments else None
    
    def get_timage(self, obj):
        return obj.movies_preview_url
    
    def get_tscnt(self, obj):
        return obj.series.count() if hasattr(obj, 'series') else 0

class MovieSearchSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    department_id = serializers.IntegerField(source='add_departments.id')
    series_count = serializers.SerializerMethodField()  # ✅ series_count qo'shildi
    
    class Meta:
        model = Add_movies
        fields = [
            'id',
            'department_id',
            'department_name',
            'movies_preview_url',
            'movies_name', 
            'country',
            'count',
            'year',
            'all_series',
            'series_count',  # ✅ yangi field
            'created_at'
        ]
    
    def get_department_name(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_series_count(self, obj):
        return obj.series.count() if hasattr(obj, 'series') else 0
    
class AllMoviesSerializer(serializers.ModelSerializer):
    aldnme = serializers.SerializerMethodField()
    aldindx = serializers.SerializerMethodField()
    alnme = serializers.CharField(source='movies_name')
    alimage = serializers.SerializerMethodField()
    alscnt = serializers.SerializerMethodField()
    alcnt = serializers.IntegerField(source="count")
    alcont = serializers.CharField(source="country")
    alllsrs = serializers.CharField(source="all_series")
    
    class Meta:
        model = Add_movies
        fields = [
            'id',
            'aldindx',
            'aldnme', 
            'alnme',
            'alimage',
            'alcont',
            'alcnt',
            'alscnt',
            'alllsrs'
        ]
    
    def get_aldnme(self, obj):
        return obj.add_departments.department_name if obj.add_departments else None
    
    def get_aldindx(self, obj):
        return obj.add_departments.id if obj.add_departments else None
    
    def get_alimage(self, obj):
        return obj.movies_preview_url
    
    def get_alscnt(self, obj):
        return obj.series.count() if hasattr(obj, 'series') else 0