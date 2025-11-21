from django.db import models
from django.utils import timezone
from users.models import User

class Add_departments(models.Model):
    department_name = models.CharField(max_length=512)
    image = models.FileField(null=True, blank=True)
    description = models.CharField(max_length=30)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return self.department_name

    @property
    def movie_count(self):
        return self.add_departments.count()

class Add_movies(models.Model):
    add_departments = models.ForeignKey(
        Add_departments, on_delete=models.CASCADE, related_name="add_departments"
    )
    movies_preview = models.FileField(null=True, blank=True, upload_to="movies_images")
    movies_preview_url = models.CharField(max_length=5024, blank=True, null=True)
    movies_name = models.CharField(max_length=128)
    movies_description = models.CharField(max_length=2048)
    movies_url = models.CharField(max_length=10000000, null=True, blank=True)
    movies_local = models.FileField(null=True, blank=True)
    country = models.CharField(max_length=32)
    count = models.PositiveIntegerField(default=0)
    year = models.CharField(max_length=32, default="")
    genre = models.CharField(max_length=512, default="")
    all_series = models.CharField(max_length=512, default="")
    created_at = models.DateTimeField(default=timezone.now, editable=True)
    is_possible = models.BooleanField(default=False)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return self.movies_name

class MovieSeries(models.Model):
    movie = models.ForeignKey(
        Add_movies, on_delete=models.CASCADE, related_name="series"
    )
    title = models.CharField(max_length=128)
    video_url = models.CharField(max_length=2048)
    video_file = models.FileField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return f"{self.movie.movies_name} - {self.title}"

class SavedFilm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    film = models.ForeignKey(Add_movies, on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return f"{self.user.username} saved {self.film.movies_name}"

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_comments")
    movie = models.ForeignKey(Add_movies, on_delete=models.CASCADE, related_name="movie_comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return f"{self.user.username} - {self.movie.movies_name}"

class LikeDislike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    movie = models.ForeignKey(Add_movies, on_delete=models.CASCADE)
    vote = models.BooleanField()
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)

    class Meta:
        unique_together = [
            ("user", "movie"),
            ("session_key", "movie"),
            ("ip_address", "movie"),
        ]
        ordering = ("-pk",)

class Notification(models.Model):
    title = models.TextField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)
    read_by = models.ManyToManyField(User, related_name="read_notifications", blank=True)
    read_by_ips = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-pk",)

    def __str__(self):
        return self.title[:50]

    def mark_as_read(self, request):
        if request.user.is_authenticated:
            if not self.read_by.filter(id=request.user.id).exists():
                self.read_by.add(request.user)
                self.views_count += 1
                self.save()
        else:
            ip = self.get_client_ip(request)
            if ip and ip not in self.read_by_ips:
                self.read_by_ips.append(ip)
                self.views_count += 1
                self.save()

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip