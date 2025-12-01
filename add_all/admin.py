from django.contrib import admin
from .models import (
    Add_departments,
    Add_movies,
    MovieSeries,
    SavedFilm,
    Comment,
    LikeDislike,
    Notification
)

# --- Inline qo'shish ---
class MovieSeriesInline(admin.TabularInline):  # yoki StackedInline
    model = MovieSeries
    extra = 1  # boshlang‘ichda nechta bo‘sh forma chiqishi
    fields = ('title', 'video_url', 'created_at')
    show_change_link = True

@admin.register(Add_movies)
class AddMoviesAdmin(admin.ModelAdmin):
    inlines = [MovieSeriesInline]
    list_display = ('movies_name', 'created_at')  # kerakli maydonlarni ko'rsatish

# --- Boshqa modellarga oddiy ro'yxat ---
admin.site.register(Add_departments)
# admin.site.register(MovieSeries)  # bu qator optional, chunki endi inlines orqali ko'rinadi
# admin.site.register(SavedFilm)
# admin.site.register(Comment)
# admin.site.register(LikeDislike)
# admin.site.register(Notification)
