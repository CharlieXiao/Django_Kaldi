from django.contrib import admin
from Kaldi_speech.models import EveryDayMotto,Course,Section,Sentence

# Register your models here.


# 指定后台网页要显示的字段，对于每日一句则显示作者和格言
class EveryDayMottoAdmin(admin.ModelAdmin):
    list_display = ["id","author","motto"]

admin.site.register(EveryDayMotto,EveryDayMottoAdmin)

admin.site.register(Course)

admin.site.register(Section)

admin.site.register(Sentence)
